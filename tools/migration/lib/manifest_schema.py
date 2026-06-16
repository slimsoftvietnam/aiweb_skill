"""Lightweight manifest validation."""

from __future__ import annotations

from typing import Any


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not data.get("source_domain"):
        errors.append("missing source_domain")

    for key in ("categories", "assets", "landing_pages", "blog_posts"):
        if key not in data:
            errors.append(f"missing {key}")
        elif not isinstance(data[key], list):
            errors.append(f"{key} must be a list")

    for key in ("product_categories", "products"):
        if key in data and not isinstance(data[key], list):
            errors.append(f"{key} must be a list")

    for i, cat in enumerate(data.get("categories") or []):
        for field in ("source_key", "name", "slug"):
            if not cat.get(field):
                errors.append(f"categories[{i}] missing {field}")

    for i, page in enumerate(data.get("landing_pages") or []):
        for field in ("source_key", "slug", "title"):
            if not page.get(field):
                errors.append(f"landing_pages[{i}] missing {field}")
        if not page.get("html_content") and not page.get("sections"):
            errors.append(f"landing_pages[{i}] missing html_content")

    for i, post in enumerate(data.get("blog_posts") or []):
        for field in ("source_key", "slug", "title"):
            if not post.get(field):
                errors.append(f"blog_posts[{i}] missing {field}")

    for i, cat in enumerate(data.get("product_categories") or []):
        for field in ("source_key", "name", "slug"):
            if not cat.get(field):
                errors.append(f"product_categories[{i}] missing {field}")

    for i, product in enumerate(data.get("products") or []):
        for field in ("source_key", "slug", "name"):
            if not product.get(field):
                errors.append(f"products[{i}] missing {field}")

    return errors
