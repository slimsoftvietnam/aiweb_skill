#!/usr/bin/env python3
"""Extract + import blog posts không có trong slimweb JSON API."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup  # noqa: E402

from lib.html_utils import (  # noqa: E402
    extract_meta,
    normalize_url,
    resolve_slimweb_file_url,
    slugify_vi,
)
from lib.http_client import HttpClient  # noqa: E402

EXTRACT = ROOT / "scrapers" / "slimcrm_blog_extract.py"
IMPORT = ROOT / "runners" / "import_manifest.py"
OUTPUT = ROOT / "output"
INVENTORY = OUTPUT / "slimcrm_blog_inventory.json"
PATCH_INVENTORY = OUTPUT / "slimcrm_blog_inventory_patch.json"


def category_from_soup(soup: BeautifulSoup) -> str:
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


def entry_from_url(client: HttpClient, url: str) -> dict:
    html = client.get_text(url)
    soup = BeautifulSoup(html, "lxml")
    meta = extract_meta(html)
    h1 = soup.select_one(".post_title h1")
    title = h1.get_text(strip=True) if h1 else meta.get("og_title") or ""
    slug = Path(url).stem
    date = ""
    ch = soup.select_one(".chuyenmuc")
    if ch:
        m = re.search(r"\((\d{2}/\d{2}/\d{4})\)", ch.get_text())
        if m:
            date = m.group(1)
    cat = category_from_soup(soup)
    img = meta.get("og_image") or ""
    if img:
        img = resolve_slimweb_file_url(normalize_url(img, url) or img) or img
    return {
        "nid": "",
        "title": title,
        "slug": slug,
        "url": url,
        "category_name": cat,
        "category_id": "40460",
        "date": date,
        "image": img,
        "category_slug": slugify_vi(cat.split(",")[0].strip() if cat else "khac"),
    }


def merge_inventory(entries: list[dict]) -> Path:
    base = json.loads(INVENTORY.read_text(encoding="utf-8")) if INVENTORY.exists() else {"posts": []}
    existing = {p.get("slug"): p for p in base.get("posts") or []}
    added = 0
    for e in entries:
        if e["slug"] not in existing:
            existing[e["slug"]] = e
            added += 1
    posts = list(existing.values())
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "slimweb_json_api+manual_urls",
        "api_url": base.get("api_url", ""),
        "stats": {"post_count": len(posts)},
        "posts": posts,
    }
    PATCH_INVENTORY.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Patch inventory: {PATCH_INVENTORY} (+{added} new, total {len(posts)})")
    return PATCH_INVENTORY


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", help="URL bài blog slimcrm.vn")
    parser.add_argument("--env", type=Path, default=ROOT / "config.env")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args()

    with HttpClient() as client:
        entries = [entry_from_url(client, u) for u in args.urls]

    merge_inventory(entries)
    only_new = OUTPUT / "slimcrm_blog_missing_manifest_inv.json"
    only_new.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "manual_urls",
                "posts": entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    py = sys.executable
    env_flag = ["--env", str(args.env)]

    rc = subprocess.call(
        [
            py,
            str(EXTRACT),
            "--inventory",
            str(only_new),
            "--limit",
            str(len(entries)),
        ]
    )
    if rc:
        return rc

    if args.extract_only:
        return 0

    manifest = OUTPUT / "slimcrm_blog_manifest.json"
    if not manifest.exists():
        print("Không tạo được manifest")
        return 1

    rc = subprocess.call(
        [
            py,
            str(IMPORT),
            "--file",
            str(manifest),
            *env_flag,
            *(["--dry-run"] if args.dry_run else ["--publish"]),
        ]
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
