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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.env_config import load_env_file, use_client_side_asset_rewrite  # noqa: E402
from lib.migration_api import api_call, ping_migration_api  # noqa: E402
from lib.migration_urls import rewrite_migrated_field, rewrite_migrated_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
LOG_PATH = OUTPUT_DIR / "slimcrm_import_log.jsonl"

DEFAULT_BASE = "http://localhost/aiweb"
ASSET_BATCH_SIZE = 40


def fetch_asset_map(
    client: httpx.Client,
    base: str,
    key: str,
    source_domain: str,
) -> dict:
    result = api_call(
        client,
        base,
        key,
        {"action": "get_asset_map", "source_domain": source_domain},
    )
    if not result.get("success"):
        return {}
    raw = result.get("map") or {}
    return raw if isinstance(raw, dict) else {}


def prepare_content_fields(
    fields: dict[str, str],
    asset_map: dict,
    client_rewrite: bool,
) -> dict[str, str]:
    if not client_rewrite:
        return fields

    prepared = dict(fields)
    for name in ("html_content", "content", "description"):
        if name in prepared and prepared[name]:
            prepared[name], _ = rewrite_migrated_text(prepared[name], asset_map)
    for name in ("seo_favicon", "seo_og_image", "featured_image"):
        if name in prepared and prepared[name]:
            prepared[name] = rewrite_migrated_field(prepared[name], asset_map)
    return prepared


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
        "product_categories": 0,
        "products": 0,
        "assets_ok": 0,
        "assets_failed": 0,
        "errors": 0,
    }

    assets = manifest.get("assets") or []
    if assets:
        ok, failed = import_assets(client, base, key, source_domain, assets, dry_run, log_path)
        stats["assets_ok"] += ok
        stats["assets_failed"] += failed

    client_rewrite = use_client_side_asset_rewrite()
    asset_map: dict = {}
    if client_rewrite:
        asset_map = fetch_asset_map(client, base, key, source_domain)
        if not asset_map:
            print(
                f"  Warning: MIGRATION_USE_NGINX_ROOT_PATH bật nhưng asset map rỗng "
                f"cho {source_domain} — URL có thể chưa được rewrite đúng."
            )

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
        page_fields = prepare_content_fields(
            {
                "html_content": page.get("html_content", ""),
                "seo_favicon": page.get("seo_favicon", ""),
                "seo_og_image": page.get("seo_og_image", ""),
            },
            asset_map,
            client_rewrite,
        )
        payload = {
            "action": "upsert_landing",
            "source_domain": source_domain,
            "source_key": source_key,
            "slug": page["slug"],
            "title": page["title"],
            "html_content": page_fields.get("html_content", ""),
            "seo_description": page.get("seo_description", ""),
            "seo_keywords": page.get("seo_keywords", ""),
            "seo_favicon": page_fields.get("seo_favicon", ""),
            "seo_og_image": page_fields.get("seo_og_image", ""),
            "language": page.get("language", "vi"),
            "is_published": True if publish else page.get("is_published", False),
            "rewrite_assets": not client_rewrite,
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
        post_fields = prepare_content_fields(
            {
                "content": post.get("content", ""),
                "featured_image": post.get("featured_image", ""),
            },
            asset_map,
            client_rewrite,
        )
        payload = {
            "action": "upsert_blog_post",
            "source_domain": source_domain,
            "source_key": source_key,
            "slug": post["slug"],
            "title": post["title"],
            "content": post_fields.get("content", ""),
            "category_slug": post.get("category_slug", ""),
            "featured_image": post_fields.get("featured_image", ""),
            "status": "published" if publish else post.get("status", "draft"),
            "published_at": post.get("published_at", ""),
            "seo_description": post.get("seo_description", ""),
            "language": post.get("language", "vi"),
            "rewrite_assets": not client_rewrite,
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

    for cat in manifest.get("product_categories") or []:
        source_key = cat["source_key"]
        if already_imported(log_path, "upsert_product_category", source_key, source_domain):
            continue
        payload = {
            "action": "upsert_product_category",
            "source_domain": source_domain,
            "source_key": source_key,
            "name": cat["name"],
            "slug": cat["slug"],
            "sort_order": cat.get("sort_order", 0),
            "dry_run": dry_run,
        }
        result = api_call(client, base, key, payload)
        ok = bool(result.get("success"))
        if ok:
            stats["product_categories"] += 1
        else:
            stats["errors"] += 1
        log_event(
            log_path,
            {
                "action": "upsert_product_category",
                "source_domain": source_domain,
                "source_key": source_key,
                "ok": ok,
                "error": result.get("error"),
                "dry_run": dry_run,
            },
        )
        time.sleep(0.2)

    for product in manifest.get("products") or []:
        source_key = product["source_key"]
        if already_imported(log_path, "upsert_product", source_key, source_domain):
            continue
        product_fields = prepare_content_fields(
            {"description": product.get("description", "")},
            asset_map,
            client_rewrite,
        )
        images = product.get("images", [])
        if client_rewrite and isinstance(images, list):
            images = [
                rewrite_migrated_field(str(img), asset_map) if isinstance(img, str) else img
                for img in images
            ]
        payload = {
            "action": "upsert_product",
            "source_domain": source_domain,
            "source_key": source_key,
            "slug": product["slug"],
            "name": product["name"],
            "description": product_fields.get("description", ""),
            "price": product.get("price", 0),
            "status": product.get("status", "available"),
            "category_slug": product.get("category_slug", ""),
            "category_key": product.get("category_key", ""),
            "images": images,
            "sort_order": product.get("sort_order", 0),
            "rewrite_assets": not client_rewrite,
            "dry_run": dry_run,
        }
        result = api_call(client, base, key, payload)
        ok = bool(result.get("success"))
        if ok:
            stats["products"] += 1
        else:
            stats["errors"] += 1
        log_event(
            log_path,
            {
                "action": "upsert_product",
                "source_domain": source_domain,
                "source_key": source_key,
                "ok": ok,
                "error": result.get("error"),
                "dry_run": dry_run,
            },
        )
        time.sleep(0.2)

    return stats


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
    if use_client_side_asset_rewrite():
        from lib.env_config import get_migration_upload_prefix

        print(f"Nginx root mode: URL prefix = {get_migration_upload_prefix()}")
    if not key:
        print("Missing MIGRATION_API_KEY. Copy config.example.env to config.env")
        return 1

    with httpx.Client() as client:
        ok, ping_error = ping_migration_api(client, base, key)
        if not ok:
            print(f"Migration API ping failed for {base}")
            if ping_error:
                print(ping_error)
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
            "product_categories": 0,
            "products": 0,
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
                totals[k] = totals.get(k, 0) + v
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
