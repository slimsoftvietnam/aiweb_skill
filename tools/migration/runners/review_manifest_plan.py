#!/usr/bin/env python3
"""Print a numbered migration plan from an AI Web manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def short(value: Any, limit: int = 90) -> str:
    text = str(value or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def row(index: int, item_type: str, item: dict[str, Any]) -> str:
    source_url = item.get("source_url") or item.get("url") or item.get("source_key") or ""
    title = item.get("title") or item.get("name") or ""
    slug = item.get("slug") or item.get("target_slug") or ""
    status = item.get("status")
    if status is None:
        status = "publish" if item.get("is_published") else "draft"
    return (
        f"{index}. [{item_type}] {short(title, 70)}\n"
        f"   source: {source_url}\n"
        f"   target: /{slug} | status: {status}"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Review migration plan before real import")
    parser.add_argument("--file", required=True, type=Path, help="Manifest JSON file")
    args = parser.parse_args()

    manifest = json.loads(args.file.read_text(encoding="utf-8"))
    items: list[tuple[str, dict[str, Any]]] = []
    items.extend(("landing", page) for page in manifest.get("landing_pages") or [])
    items.extend(("blog", post) for post in manifest.get("blog_posts") or [])

    print(f"Source domain: {manifest.get('source_domain', '')}")
    print(f"Landing pages: {len(manifest.get('landing_pages') or [])}")
    print(f"Blog posts: {len(manifest.get('blog_posts') or [])}")
    print(f"Assets: {len(manifest.get('assets') or [])}")
    print()

    if items:
        print("Migration plan:")
        for index, (item_type, item) in enumerate(items, 1):
            print(row(index, item_type, item))
    else:
        print("Migration plan: no landing pages or blog posts found.")

    skipped = manifest.get("skipped_urls") or manifest.get("skipped") or []
    if skipped:
        print()
        print("Skipped URLs:")
        for item in skipped:
            if isinstance(item, dict):
                print(f"- {item.get('url', '')} ({item.get('reason', 'skipped')})")
            else:
                print(f"- {item}")

    print()
    print("Ask the user to choose: all, numbers like 1,3,5-8, or cancel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
