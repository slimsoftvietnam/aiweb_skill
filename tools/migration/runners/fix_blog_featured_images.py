#!/usr/bin/env python3
"""Sửa ảnh đại diện blog: tải từ inventory URL đúng → upload local."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lib.paths import aiweb_db_path, aiweb_upload_dir, load_default_env  # noqa: E402

load_default_env()
DB = aiweb_db_path()
UPLOAD_DIR = aiweb_upload_dir()
INVENTORY = ROOT / "output" / "slimcrm_blog_inventory.json"
SOURCE_DOMAIN = "slimcrm.vn"

from lib.html_utils import resolve_slimweb_file_url  # noqa: E402

MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}


def guess_ext(mime: str, url: str) -> str:
    mime = (mime or "").split(";")[0].strip().lower()
    if mime in MIME_EXT:
        return MIME_EXT[mime]
    path = urlparse(url).path
    ext = Path(path).suffix.lstrip(".").lower()
    return ext if ext in {"jpg", "jpeg", "png", "gif", "webp", "svg"} else "jpg"


def candidate_urls(slug: str, current: str, inv_image: str) -> list[str]:
    out: list[str] = []
    for raw in (inv_image, current):
        if not raw:
            continue
        if raw.startswith("//"):
            raw = "https:" + raw
        out.append(raw)
        resolved = resolve_slimweb_file_url(raw)
        if resolved and resolved not in out:
            out.append(resolved)
    return out


def download_image(client: httpx.Client, url: str) -> tuple[bytes, str] | None:
    try:
        resp = client.get(url, follow_redirects=True, timeout=60)
        if resp.status_code != 200:
            return None
        mime = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if not mime.startswith("image/"):
            return None
        return resp.content, mime
    except Exception:  # noqa: BLE001
        return None


def save_upload(body: bytes, mime: str, source_url: str) -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1(body).hexdigest()[:12]
    ext = guess_ext(mime, source_url)
    name = f"mig_{h}.{ext}"
    dest = UPLOAD_DIR / name
    if not dest.exists():
        dest.write_bytes(body)
    return f"upload/{name}"


def main() -> int:
    if not INVENTORY.exists():
        print("Missing inventory")
        return 1

    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    by_slug = {p["slug"]: p.get("image", "") for p in inv.get("posts", [])}

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, slug, featured_image FROM posts WHERE featured_image LIKE 'http%'"
    ).fetchall()

    print(f"Posts to fix: {len(rows)}")
    ok = 0
    fail = 0

    with httpx.Client(headers={"User-Agent": "AIWeb-Migration/1.0"}) as client:
        for row in rows:
            slug = row["slug"]
            current = row["featured_image"] or ""
            inv_img = by_slug.get(slug, "")
            local_path = ""
            used_url = ""
            body = b""
            mime = ""

            for url in candidate_urls(slug, current, inv_img):
                got = download_image(client, url)
                if not got:
                    continue
                body, mime = got
                local_path = save_upload(body, mime, url)
                used_url = url
                break

            if not local_path:
                print(f"  FAIL {slug}")
                fail += 1
                continue
            conn.execute(
                "UPDATE posts SET featured_image = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (local_path, row["id"]),
            )
            norm = resolve_slimweb_file_url(used_url) or used_url.split("?")[0]
            conn.execute(
                """
                INSERT INTO migration_assets (source_domain, source_url, local_path, content_hash, mime_type, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_domain, source_url) DO UPDATE SET
                    local_path = excluded.local_path,
                    content_hash = excluded.content_hash,
                    mime_type = excluded.mime_type,
                    file_size = excluded.file_size
                """,
                (
                    SOURCE_DOMAIN,
                    norm,
                    local_path,
                    hashlib.sha1(body).hexdigest(),
                    mime,
                    len(body),
                ),
            )
            print(f"  OK {slug} -> {local_path}")
            ok += 1

    conn.commit()
    print(f"Done: ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
