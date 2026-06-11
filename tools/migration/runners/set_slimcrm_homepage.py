#!/usr/bin/env python3
"""Gan trang chu SlimCRM (migration source_key=index) lam homepage AI Web."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.paths import aiweb_db_path, load_default_env  # noqa: E402

load_default_env()
DB = aiweb_db_path()


def main() -> int:
    if not DB.exists():
        print(f"DB not found: {DB}")
        return 1

    conn = sqlite3.connect(DB)
    row = conn.execute(
        """
        SELECT local_id FROM migration_entities
        WHERE source_domain = 'slimcrm.vn'
          AND entity_type = 'landing'
          AND source_key = 'index'
        LIMIT 1
        """
    ).fetchone()

    if not row:
        page = conn.execute(
            "SELECT id FROM landing_pages WHERE product_name = 'home' LIMIT 1"
        ).fetchone()
        if not page:
            print("Chua tim thay landing home/index")
            return 1
        page_id = page[0]
    else:
        page_id = row[0]

    conn.execute(
        """
        INSERT INTO global_settings (setting_key, setting_value, updated_at)
        VALUES ('default_index_page', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(setting_key) DO UPDATE SET
            setting_value = excluded.setting_value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (str(page_id),),
    )
    conn.commit()
    print(f"default_index_page = {page_id} (slimcrm home)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
