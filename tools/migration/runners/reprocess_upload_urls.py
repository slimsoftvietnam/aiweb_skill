#!/usr/bin/env python3
"""Đổi uploads/migrate → aiweb_core/uploads/migrate trong DB (site đã import trước đó)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.env_config import get_migration_upload_prefix, load_env_file, use_client_side_asset_rewrite
from lib.migration_urls import apply_upload_prefix_to_text, rewrite_migrated_text
from lib.paths import aiweb_db_path, load_default_env

TEXT_COLUMNS: dict[str, list[str]] = {
    "landing_page_sections": ["html_content"],
    "landing_pages": ["seo_favicon", "seo_og_image", "header_code", "footer_code"],
    "blog_posts": ["content", "featured_image"],
    "products": ["description", "images"],
}


def _rewrite_value(value: str | None, prefix: str) -> tuple[str, bool]:
    if value is None or value == "":
        return value or "", False
    text = str(value)
    if text.startswith("[") or (text.startswith("{") and '"uploads/migrate/' in text):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                changed = False
                out = []
                for item in parsed:
                    if isinstance(item, str):
                        new_item = apply_upload_prefix_to_text(item, prefix)
                        changed = changed or new_item != item
                        out.append(new_item)
                    else:
                        out.append(item)
                if changed:
                    return json.dumps(out, ensure_ascii=False), True
        except json.JSONDecodeError:
            pass
    new_text, n = rewrite_migrated_text(text, prefix=prefix)
    return new_text, n > 0 or new_text != text


def reprocess_db(db_path: Path, prefix: str, dry_run: bool) -> dict[str, int]:
    stats = {"tables": 0, "rows": 0, "columns": 0}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        for table, columns in TEXT_COLUMNS.items():
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            if not cur.fetchone():
                continue

            existing_cols = {
                row[1]
                for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            cols = [c for c in columns if c in existing_cols]
            if not cols:
                continue

            stats["tables"] += 1
            select_cols = ["rowid", *cols]
            rows = conn.execute(
                f"SELECT {', '.join(select_cols)} FROM {table}"
            ).fetchall()

            for row in rows:
                updates: dict[str, str] = {}
                for col in cols:
                    original = row[col]
                    new_val, changed = _rewrite_value(original, prefix)
                    if changed:
                        updates[col] = new_val
                if not updates:
                    continue

                stats["rows"] += 1
                stats["columns"] += len(updates)
                if dry_run:
                    continue

                set_clause = ", ".join(f"{col} = ?" for col in updates)
                params = list(updates.values()) + [row["rowid"]]
                conn.execute(
                    f"UPDATE {table} SET {set_clause} WHERE rowid = ?",
                    params,
                )

        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reprocess URL uploads/migrate trong DB AI Web (Nginx root deploy)",
    )
    parser.add_argument("--env", type=Path, default=Path(__file__).resolve().parents[1] / "config.env")
    parser.add_argument("--db", type=Path, help="Override path tới landing_pages.db")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--prefix",
        help="Override MIGRATION_UPLOAD_PREFIX (mặc định: aiweb_core/uploads khi USE_NGINX_ROOT_PATH=1)",
    )
    args = parser.parse_args()

    load_env_file(args.env)
    load_default_env()

    prefix = args.prefix or get_migration_upload_prefix()
    if prefix == "uploads" and not args.prefix:
        print(
            "Prefix vẫn là 'uploads'. "
            "Đặt MIGRATION_USE_NGINX_ROOT_PATH=1 hoặc MIGRATION_UPLOAD_PREFIX=aiweb_core/uploads trong config.env"
        )
        return 1

    db_path = args.db or aiweb_db_path()
    if not db_path.is_file():
        print(f"Không tìm thấy DB: {db_path}")
        return 1

    print(f"DB: {db_path}")
    print(f"Prefix: {prefix}")
    print(f"Client-side rewrite mode: {use_client_side_asset_rewrite()}")
    print(f"Dry run: {args.dry_run}")

    stats = reprocess_db(db_path, prefix, args.dry_run)
    print("Done:", stats)
    if args.dry_run:
        print("(dry-run — không ghi DB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
