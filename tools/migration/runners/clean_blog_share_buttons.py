#!/usr/bin/env python3
"""Xóa khối btn-share / cd-top thừa trong nội dung blog đã import."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
from lib.html_utils import strip_legacy_blog_chrome  # noqa: E402
from lib.paths import aiweb_db_path, load_default_env  # noqa: E402

load_default_env()
DB = aiweb_db_path()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, slug, content FROM posts WHERE content LIKE '%btn-share%' OR content LIKE '%cd-top%'"
    ).fetchall()

    updated = 0
    for row in rows:
        cleaned = strip_legacy_blog_chrome(row["content"])
        if cleaned == row["content"]:
            continue
        updated += 1
        if args.dry_run:
            print(f"[dry-run] {row['id']} {row['slug']}")
            continue
        conn.execute("UPDATE posts SET content = ? WHERE id = ?", (cleaned, row["id"]))

    if not args.dry_run and updated:
        conn.commit()
    conn.close()

    print(f"Posts scanned: {len(rows)}, updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
