#!/usr/bin/env python3
"""Extract generic inventory → AI Web manifest JSON."""

from __future__ import annotations

import argparse
import json
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
    slugify_vi,
)
from lib.http_client import HttpClient  # noqa: E402
from lib.manifest_schema import validate_manifest  # noqa: E402
from scrapers.site_recon import domain_file_key, normalize_domain, target_slug_from_key  # noqa: E402

OUTPUT_DIR = ROOT / "output"


def blog_content_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for selector in (
        "article",
        "#post_text",
        ".post_text",
        ".post-content",
        ".entry-content",
        ".article-content",
        "main",
    ):
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            return str(node)
    body = soup.body
    return str(body) if body else html


def extract_landing(client: HttpClient, entry: dict, source_domain: str) -> dict:
    url = entry["url"]
    html = client.get_text(url)
    html = normalize_html_urls(html, url)
    meta = extract_meta(html)
    source_key = entry["source_key"]
    assets = extract_asset_urls(html, url, source_domain=source_domain)
    return {
        "source_key": source_key,
        "slug": entry.get("target_slug") or target_slug_from_key(source_key),
        "title": meta.get("og_title") or meta.get("title") or entry.get("title_guess") or source_key,
        "html_content": html,
        "seo_description": meta.get("og_description") or meta.get("description") or "",
        "seo_favicon": "",
        "seo_og_image": meta.get("og_image") or "",
        "language": "vi",
        "is_published": False,
        "source_url": url,
        "_assets": assets,
        "_source_url": url,
    }


def extract_blog(client: HttpClient, entry: dict, source_domain: str) -> dict:
    url = entry["url"]
    html = client.get_text(url)
    html = normalize_html_urls(html, url)
    meta = extract_meta(html)
    source_key = entry["source_key"]
    content = blog_content_html(html)
    assets = extract_asset_urls(content, url, source_domain=source_domain)
    path = urlparse(url).path.strip("/").split("/")
    category_slug = slugify_vi(path[0], 40) if len(path) > 1 else "tin-tuc"
    return {
        "source_key": source_key,
        "slug": entry.get("target_slug") or source_key,
        "title": meta.get("og_title") or meta.get("title") or entry.get("title_guess") or source_key,
        "content": content,
        "category_slug": category_slug,
        "featured_image": meta.get("og_image") or "",
        "status": "draft",
        "published_at": meta.get("published_at") or "",
        "source_url": url,
        "_assets": assets,
        "_source_url": url,
    }


def filter_entries(pages: list[dict], only_keys: set[str] | None, pilot: int | None) -> list[dict]:
    if only_keys:
        return [p for p in pages if p.get("source_key") in only_keys]
    if pilot is not None and pilot > 0:
        return pages[:pilot]
    return pages


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Extract inventory to manifest for any domain")
    parser.add_argument("--domain", required=True, help="Source domain, e.g. example.com")
    parser.add_argument("--file", type=Path, help="Inventory JSON (default: output/{domain}_inventory.json)")
    parser.add_argument("--only", help="Comma-separated source_key list to extract")
    parser.add_argument("--pilot", type=int, help="Extract first N pages only")
    parser.add_argument("--landing-only", action="store_true", help="Skip blog_post pages")
    args = parser.parse_args()

    domain = normalize_domain(args.domain)
    inventory_path = args.file or (OUTPUT_DIR / f"{domain_file_key(domain)}_inventory.json")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    pages = inventory.get("pages") or []
    only_keys = {k.strip() for k in args.only.split(",") if k.strip()} if args.only else None
    pages = filter_entries(pages, only_keys, args.pilot)
    if args.landing_only:
        pages = [p for p in pages if p.get("type") == "landing"]

    landing_pages: list[dict] = []
    blog_posts: list[dict] = []
    all_assets: list[str] = []
    skipped: list[dict] = list(inventory.get("skipped") or [])

    with HttpClient() as client:
        for entry in pages:
            try:
                if entry.get("type") == "blog_post":
                    item = extract_blog(client, entry, domain)
                    blog_posts.append({k: v for k, v in item.items() if not k.startswith("_")})
                else:
                    item = extract_landing(client, entry, domain)
                    landing_pages.append({k: v for k, v in item.items() if not k.startswith("_")})
                all_assets.extend(item.get("_assets") or [])
            except Exception as exc:  # noqa: BLE001
                skipped.append({"url": entry.get("url", ""), "reason": f"extract_error: {exc}"})

    categories: list[dict] = []
    cat_counts = Counter(post.get("category_slug") or "tin-tuc" for post in blog_posts)
    for slug, count in cat_counts.items():
        categories.append(
            {
                "source_key": slug,
                "name": slug.replace("-", " ").title(),
                "slug": slug,
                "description": f"{count} bài",
            }
        )

    manifest = {
        "source_domain": domain,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
        "assets": dedupe_assets(all_assets),
        "landing_pages": landing_pages,
        "blog_posts": blog_posts,
        "skipped_urls": skipped,
    }

    errors = validate_manifest(manifest)
    if errors:
        print("Manifest validation warnings/errors:")
        for err in errors:
            print(f"  - {err}")

    out_path = OUTPUT_DIR / f"{domain_file_key(domain)}_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"  landing_pages: {len(landing_pages)}")
    print(f"  blog_posts: {len(blog_posts)}")
    print(f"  assets: {len(manifest['assets'])}")
    print()
    print("Next: python runners/review_manifest_plan.py --file", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
