"""URL công khai cho asset migrate — hỗ trợ Nginx root (aiweb_core/uploads)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from lib.env_config import DEFAULT_UPLOAD_PREFIX, get_migration_upload_prefix

_MIGRATE_PATH_RE = re.compile(
    r"(?P<prefix>/uploads/migrate/|uploads/migrate/|(?<![\w/])uploads/migrate/)",
    re.IGNORECASE,
)


def _strip_uploads_prefix(local_path: str) -> str:
    path = (local_path or "").strip().replace("\\", "/").lstrip("/")
    return re.sub(r"^uploads/", "", path, flags=re.IGNORECASE)


def migration_public_relative(local_path: str, prefix: str | None = None) -> str:
    """Path tương đối site root, không dấu / đầu: aiweb_core/uploads/migrate/..."""
    upload_prefix = normalize_upload_prefix(prefix or get_migration_upload_prefix())
    rel = _strip_uploads_prefix(local_path)
    return f"{upload_prefix}/{rel}" if rel else upload_prefix


def migration_public_absolute(local_path: str, prefix: str | None = None) -> str:
    """Path tuyệt đối: /aiweb_core/uploads/migrate/..."""
    return "/" + migration_public_relative(local_path, prefix)


def normalize_upload_prefix(prefix: str) -> str:
    cleaned = (prefix or DEFAULT_UPLOAD_PREFIX).strip().strip("/").replace("\\", "/")
    return cleaned or DEFAULT_UPLOAD_PREFIX


def apply_upload_prefix_to_text(text: str, target_prefix: str | None = None) -> str:
    """
    Đổi uploads/migrate/ → aiweb_core/uploads/migrate/ trong HTML đã import trước đó.
    Chỉ đụng path migrate; không thay URL ngoài hoặc path đã có aiweb_core/uploads.
    """
    if not text:
        return text

    prefix = normalize_upload_prefix(target_prefix or get_migration_upload_prefix())
    if prefix == DEFAULT_UPLOAD_PREFIX:
        return text
    if "aiweb_core/uploads/" in text.lower():
        return text

    def repl(match: re.Match[str]) -> str:
        matched = match.group("prefix")
        if matched.startswith("/"):
            return f"/{prefix}/migrate/"
        return f"{prefix}/migrate/"

    return _MIGRATE_PATH_RE.sub(repl, text)


def build_replacement_map(
    asset_map: dict[str, Any],
    prefix: str | None = None,
) -> dict[str, str]:
    """
    Map source URL / path cũ → path công khai mới (absolute /prefix/...).
    """
    upload_prefix = normalize_upload_prefix(prefix or get_migration_upload_prefix())
    replacements: dict[str, str] = {}

    for source_url, info in asset_map.items():
        if not isinstance(info, dict):
            continue
        local_path = _strip_uploads_prefix(str(info.get("local_path") or ""))
        if not local_path:
            continue

        target_abs = migration_public_absolute(local_path, upload_prefix)
        target_rel = migration_public_relative(local_path, upload_prefix)

        candidates = {
            str(source_url or "").strip(),
            str(source_url or "").strip().rstrip("/"),
            str(info.get("public_url") or "").strip(),
            str(info.get("public_url") or "").strip().rstrip("/"),
            f"uploads/{local_path}",
            f"/uploads/{local_path}",
        }

        pub = str(info.get("public_url") or "")
        if pub:
            parsed = urlparse(pub)
            if parsed.path:
                candidates.add(parsed.path)
                candidates.add(parsed.path.rstrip("/"))

        for key in candidates:
            if not key or key == target_abs or key == target_rel:
                continue
            replacements[key] = target_abs

    return replacements


def rewrite_text_with_map(text: str, replacements: dict[str, str]) -> tuple[str, int]:
    if not text or not replacements:
        return text, 0

    count = 0
    result = text
    for source in sorted(replacements.keys(), key=len, reverse=True):
        target = replacements[source]
        if not source or source == target or source not in result:
            continue
        result = result.replace(source, target)
        count += 1
    return result, count


def rewrite_migrated_text(
    text: str,
    asset_map: dict[str, Any] | None = None,
    prefix: str | None = None,
) -> tuple[str, int]:
    """Rewrite HTML/text: asset map + prefix swap uploads/migrate."""
    upload_prefix = normalize_upload_prefix(prefix or get_migration_upload_prefix())
    if upload_prefix == DEFAULT_UPLOAD_PREFIX and not asset_map:
        return text, 0

    total = 0
    result = text
    if asset_map:
        repl = build_replacement_map(asset_map, upload_prefix)
        result, n = rewrite_text_with_map(result, repl)
        total += n
    result = apply_upload_prefix_to_text(result, upload_prefix)
    if result != text and total == 0:
        total = 1
    return result, total


def rewrite_migrated_field(
    value: str,
    asset_map: dict[str, Any] | None = None,
    prefix: str | None = None,
) -> str:
    if not value or value.startswith(("http://", "https://", "data:")):
        if value and asset_map and value in build_replacement_map(asset_map, prefix):
            return build_replacement_map(asset_map, prefix)[value]
        if value and (value.startswith("http://") or value.startswith("https://")):
            parsed = urlparse(value)
            path = parsed.path or ""
            if asset_map:
                repl = build_replacement_map(asset_map, prefix)
                if path in repl:
                    return repl[path]
            rewritten = apply_upload_prefix_to_text(path, prefix)
            if rewritten != path:
                return f"{parsed.scheme}://{parsed.netloc}{rewritten}"
        return value

    rewritten, _ = rewrite_migrated_text(value, asset_map, prefix)
    return rewritten
