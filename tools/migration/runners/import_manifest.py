#!/usr/bin/env python3
"""Import manifest JSON files via AI Web Migration API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
LOG_PATH = OUTPUT_DIR / "slimcrm_import_log.jsonl"

DEFAULT_BASE = "http://localhost/aiweb"
ASSET_BATCH_SIZE = 40


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def api_call(
    client: httpx.Client,
    base: str,
    key: str,
    payload: dict[str, Any],
    retries: int = 3,
) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/api/migration.php"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    last_error = ""
    for attempt in range(retries):
        try:
            resp = client.post(url, headers=headers, json=payload, timeout=120.0)
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400 and not data.get("success"):
                last_error = data.get("error") or resp.text
                time.sleep(1.0 * (attempt + 1))
                continue
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(1.0 * (attempt + 1))
    return {"success": False, "error": last_error or "unknown error"}


def log_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def already_imported(log_path: Path, action: str, source_key: str, source_domain: str) -> bool:
    if not log_path.exists():
        return False
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (
            row.get("ok")
            and not row.get("dry_run")
            and row.get("action") == action
            and row.get("source_key") == source_key
            and row.get("source_domain") == source_domain
        ):
            return True
    return False


def import_assets(
    client: httpx.Client,
    base: str,
    key: str,
    source_domain: str,
    assets: list[dict[str, str]],
    dry_run: bool,
    log_path: Path,
) -> tuple[int, int]:
    ok = 0
    failed = 0
    urls = [a["source_url"] for a in assets if a.get("source_url")]
    for i in range(0, len(urls), ASSET_BATCH_SIZE):
        batch = [{"source_url": u} for u in urls[i : i + ASSET_BATCH_SIZE]]
        payload = {
            "action": "import_assets",
            "source_domain": source_domain,
            "items": batch,
            "dry_run": dry_run,
        }
        result = api_call(client, base, key, payload)
        success = bool(result.get("success"))
        imported = int(result.get("imported", 0))
        batch_failed = int(result.get("failed", 0))
        if success:
            ok += imported
            failed += batch_failed
        else:
            failed += len(batch)
        log_event(
            log_path,
            {
                "action": "import_assets",
                "source_domain": source_domain,
                "batch_start": i,
                "batch_size": len(batch),
                "ok": success,
                "imported": imported,
                "failed": batch_failed,
                "error": result.get("error"),
                "dry_run": dry_run,
            },
        )
        time.sleep(0.25)
    return ok, failed


def import_manifest_file(
    client: httpx.Client,
    base: str,
    key: str,
    manifest_path: Path,
    dry_run: bool,
    log_path: Path,
    publish: bool,
    force_upsert: bool = False,
) -> dict[str, int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_domain = manifest.get("source_domain", "slimcrm.vn")
    stats = {
        "categories": 0,
        "landings": 0,
        "blog_posts": 0,
        "assets_ok": 0,
        "assets_failed": 0,
        "errors": 0,
    }

    assets = manifest.get("assets") or []
    if assets:
        ok, failed = import_assets(client, base, key, source_domain, assets, dry_run, log_path)
        stats["assets_ok"] += ok
        stats["assets_failed"] += failed

    for cat in manifest.get("categories") or []:
        source_key = cat["source_key"]
        if already_imported(log_path, "upsert_category", source_key, source_domain):
            continue
        payload = {
            "action": "upsert_category",
            "source_domain": source_domain,
            "source_key": source_key,
            "name": cat["name"],
            "slug": cat["slug"],
            "description": cat.get("description", ""),
            "dry_run": dry_run,
        }
        result = api_call(client, base, key, payload)
        ok = bool(result.get("success"))
        if ok:
            stats["categories"] += 1
        else:
            stats["errors"] += 1
        log_event(
            log_path,
            {
                "action": "upsert_category",
                "source_domain": source_domain,
                "source_key": source_key,
                "ok": ok,
                "error": result.get("error"),
                "dry_run": dry_run,
            },
        )
        time.sleep(0.2)

    for page in manifest.get("landing_pages") or []:
        source_key = page["source_key"]
        if not force_upsert and already_imported(log_path, "upsert_landing", source_key, source_domain):
            continue
        payload = {
            "action": "upsert_landing",
            "source_domain": source_domain,
            "source_key": source_key,
            "slug": page["slug"],
            "title": page["title"],
            "html_content": page.get("html_content", ""),
            "seo_description": page.get("seo_description", ""),
            "seo_keywords": page.get("seo_keywords", ""),
            "seo_favicon": page.get("seo_favicon", ""),
            "seo_og_image": page.get("seo_og_image", ""),
            "language": page.get("language", "vi"),
            "is_published": True if publish else page.get("is_published", False),
            "rewrite_assets": True,
            "dry_run": dry_run,
        }
        result = api_call(client, base, key, payload)
        ok = bool(result.get("success"))
        if ok:
            stats["landings"] += 1
        else:
            stats["errors"] += 1
        log_event(
            log_path,
            {
                "action": "upsert_landing",
                "source_domain": source_domain,
                "source_key": source_key,
                "ok": ok,
                "error": result.get("error"),
                "dry_run": dry_run,
            },
        )
        time.sleep(0.2)

    for post in manifest.get("blog_posts") or []:
        source_key = post["source_key"]
        if already_imported(log_path, "upsert_blog_post", source_key, source_domain):
            continue
        payload = {
            "action": "upsert_blog_post",
            "source_domain": source_domain,
            "source_key": source_key,
            "slug": post["slug"],
            "title": post["title"],
            "content": post.get("content", ""),
            "category_slug": post.get("category_slug", ""),
            "featured_image": post.get("featured_image", ""),
            "status": "published" if publish else post.get("status", "draft"),
            "published_at": post.get("published_at", ""),
            "seo_description": post.get("seo_description", ""),
            "language": post.get("language", "vi"),
            "rewrite_assets": True,
            "dry_run": dry_run,
        }
        result = api_call(client, base, key, payload)
        ok = bool(result.get("success"))
        if ok:
            stats["blog_posts"] += 1
        else:
            stats["errors"] += 1
        log_event(
            log_path,
            {
                "action": "upsert_blog_post",
                "source_domain": source_domain,
                "source_key": source_key,
                "ok": ok,
                "error": result.get("error"),
                "dry_run": dry_run,
            },
        )
        time.sleep(0.2)

    return stats


def ping(client: httpx.Client, base: str, key: str) -> bool:
    url = f"{base.rstrip('/')}/api/migration.php?action=ping"
    headers = {"Authorization": f"Bearer {key}"}
    resp = client.get(url, headers=headers, timeout=30.0)
    data = resp.json() if resp.content else {}
    return bool(data.get("success"))


def list_entities(client: httpx.Client, base: str, key: str, source_domain: str) -> dict:
    payload = {"action": "list_entities", "source_domain": source_domain}
    return api_call(client, base, key, payload)


def collect_manifest_files(paths: list[Path], glob_pattern: str | None) -> list[Path]:
    files: list[Path] = []
    if glob_pattern:
        files.extend(sorted(ROOT.glob(glob_pattern)))
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.glob("*.json")))
        else:
            files.append(p)
    # stable unique order
    seen: set[str] = set()
    ordered: list[Path] = []
    for f in files:
        key = str(f.resolve())
        if key not in seen:
            seen.add(key)
            ordered.append(f)
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description="Import slimcrm manifest via Migration API")
    parser.add_argument("--file", action="append", type=Path, help="Manifest JSON file")
    parser.add_argument("--glob", help="Glob under tools/migration, e.g. output/slimcrm_manifest_*_landing.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Publish landings and blog posts")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run upserts even if import log shows success (use with --publish)",
    )
    parser.add_argument("--env", type=Path, default=ROOT / "config.env")
    parser.add_argument("--ping-only", action="store_true")
    args = parser.parse_args()

    load_env_file(args.env)
    base = os.environ.get("AIWEB_BASE", DEFAULT_BASE).rstrip("/")
    key = os.environ.get("MIGRATION_API_KEY", "")
    if not key:
        print("Missing MIGRATION_API_KEY. Copy config.example.env to config.env")
        return 1

    with httpx.Client() as client:
        if not ping(client, base, key):
            print(f"Migration API ping failed for {base}")
            return 1
        print(f"Migration API OK: {base}")

        if args.ping_only:
            return 0

        files = collect_manifest_files(args.file or [], args.glob)
        if not files:
            print("No manifest files specified. Use --file or --glob")
            return 1

        totals = {
            "categories": 0,
            "landings": 0,
            "blog_posts": 0,
            "assets_ok": 0,
            "assets_failed": 0,
            "errors": 0,
        }
        for manifest_path in files:
            print(f"Importing {manifest_path} (dry_run={args.dry_run})")
            stats = import_manifest_file(
                client,
                base,
                key,
                manifest_path,
                args.dry_run,
                LOG_PATH,
                args.publish,
                force_upsert=args.force,
            )
            for k, v in stats.items():
                totals[k] += v
            print(f"  -> {stats}")

        domains = ["slimcrm.vn"]
        if any("blog.slimcrm.vn" == json.loads(f.read_text(encoding="utf-8")).get("source_domain") for f in files):
            domains.append("blog.slimcrm.vn")
        for domain in domains:
            entities = list_entities(client, base, key, domain)
            count = len(entities.get("entities") or [])
            print(f"list_entities {domain}: {count}")

        print("Totals:", totals)
        if args.dry_run:
            print("(dry-run mode — no DB writes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
