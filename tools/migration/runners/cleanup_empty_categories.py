#!/usr/bin/env python3
"""Xóa chuyên mục blog không có bài viết."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.paths import aiweb_db_path, load_default_env  # noqa: E402

load_default_env()
DB = aiweb_db_path()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB.exists():
        print(f"Không tìm thấy DB: {DB}")
        return 1

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    empty = conn.execute(
        """
        SELECT c.id, c.name, c.slug
        FROM categories c
        LEFT JOIN posts p ON p.category_id = c.id
        GROUP BY c.id
        HAVING COUNT(p.id) = 0
        ORDER BY c.slug
        """
    ).fetchall()

    if not empty:
        print("Không có chuyên mục rỗng.")
        return 0

    print(f"Found {len(empty)} empty categories:")
    for row in empty:
        name = str(row["name"]).encode("ascii", "replace").decode("ascii")
        print(f"  [{row['id']}] {row['slug']} | {name}")

    if args.dry_run:
        print("(dry-run, no delete)")
        return 0

    ids = [row["id"] for row in empty]
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"DELETE FROM categories WHERE id IN ({placeholders})", ids)

    conn.execute(
        f"""
        DELETE FROM migration_entities
        WHERE entity_type = 'category'
          AND local_id IN ({placeholders})
        """,
        ids,
    )

    conn.commit()
    print(f"Deleted {len(ids)} empty categories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
