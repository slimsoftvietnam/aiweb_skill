#!/usr/bin/env python3
"""Extract slimcrm.vn/blog từ inventory → manifest + categories."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from lib.html_utils import (  # noqa: E402
    dedupe_assets,
    extract_asset_urls,
    extract_meta,
    normalize_html_urls,
    normalize_url,
    resolve_slimweb_file_url,
    slugify_vi,
    strip_legacy_blog_chrome,
)
from lib.http_client import HttpClient  # noqa: E402

INVENTORY = ROOT / "output" / "slimcrm_blog_inventory.json"
OUTPUT_DIR = ROOT / "output"
SOURCE_DOMAIN = "slimcrm.vn"


def parse_date_vn(raw: str) -> str:
    raw = (raw or "").strip()
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", raw)
    if not m:
        return ""
    d, mo, y = m.groups()
    return f"{y}-{mo}-{d} 00:00:00"


def primary_category_name(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    return raw.split(",")[0].strip()


def extract_category_from_html(soup: BeautifulSoup) -> str:
    kw = soup.find("meta", attrs={"name": "keywords"})
    if kw and kw.get("content"):
        return kw["content"].strip()
    ch = soup.select_one(".chuyenmuc")
    if not ch:
        return ""
    for a in ch.find_all("a"):
        t = a.get_text(strip=True)
        if t and t not in ("Trang chủ", "Home", "#"):
            return t
    return ""


def extract_body_html(soup: BeautifulSoup) -> str:
    node = soup.select_one("#post_text") or soup.select_one(".post_text")
    if not node:
        return ""
    return strip_legacy_blog_chrome(str(node))


def extract_post(client: HttpClient, entry: dict) -> dict | None:
    url = entry["url"]
    try:
        html = client.get_text(url)
    except Exception:  # noqa: BLE001
        return None

    html = normalize_html_urls(html, url)
    soup = BeautifulSoup(html, "lxml")
    meta = extract_meta(html)

    title = ""
    h1 = soup.select_one(".post_title h1")
    if h1:
        title = h1.get_text(strip=True)
    if not title:
        title = meta.get("og_title") or meta.get("title") or entry.get("title", "")

    category_name = extract_category_from_html(soup) or primary_category_name(
        entry.get("category_name", "")
    )
    category_slug = slugify_vi(category_name or "khac")
    body = extract_body_html(soup)
    if not body:
        return None

    assets = extract_asset_urls(body, url)
    featured = entry.get("image") or meta.get("og_image") or ""
    if featured:
        featured = resolve_slimweb_file_url(normalize_url(featured, url) or featured)
        if featured:
            assets.append(featured)

    date_raw = entry.get("date") or ""
    ch = soup.select_one(".chuyenmuc")
    if ch:
        dm = re.search(r"\((\d{2}/\d{2}/\d{4})\)", ch.get_text())
        if dm:
            date_raw = dm.group(1)

    slug = entry.get("slug") or Path(url).stem
    source_key = f"blog/{slug}"

    return {
        "source_key": source_key,
        "slug": slug,
        "title": title,
        "content": body,
        "category_slug": category_slug,
        "category_name": category_name or category_slug,
        "featured_image": featured,
        "status": "published",
        "published_at": parse_date_vn(date_raw),
        "seo_description": meta.get("og_description") or meta.get("description") or "",
        "language": "vi",
        "_assets": assets,
        "_url": url,
    }


def build_categories(posts: list[dict]) -> list[dict]:
    seen: dict[str, str] = {}
    for p in posts:
        slug = p.get("category_slug", "khac")
        name = p.get("category_name") or slug
        seen[slug] = name
    return [
        {"source_key": slug, "name": name, "slug": slug, "description": ""}
        for slug, name in sorted(seen.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--slug", help="Chỉ extract 1 slug")
    args = parser.parse_args()

    if not args.inventory.exists():
        print("Chạy slimcrm_blog_scan.py trước")
        return 1

    inv = json.loads(args.inventory.read_text(encoding="utf-8"))
    entries = inv["posts"]
    if args.slug:
        entries = [e for e in entries if e.get("slug") == args.slug]
    else:
        entries = entries[args.offset :]
        if args.limit:
            entries = entries[: args.limit]

    posts: list[dict] = []
    all_assets: list[str] = []

    with HttpClient() as client:
        for i, entry in enumerate(entries, 1):
            print(f"[{i}/{len(entries)}] {entry.get('url')}")
            post = extract_post(client, entry)
            if post:
                all_assets.extend(post.pop("_assets", []))
                post.pop("_url", None)
                posts.append(post)

    categories = build_categories(posts)
    assets = dedupe_assets(all_assets)

    use_single = bool(args.slug) or (args.limit > 0 and args.limit <= 10)
    if use_single:
        out = OUTPUT_DIR / "slimcrm_blog_manifest.json"
        manifest = {
            "source_domain": SOURCE_DOMAIN,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "categories": categories,
            "assets": assets,
            "landing_pages": [],
            "blog_posts": posts,
        }
        out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out} posts={len(posts)} cats={len(categories)} assets={len(assets)}")
    else:
        for idx in range(0, len(posts), args.batch_size):
            batch = posts[idx : idx + args.batch_size]
            batch_cats = build_categories(batch)
            batch_num = idx // args.batch_size + 1
            out = OUTPUT_DIR / f"slimcrm_blog_manifest_batch_{batch_num:03d}.json"
            manifest = {
                "source_domain": SOURCE_DOMAIN,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "categories": batch_cats if batch_num == 1 else categories,
                "assets": assets if batch_num == 1 else [],
                "landing_pages": [],
                "blog_posts": batch,
            }
            out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Wrote {out} ({len(batch)} posts)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
