"""Đọc config.env cho pipeline migrate."""

from __future__ import annotations

import os
from pathlib import Path

MIGRATION_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_UPLOAD_PREFIX = "uploads"
NGINX_ROOT_UPLOAD_PREFIX = "aiweb_core/uploads"


def load_env_file(path: Path | None = None) -> None:
    env_path = path or (MIGRATION_ROOT / "config.env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def normalize_upload_prefix(prefix: str) -> str:
    cleaned = (prefix or DEFAULT_UPLOAD_PREFIX).strip().strip("/").replace("\\", "/")
    return cleaned or DEFAULT_UPLOAD_PREFIX


def get_migration_upload_prefix() -> str:
    """
    Prefix URL công khai cho file migrate trên AI Web.

    - uploads (mặc định): Apache / local — .htaccess rewrite /uploads/ → aiweb_core/uploads/
    - aiweb_core/uploads: Nginx root — serve trực tiếp không cần rewrite
    """
    explicit = os.environ.get("MIGRATION_UPLOAD_PREFIX", "").strip()
    if explicit:
        return normalize_upload_prefix(explicit)

    flag = os.environ.get("MIGRATION_USE_NGINX_ROOT_PATH", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return NGINX_ROOT_UPLOAD_PREFIX

    return DEFAULT_UPLOAD_PREFIX


def use_client_side_asset_rewrite() -> bool:
    """True khi prefix khác uploads — tránh API ghi đè lại bằng uploads/."""
    return get_migration_upload_prefix() != DEFAULT_UPLOAD_PREFIX
