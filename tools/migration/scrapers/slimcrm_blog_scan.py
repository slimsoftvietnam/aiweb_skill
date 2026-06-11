#!/usr/bin/env python3
"""Quét blog slimcrm.vn qua slimweb JSON API → inventory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.html_utils import slugify_vi  # noqa: E402
from lib.http_client import HttpClient  # noqa: E402

JSON_API = "https://slimweb.vn/json3/11926/40460"
BLOG_BASE = "https://slimcrm.vn/blog/"
OUTPUT = ROOT / "output" / "slimcrm_blog_inventory.json"


def load_json_response(client: HttpClient, url: str) -> dict:
    return json.loads(client.get_bytes(url).decode("utf-8-sig"))


def build_blog_url(item: dict) -> str:
    alias = (item.get("alias") or "").strip()
    if alias:
        path = alias if alias.startswith("/") else f"/{alias}"
        if not path.endswith(".html"):
            path += ".html"
        return f"https://slimcrm.vn{path}"
    link = (item.get("link") or "").strip()
    if link:
        if link.startswith("http"):
            return link.split("?")[0] + ("" if ".html" in link else ".html")
        return urljoin("https://slimcrm.vn/", link.lstrip("/"))
    return ""


def parse_nodes(data: dict) -> tuple[list[dict], dict]:
    nodes = data.get("nodes") or []
    pager = data.get("pager") or {}
    posts: list[dict] = []
    for wrapper in nodes:
        if not isinstance(wrapper, dict):
            continue
        item = wrapper.get("node") if isinstance(wrapper.get("node"), dict) else wrapper
        url = build_blog_url(item)
        if not url:
            continue
        slug_file = Path(url).name.replace(".html", "")
        category_name = str(item.get("category") or item.get("keywords") or "").strip()
        posts.append(
            {
                "nid": str(item.get("nid") or ""),
                "title": str(item.get("title") or "").strip(),
                "slug": slug_file,
                "url": url,
                "category_name": category_name,
                "category_id": str(item.get("field_blog_chuyenmuc_1") or ""),
                "date": str(item.get("date") or "").strip(),
                "image": str(item.get("image") or "").strip(),
            }
        )
    return posts, pager


def fetch_all_pages(client: HttpClient, max_pages: int = 0) -> list[dict]:
    all_posts: list[dict] = []
    page = 1
    while True:
        url = f"{JSON_API}?page={page}"
        print(f"Fetch {url}")
        data = load_json_response(client, url)
        posts, pager = parse_nodes(data)
        all_posts.extend(posts)
        total_pages = int(pager.get("total_pages") or pager.get("pages") or pager.get("page_count") or 0)
        current = int(pager.get("current_page") or pager.get("page") or page)
        print(f"  page {current}/{total_pages or '?'} nodes={len(posts)}")
        if not posts:
            break
        if total_pages and current >= total_pages:
            break
        if max_pages and page >= max_pages:
            break
        # stop if no pager advance hint and empty next would fail
        if not total_pages and len(posts) == 0:
            break
        page += 1
        if page > 500:
            break
    return all_posts


def dedupe(posts: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for p in posts:
        key = p.get("url") or p.get("slug_file") or p.get("nid")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--sample-raw", action="store_true", help="Save first node raw")
    args = parser.parse_args()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with HttpClient(delay=0.5) as client:
        sample = load_json_response(client, f"{JSON_API}?page=1")
        if args.sample_raw and sample.get("nodes"):
            (OUTPUT.parent / "slimcrm_blog_sample_node.json").write_text(
                json.dumps(sample["nodes"][0], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        posts = dedupe(fetch_all_pages(client, args.max_pages))

    # stats categories
    cats: dict[str, int] = {}
    for p in posts:
        c = p.get("category_name") or "(chưa có)"
        cats[c] = cats.get(c, 0) + 1

    for p in posts:
        primary = (p.get("category_name") or "").split(",")[0].strip()
        p["category_slug"] = slugify_vi(primary or "khac")

    inv = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "slimweb_json_api",
        "api_url": JSON_API,
        "stats": {
            "post_count": len(posts),
            "categories": cats,
        },
        "posts": posts,
    }
    OUTPUT.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = OUTPUT.parent / "slimcrm_blog_links.csv"
    lines = ["stt,url,title,category,category_slug,date,nid,migrate_status"]
    for i, p in enumerate(posts, 1):
        row = [
            str(i),
            p.get("url", ""),
            (p.get("title") or "").replace('"', "'"),
            p.get("category_name", ""),
            p.get("category_slug", ""),
            p.get("date", ""),
            p.get("nid", ""),
            "pending",
        ]
        lines.append(",".join(f'"{x}"' if "," in str(x) else str(x) for x in row))
    csv_path.write_text("\n".join(lines), encoding="utf-8-sig")

    print(f"Wrote {OUTPUT} ({len(posts)} posts)")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
