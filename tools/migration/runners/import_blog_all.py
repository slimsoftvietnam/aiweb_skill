#!/usr/bin/env python3
"""Extract + import toàn bộ blog slimcrm.vn theo batch."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
INVENTORY = OUTPUT / "slimcrm_blog_inventory.json"
EXTRACT = ROOT / "scrapers" / "slimcrm_blog_extract.py"
IMPORT = ROOT / "runners" / "import_manifest.py"


def build_categories_manifest() -> Path:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    seen: dict[str, str] = {}
    for p in inv.get("posts") or []:
        name = (p.get("category_name") or "").split(",")[0].strip()
        slug = p.get("category_slug") or ""
        if name and slug:
            seen[slug] = name
    out = OUTPUT / "slimcrm_blog_categories.json"
    manifest = {
        "source_domain": "slimcrm.vn",
        "categories": [
            {"source_key": s, "name": n, "slug": s, "description": ""}
            for s, n in sorted(seen.items())
        ],
        "assets": [],
        "landing_pages": [],
        "blog_posts": [],
    }
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=ROOT / "config.env")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--import-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not INVENTORY.exists():
        print("Chạy slimcrm_blog_scan.py trước")
        return 1

    py = sys.executable
    env_flag = ["--env", str(args.env)]

    if not args.import_only:
        cat_manifest = build_categories_manifest()
        cats = json.loads(cat_manifest.read_text(encoding="utf-8"))["categories"]
        print(f"Categories manifest: {cat_manifest} ({len(cats)} cats)")
        rc = run(
            [
                py,
                str(IMPORT),
                "--file",
                str(cat_manifest),
                *env_flag,
                *(["--dry-run"] if args.dry_run else ["--publish"]),
            ]
        )
        if rc:
            return rc

        rc = run(
            [
                py,
                str(EXTRACT),
                "--batch-size",
                str(args.batch_size),
            ]
        )
        if rc:
            return rc

    if args.extract_only:
        return 0

    batches = sorted(OUTPUT.glob("slimcrm_blog_manifest_batch_*.json"))
    if not batches:
        single = OUTPUT / "slimcrm_blog_manifest.json"
        if not single.exists():
            print("Không tìm thấy manifest blog")
            return 1
        batches = [single]

    for manifest in batches:
        rc = run(
            [
                py,
                str(IMPORT),
                "--file",
                str(manifest),
                *env_flag,
                *(["--dry-run"] if args.dry_run else ["--publish"]),
            ]
        )
        if rc:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
