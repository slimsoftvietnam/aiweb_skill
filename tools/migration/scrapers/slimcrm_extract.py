#!/usr/bin/env python3
"""Extract slimcrm inventory → manifest JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from lib.html_utils import (  # noqa: E402
    dedupe_assets,
    extract_asset_urls,
    extract_meta,
    normalize_html_urls,
    normalize_url,
)
from lib.http_client import HttpClient  # noqa: E402
from lib.manifest_schema import validate_manifest  # noqa: E402

OUTPUT_DIR = ROOT / "output"
INVENTORY_PATH = OUTPUT_DIR / "slimcrm_inventory.json"

LANDING_DOMAIN = "slimcrm.vn"
BLOG_DOMAIN = "blog.slimcrm.vn"

CATEGORY_NAMES = {
    "quan-tri": "Quản trị",
    "crm": "CRM",
    "marketing": "Marketing",
    "ung-dung-ai": "Ứng dụng AI",
    "sales": "Sales",
    "sales-marketing": "Sales & Marketing",
    "nhan-su": "Nhân sự",
    "chuyen-doi-so": "Chuyển đổi số",
    "cong-nghe": "Công nghệ",
    "tang-truong": "Tăng trưởng",
    "hieu-suat": "Hiệu suất",
    "khoi-nghiep": "Khởi nghiệp",
    "ebook": "Ebook",
    "legacy": "Bài viết cũ",
    "tin-tuc": "Tin tức",
    "ai": "AI",
}

CATEGORY_NORMALIZE = {
    "crm": "crm",
    "quantri": "quan-tri",
    "chuyendoiso": "chuyen-doi-so",
    "tang-truong-marketing": "tang-truong",
    "chuyen-doi-so-marketing": "chuyen-doi-so",
}

PILOT_LANDINGS = {"index", "tinhnang", "tai-nguyen", "cong-cu", "prompt"}
PILOT_BLOG_KEYS = {
    "marketing/content-map",
    "crm/phan-mem-crm",
    "quan-tri/van-hoa-doanh-nghiep-la-gi",
    "sales-marketing/ban-hang-la-gi",
}


def landing_slug_from_key(source_key: str) -> str:
    return "home" if source_key == "index" else source_key


def normalize_category_slug(slug: str) -> str:
    slug = (slug or "legacy").strip().lower()
    return CATEGORY_NORMALIZE.get(slug, slug)


def extract_landing(client: HttpClient, entry: dict) -> dict:
    url = entry["url"]
    html = client.get_text(url)
    html = normalize_html_urls(html, url)
    meta = extract_meta(html)
    source_key = entry["source_key"]
    assets = extract_asset_urls(html, url)
    return {
        "source_key": source_key,
        "slug": landing_slug_from_key(source_key),
        "title": meta.get("og_title") or meta.get("title") or entry.get("title_guess") or source_key,
        "html_content": html,
        "seo_description": meta.get("og_description") or meta.get("description") or "",
        "seo_favicon": "",
        "seo_og_image": meta.get("og_image") or "",
        "language": "vi",
        "is_published": False,
        "_assets": assets,
        "_source_url": url,
    }


def extract_blog_body(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    selectors = [
        ".field-name-body .field-item",
        ".field-name-body",
        "article .field-item",
        "article",
        ".node-content",
    ]
    for sel in selectors:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            return str(node)
    return ""


def extract_blog(client: HttpClient, entry: dict, slug_registry: Counter) -> dict | None:
    url = entry["url"]
    try:
        html = client.get_text(url)
    except Exception:  # noqa: BLE001
        return None

    html = normalize_html_urls(html, url)
    meta = extract_meta(html)
    category_slug = normalize_category_slug(entry.get("category_slug", "legacy"))
    post_slug = entry.get("post_slug") or Path(urlparse(url).path).name
    source_key = f"{category_slug}/{post_slug}" if category_slug != "legacy" else post_slug

    slug = post_slug
    if slug_registry[slug] > 0:
        slug = f"{category_slug}-{post_slug}"
    slug_registry[slug] += 1

    body = extract_blog_body(html)
    if not body:
        return None

    assets = extract_asset_urls(body, url)
    featured = meta.get("og_image") or ""
    if featured:
        featured = normalize_url(featured, url)
        if featured:
            assets.append(featured)

    published = meta.get("published_at", "")
    if published:
        published = published.replace("T", " ").replace("Z", "")[:19]

    return {
        "source_key": source_key,
        "slug": slug,
        "title": meta.get("og_title") or meta.get("title") or post_slug,
        "content": body,
        "category_slug": category_slug,
        "featured_image": featured,
        "status": "draft",
        "published_at": published,
        "seo_description": meta.get("og_description") or meta.get("description") or "",
        "language": "vi",
        "_assets": assets,
        "_source_url": url,
    }


def build_categories(posts: list[dict]) -> list[dict]:
    slugs = {normalize_category_slug(p.get("category_slug", "legacy")) for p in posts}
    categories = []
    for slug in sorted(slugs):
        categories.append(
            {
                "source_key": slug,
                "name": CATEGORY_NAMES.get(slug, slug.replace("-", " ").title()),
                "slug": slug,
                "description": "",
            }
        )
    return categories


def split_blog_batches(posts: list[dict], batch_size: int) -> list[list[dict]]:
    return [posts[i : i + batch_size] for i in range(0, len(posts), batch_size)]


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_internal(manifest: dict) -> dict:
    clean = json.loads(json.dumps(manifest))
    for page in clean.get("landing_pages", []):
        page.pop("_assets", None)
        page.pop("_source_url", None)
    for post in clean.get("blog_posts", []):
        post.pop("_assets", None)
        post.pop("_source_url", None)
    return clean


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract slimcrm manifest")
    parser.add_argument("--pilot", action="store_true", help="Only pilot URLs")
    parser.add_argument(
        "--include-blog",
        action="store_true",
        help="Also extract blog.slimcrm.vn (disabled by default)",
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Blog posts per batch file")
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    args = parser.parse_args()

    if not args.inventory.exists():
        print(f"Missing inventory: {args.inventory}. Run slimcrm_recon.py first.")
        return 1

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    landing_entries = [
        e for e in inventory["sources"]["slimcrm.vn"]["landing_pages"]
        if e.get("type", "landing") == "landing"
    ]
    blog_entries: list[dict] = []
    if args.include_blog:
        blog_entries = inventory.get("sources", {}).get("blog.slimcrm.vn", {}).get("posts", [])

    if args.pilot:
        landing_entries = [e for e in landing_entries if e["source_key"] in PILOT_LANDINGS]
        if args.include_blog:
            blog_entries = [
                e
                for e in blog_entries
                if f"{e.get('category_slug','')}/{e.get('post_slug','')}" in PILOT_BLOG_KEYS
                or e.get("post_slug") in PILOT_BLOG_KEYS
            ]

    all_assets: list[str] = []
    landing_pages: list[dict] = []
    blog_posts: list[dict] = []
    slug_registry: Counter = Counter()

    with HttpClient() as client:
        for entry in landing_entries:
            print(f"Extract landing: {entry['url']}")
            page = extract_landing(client, entry)
            all_assets.extend(page.pop("_assets", []))
            page.pop("_source_url", None)
            landing_pages.append(page)

        if args.include_blog:
            for entry in blog_entries:
                print(f"Extract blog: {entry['url']}")
                post = extract_blog(client, entry, slug_registry)
                if post:
                    all_assets.extend(post.pop("_assets", []))
                    post.pop("_source_url", None)
                    blog_posts.append(post)

    assets = dedupe_assets(all_assets)

    landing_manifest = {
        "source_domain": LANDING_DOMAIN,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": [],
        "assets": [
            a for a in assets
            if LANDING_DOMAIN in a["source_url"] or "ai.slim.vn" in a["source_url"]
        ],
        "landing_pages": landing_pages,
        "blog_posts": [],
    }

    prefix = "slimcrm_manifest_pilot" if args.pilot else "slimcrm_manifest"
    landing_path = OUTPUT_DIR / f"{prefix}_landing.json"
    write_manifest(landing_path, strip_internal(landing_manifest))
    print(f"Wrote {landing_path} ({len(landing_pages)} landings)")

    if args.include_blog:
        categories = build_categories(blog_posts)
        blog_assets = [a for a in assets if BLOG_DOMAIN in a["source_url"]]
        blog_manifest_base = {
            "source_domain": BLOG_DOMAIN,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "categories": categories,
            "assets": blog_assets,
            "landing_pages": [],
        }
        batches = split_blog_batches(blog_posts, args.batch_size)
        if args.pilot:
            blog_manifest = {**blog_manifest_base, "blog_posts": blog_posts, "assets": assets}
            blog_path = OUTPUT_DIR / f"{prefix}_blog.json"
            write_manifest(blog_path, strip_internal(blog_manifest))
            print(f"Wrote {blog_path} ({len(blog_posts)} posts)")
        else:
            for idx, batch in enumerate(batches, start=1):
                manifest = {
                    **blog_manifest_base,
                    "blog_posts": batch,
                    "assets": blog_assets if idx == 1 else [],
                }
                blog_path = OUTPUT_DIR / f"slimcrm_manifest_blog_batch_{idx:03d}.json"
                write_manifest(blog_path, strip_internal(manifest))
                print(f"Wrote {blog_path} ({len(batch)} posts)")

    errors = validate_manifest({**landing_manifest, "blog_posts": blog_posts})
    if errors:
        print("Validation warnings:", errors)
    print(f"Done. landings={len(landing_pages)} blog_posts={len(blog_posts)} assets={len(assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
