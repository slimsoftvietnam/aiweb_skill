"""Resolve đường dẫn tới cài đặt AI Web (repo aiweb riêng)."""

from __future__ import annotations

import os
from pathlib import Path

MIGRATION_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = MIGRATION_ROOT.parent
SKILL_REPO_ROOT = TOOLS_ROOT.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def resolve_aiweb_root() -> Path:
    """Thư mục gốc chứa aiweb_core/ (repo aiweb)."""
    env_path = os.environ.get("AIWEB_ROOT", "").strip()
    if env_path:
        root = Path(env_path).expanduser().resolve()
        if (root / "aiweb_core").is_dir():
            return root

    for candidate in (
        SKILL_REPO_ROOT,  # monorepo: aiweb/tools/migration
        SKILL_REPO_ROOT.parent / "aiweb",  # sibling: aiweb_skill + aiweb
        Path.cwd(),
        Path.cwd().parent,
    ):
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if (resolved / "aiweb_core").is_dir():
            return resolved

    return SKILL_REPO_ROOT


def aiweb_db_path() -> Path:
    return resolve_aiweb_root() / "aiweb_core" / "data" / "landing_pages.db"


def aiweb_upload_dir() -> Path:
    return resolve_aiweb_root() / "aiweb_core" / "uploads" / "upload"


def load_default_env() -> None:
    _load_env_file(MIGRATION_ROOT / "config.env")
