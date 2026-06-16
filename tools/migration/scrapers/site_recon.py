#!/usr/bin/env python3
"""Generic recon: domain + seed URL(s) → inventory JSON for migration planning."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.html_utils import extract_meta, host_matches_source, normalize_url, slugify_vi  # noqa: E402
from lib.http_client import HttpClient  # noqa: E402

OUTPUT_DIR = ROOT / "output"

SKIP_PATH_PREFIXES = (
    "/admin",
    "/wp-admin",
    "/login",
    "/signin",
    "/signup",
    "/register",
    "/cart",
    "/checkout",
    "/account",
    "/user/",
    "/search",
    "/comment/",
    "/api/",
)

SKIP_EXTENSIONS = (
    ".pdf",
    ".zip",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".xml",
    ".json",
    ".rss",
    ".atom",
)


def normalize_domain(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://", "", value)
    return value.removeprefix("www.").split("/")[0]


def domain_file_key(domain: str) -> str:
    return normalize_domain(domain).replace(".", "_")


def default_start_url(domain: str) -> str:
    return f"https://{normalize_domain(domain)}/"


def classify_page(url: str) -> str:
    path = urlparse(url).path.lower()
    for prefix in SKIP_PATH_PREFIXES:
        if path.startswith(prefix):
            return "skip"
    for ext in SKIP_EXTENSIONS:
        if path.endswith(ext):
            return "skip"
    blog_markers = ("/blog/", "/posts/", "/post/", "/tin-tuc/", "/bai-viet/", "/news/", "/article/")
    if any(marker in path for marker in blog_markers):
        return "blog_post"
    return "landing"


def source_key_from_url(url: str, domain: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "home"
    stem = Path(path).stem or Path(path).name
    if stem in ("index", "home"):
        return "home"
    return slugify_vi(stem, 80)


def target_slug_from_key(source_key: str) -> str:
    return "home" if source_key == "home" else source_key


def fetch_sitemap_urls(
    client: HttpClient,
    domain: str,
    include_subdomains: bool,
) -> list[str]:
    sitemap_url = f"https://{normalize_domain(domain)}/sitemap.xml"
    try:
        xml_bytes = client.get_bytes(sitemap_url)
    except Exception:  # noqa: BLE001
        return []

    urls: list[str] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc_el in root.findall(".//s:loc", ns):
        loc = (loc_el.text or "").strip()
        if not loc:
            continue
        host = urlparse(loc).netloc.lower().removeprefix("www.")
        if host_matches_source(host, domain, include_subdomains):
            urls.append(loc.split("?")[0])
    return urls


def discover_pages(
    client: HttpClient,
    domain: str,
    seeds: list[str],
    include_subdomains: bool,
    max_pages: int,
    use_sitemap: bool,
) -> tuple[list[dict], list[dict]]:
    seen: set[str] = set()
    queue = list(dict.fromkeys(seeds))
    pages: list[dict] = []
    skipped: list[dict] = []

    if use_sitemap:
        for url in fetch_sitemap_urls(client, domain, include_subdomains):
            if url not in seen:
                queue.append(url)

    while queue and len(pages) + len(skipped) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        host = urlparse(url).netloc.lower().removeprefix("www.")
        if not host_matches_source(host, domain, include_subdomains):
            skipped.append({"url": url, "reason": "external_host"})
            continue

        page_type = classify_page(url)
        if page_type == "skip":
            skipped.append({"url": url, "reason": "path_skip_rule"})
            continue

        try:
            html = client.get_text(url)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"url": url, "reason": f"fetch_error: {exc}"})
            continue

        meta = extract_meta(html)
        source_key = source_key_from_url(url, domain)
        pages.append(
            {
                "url": url,
                "source_key": source_key,
                "target_slug": target_slug_from_key(source_key),
                "title_guess": meta.get("og_title") or meta.get("title") or source_key,
                "type": page_type,
            }
        )

        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
            href = match.group(1).strip()
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full = normalize_url(href, url)
            if not full:
                continue
            link_host = urlparse(full).netloc.lower().removeprefix("www.")
            if not host_matches_source(link_host, domain, include_subdomains):
                continue
            if classify_page(full) == "skip":
                continue
            clean = full.split("?")[0]
            if clean not in seen:
                queue.append(clean)

    return pages, skipped


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Recon any domain for AI Web migration")
    parser.add_argument("--domain", required=True, help="Source domain, e.g. example.com")
    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        default=[],
        help="Seed URL (repeatable). Default: https://{domain}/",
    )
    parser.add_argument("--sitemap", action="store_true", help="Also read /sitemap.xml")
    parser.add_argument(
        "--no-subdomains",
        action="store_true",
        help="Only crawl exact domain, not subdomains",
    )
    parser.add_argument("--max-pages", type=int, default=200, help="Max pages to inspect")
    args = parser.parse_args()

    domain = normalize_domain(args.domain)
    seeds = args.urls or [default_start_url(domain)]
    include_subdomains = not args.no_subdomains

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with HttpClient() as client:
        pages, skipped = discover_pages(
            client,
            domain,
            seeds,
            include_subdomains,
            args.max_pages,
            args.sitemap,
        )

    landing = [p for p in pages if p["type"] == "landing"]
    blog = [p for p in pages if p["type"] == "blog_post"]

    inventory = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_domain": domain,
        "start_urls": seeds,
        "scope": {
            "include_subdomains": include_subdomains,
            "used_sitemap": args.sitemap,
            "max_pages": args.max_pages,
        },
        "pages": pages,
        "skipped": skipped,
        "stats": {
            "landing_count": len(landing),
            "blog_count": len(blog),
            "skip_count": len(skipped),
            "total_discovered": len(pages),
        },
    }

    out_path = OUTPUT_DIR / f"{domain_file_key(domain)}_inventory.json"
    out_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")
    print(f"  domain: {domain}")
    print(f"  landing: {inventory['stats']['landing_count']}")
    print(f"  blog: {inventory['stats']['blog_count']}")
    print(f"  skipped: {inventory['stats']['skip_count']}")
    print()
    print("Next: python runners/review_inventory_plan.py --file", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
