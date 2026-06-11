#!/usr/bin/env python3
"""Recon slimcrm.vn landing pages → inventory JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.html_utils import extract_asset_urls, extract_meta, normalize_url  # noqa: E402
from lib.http_client import HttpClient  # noqa: E402

OUTPUT_DIR = ROOT / "output"
LANDING_BASE = "https://slimcrm.vn"
BLOG_BASE = "https://blog.slimcrm.vn"
BLOG_SITEMAP = f"{BLOG_BASE}/sitemap.xml"

LANDING_SEEDS = [
    f"{LANDING_BASE}/index.html",
    f"{LANDING_BASE}/tai-nguyen.html",
    f"{LANDING_BASE}/cong-cu.html",
    f"{LANDING_BASE}/prompt.html",
    f"{LANDING_BASE}/tinhnang.html",
]

SKIP_HOST_SUFFIXES = (
    "help.slimcrm.vn",
    "blog.slimcrm.vn",
)
SKIP_PATH_PREFIXES = (
    "/admin",
    "/user/",
    "/search",
    "/comment/",
)


def parse_blog_sitemap(xml_bytes: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(xml_bytes)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    posts: list[dict[str, str]] = []
    for loc_el in root.findall(".//s:loc", ns):
        url = (loc_el.text or "").strip()
        if not url:
            continue
        path = url.replace(f"{BLOG_BASE}/", "").strip("/")
        parts = path.split("/")
        category_slug = ""
        post_slug = ""
        if len(parts) >= 2:
            category_slug = parts[0].lower()
            post_slug = parts[1]
        elif len(parts) == 1:
            category_slug = "legacy"
            post_slug = parts[0]
        lastmod = ""
        parent = loc_el.getparent() if hasattr(loc_el, "getparent") else None
        # ElementTree has no getparent in stdlib; find via iteration
        for url_node in root.findall(".//s:url", ns):
            loc = url_node.find("s:loc", ns)
            if loc is not None and (loc.text or "").strip() == url:
                lm = url_node.find("s:lastmod", ns)
                if lm is not None and lm.text:
                    lastmod = lm.text.strip()
                break
        posts.append(
            {
                "url": url,
                "category_slug": category_slug,
                "post_slug": post_slug,
                "lastmod": lastmod,
            }
        )
    return posts


def is_landing_html_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "slimcrm.vn":
        return False
    path = parsed.path.lower()
    if not path.endswith(".html"):
        return False
    for prefix in SKIP_PATH_PREFIXES:
        if path.startswith(prefix):
            return False
    return True


def classify_landing_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.startswith("/blog/"):
        return "legacy_blog_on_main"
    return "landing"


def discover_landing_pages(client: HttpClient) -> tuple[list[dict], list[dict], list[dict]]:
    seen: set[str] = set()
    queue = list(LANDING_SEEDS)
    landing_pages: list[dict] = []
    legacy_blog: list[dict] = []
    skip: list[dict] = []

    while queue:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        if not is_landing_html_url(url):
            skip.append({"url": url, "reason": "not_landing_html"})
            continue

        try:
            html = client.get_text(url)
        except Exception as exc:  # noqa: BLE001
            skip.append({"url": url, "reason": f"fetch_error: {exc}"})
            continue

        kind = classify_landing_url(url)
        meta = extract_meta(html)
        source_key = Path(urlparse(url).path).stem
        entry = {
            "url": url,
            "source_key": source_key,
            "title_guess": meta.get("og_title") or meta.get("title") or source_key,
            "type": kind,
        }
        if kind == "legacy_blog_on_main":
            legacy_blog.append(entry)
        else:
            landing_pages.append(entry)

        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
            href = match.group(1).strip()
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            full = normalize_url(href, url)
            if not full:
                continue
            host = urlparse(full).netloc.lower().removeprefix("www.")
            if any(host == s or host.endswith("." + s) for s in SKIP_HOST_SUFFIXES):
                continue
            if host != "slimcrm.vn":
                continue
            if is_landing_html_url(full) and full not in seen:
                queue.append(full.split("?")[0])

    return landing_pages, legacy_blog, skip


def sample_image_domains(client: HttpClient, urls: list[str], limit: int = 20) -> Counter:
    domains: Counter = Counter()
    for url in urls[:limit]:
        try:
            html = client.get_text(url)
            for asset in extract_asset_urls(html, url):
                host = urlparse(asset).netloc.lower().removeprefix("www.")
                domains[host] += 1
        except Exception:  # noqa: BLE001
            continue
    return domains


def main() -> int:
    parser = argparse.ArgumentParser(description="Recon slimcrm.vn landing inventory")
    parser.add_argument(
        "--include-blog",
        action="store_true",
        help="Also fetch blog.slimcrm.vn sitemap (disabled by default)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with HttpClient() as client:
        blog_posts: list[dict[str, str]] = []
        categories: list[dict] = []
        if args.include_blog:
            blog_xml = client.get_bytes(BLOG_SITEMAP)
            blog_posts = parse_blog_sitemap(blog_xml)
            cat_counts = Counter(p["category_slug"] for p in blog_posts if p["category_slug"])
            categories = [
                {"slug": slug, "post_count": count}
                for slug, count in cat_counts.most_common()
            ]

        landing_pages, legacy_blog, skip = discover_landing_pages(client)

        flat_blog = sum(1 for p in blog_posts if p.get("category_slug") == "legacy")
        nested_blog = len(blog_posts) - flat_blog

        sample_urls = [p["url"] for p in landing_pages[:20]]
        image_domains = sample_image_domains(client, sample_urls)

    inventory = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "landing_only" if not args.include_blog else "landing_and_blog",
        "sources": {
            "slimcrm.vn": {
                "landing_pages": landing_pages,
                "legacy_blog": legacy_blog,
                "skip": skip,
            },
        },
        "stats": {
            "landing_count": len(landing_pages),
            "legacy_blog_on_main_count": len(legacy_blog),
            "blog_count": len(blog_posts),
            "nested_blog_urls": nested_blog,
            "flat_blog_urls": flat_blog,
            "skip_count": len(skip),
            "image_domains_sample": dict(image_domains),
        },
    }
    if args.include_blog:
        inventory["sources"]["blog.slimcrm.vn"] = {
            "posts": blog_posts,
            "categories": categories,
        }

    out_path = OUTPUT_DIR / "slimcrm_inventory.json"
    out_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"  scope: {inventory['scope']}")
    print(f"  landing_count: {inventory['stats']['landing_count']}")
    if args.include_blog:
        print(f"  blog_count: {inventory['stats']['blog_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
