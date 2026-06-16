#!/usr/bin/env python3
"""Print a numbered migration plan from a recon inventory (before extract/import)."""

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


def row(index: int, page: dict[str, Any]) -> str:
    page_type = page.get("type") or "landing"
    return (
        f"{index}. [{page_type}] {short(page.get('title_guess'), 70)}\n"
        f"   source: {page.get('url', '')}\n"
        f"   target: /{page.get('target_slug') or page.get('source_key') or ''}"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Review migration plan from recon inventory")
    parser.add_argument("--file", required=True, type=Path, help="Inventory JSON from site_recon.py")
    args = parser.parse_args()

    inventory = json.loads(args.file.read_text(encoding="utf-8"))
    pages = inventory.get("pages") or []
    skipped = inventory.get("skipped") or []
    stats = inventory.get("stats") or {}

    print(f"Source domain: {inventory.get('source_domain', '')}")
    print(f"Start URLs: {', '.join(inventory.get('start_urls') or [])}")
    print(f"Landing pages: {stats.get('landing_count', sum(1 for p in pages if p.get('type') == 'landing'))}")
    print(f"Blog posts: {stats.get('blog_count', sum(1 for p in pages if p.get('type') == 'blog_post'))}")
    print(f"Skipped during recon: {stats.get('skip_count', len(skipped))}")
    print()

    if pages:
        print("Migration plan (recon):")
        for index, page in enumerate(pages, 1):
            print(row(index, page))
    else:
        print("Migration plan: no pages discovered.")

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
    print("Then extract with site_extract.py --only ... or --pilot N before import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
