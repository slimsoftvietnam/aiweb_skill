"""HTTP helpers for AI Web Migration / Agent API."""

from __future__ import annotations

import time
from typing import Any

import httpx

LICENSE_ERROR = "License required"


def license_hint() -> str:
    return (
        "Site chưa kích hoạt bản quyền (license). "
        "Vào /activate_license trên AIPage, kích hoạt key cho domain này, rồi chạy lại."
    )


def is_license_error(status_code: int, data: dict[str, Any]) -> bool:
    if status_code != 403:
        return False
    err = str(data.get("error") or "").lower()
    msg = str(data.get("message") or "").lower()
    return "license" in err or "license" in msg or "bản quyền" in msg


def migration_api_url(base: str, query_action: str | None = None) -> str:
    root = base.rstrip("/")
    url = f"{root}/api/migration.php"
    if query_action:
        url = f"{url}?action={query_action}"
    return url


def api_call(
    client: httpx.Client,
    base: str,
    key: str,
    payload: dict[str, Any],
    retries: int = 3,
) -> dict[str, Any]:
    url = migration_api_url(base)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    last_error = ""
    for attempt in range(retries):
        try:
            resp = client.post(url, headers=headers, json=payload, timeout=120.0)
            data = resp.json() if resp.content else {}
            if is_license_error(resp.status_code, data):
                return {
                    "success": False,
                    "error": LICENSE_ERROR,
                    "message": data.get("message") or license_hint(),
                }
            if resp.status_code >= 400 and not data.get("success"):
                last_error = data.get("error") or data.get("message") or resp.text
                time.sleep(1.0 * (attempt + 1))
                continue
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(1.0 * (attempt + 1))
    return {"success": False, "error": last_error or "unknown error"}


def ping_migration_api(client: httpx.Client, base: str, key: str) -> tuple[bool, str]:
    url = migration_api_url(base, "ping")
    headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = client.get(url, headers=headers, timeout=30.0)
        data = resp.json() if resp.content else {}
        if is_license_error(resp.status_code, data):
            return False, data.get("message") or license_hint()
        if bool(data.get("success")):
            return True, ""
        return False, data.get("error") or data.get("message") or resp.text
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
