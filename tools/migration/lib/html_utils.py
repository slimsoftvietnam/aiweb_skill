"""URL normalization and asset extraction from HTML."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
SKIP_HOSTS = {
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "www.googletagmanager.com",
    "www.google-analytics.com",
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
}
MIGRATABLE_HOSTS = {
    "slimcrm.vn",
    "www.slimcrm.vn",
    "blog.slimcrm.vn",
    "slimweb.vn",
    "www.slimweb.vn",
    "ai.slim.vn",
    "www.ai.slim.vn",
}


def slugify_vi(text: str, max_len: int = 80) -> str:
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return (text[:max_len].strip("-") or "khac")


def page_base_url(page_url: str) -> str:
    """Directory base for resolving relative assets on a static .html page."""
    parsed = urlparse(page_url)
    path = parsed.path or "/"
    if path.endswith(".html"):
        path = path.rsplit("/", 1)[0] + "/"
    elif not path.endswith("/"):
        path += "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def normalize_url(url: str, base: str) -> str:
    url = (url or "").strip()
    if not url or url.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith(("http://", "https://")):
        url = urljoin(page_base_url(base) if base.startswith("http") else base, url)
    parsed = urlparse(url)
    scheme = "https" if parsed.scheme in ("http", "https") else parsed.scheme
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def normalize_html_urls(html: str, base_url: str) -> str:
    """Rewrite relative and http URLs to absolute https in HTML string."""
    soup = BeautifulSoup(html, "lxml")
    base = page_base_url(base_url)

    for tag in soup.find_all(True):
        for attr in ("href", "src", "content", "data-src"):
            if not tag.has_attr(attr):
                continue
            val = tag.get(attr)
            if not isinstance(val, str):
                continue
            if attr == "content" and tag.name == "meta":
                if not val.startswith(("http://", "https://", "/")):
                    continue
            normalized = normalize_url(val, base)
            if normalized:
                tag[attr] = normalized

        if tag.has_attr("srcset"):
            srcset = tag["srcset"]
            if isinstance(srcset, str):
                parts = []
                for item in srcset.split(","):
                    item = item.strip()
                    if not item:
                        continue
                    bits = item.split()
                    bits[0] = normalize_url(bits[0], base) or bits[0]
                    parts.append(" ".join(bits))
                tag["srcset"] = ", ".join(parts)

    style_tags = soup.find_all("style")
    for style in style_tags:
        if style.string:
            style.string = _normalize_css_urls(style.string, base)

    for tag in soup.find_all(style=True):
        tag["style"] = _normalize_css_urls(tag["style"], base)

    return str(soup)


def _normalize_css_urls(css: str, base: str) -> str:
    def repl(match: re.Match[str]) -> str:
        raw = match.group(1).strip("'\"")
        normalized = normalize_url(raw, base)
        return f"url({normalized})" if normalized else match.group(0)

    return re.sub(r"url\(([^)]+)\)", repl, css)


def resolve_slimweb_file_url(url: str) -> str:
    """Chuyển URL Drupal image style → file gốc trên slimweb.vn."""
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    m = re.search(r"/sites/default/files/styles/[^/]+/public/([^?]+)", url)
    if m:
        return f"https://slimweb.vn/sites/default/files/{m.group(1)}"
    return url.split("?")[0]


def looks_like_image(url: str) -> bool:
    path = urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True
    if "/images/" in path or "/sites/default/files/" in path or "/uploads/" in path:
        return True
    return False


def is_migratable_asset(url: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in SKIP_HOSTS:
        return False
    if host in MIGRATABLE_HOSTS or host.endswith(".slimcrm.vn") or host.endswith(".slim.vn"):
        return looks_like_image(url)
    return False


def extract_asset_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    base = page_base_url(base_url)
    found: set[str] = set()

    for tag in soup.find_all(["img", "source", "link", "meta"]):
        for attr in ("src", "data-src", "href", "content"):
            if not tag.has_attr(attr):
                continue
            val = tag.get(attr)
            if not isinstance(val, str):
                continue
            if tag.name == "link" and tag.get("rel") not in (["icon"], ["shortcut icon"], ["apple-touch-icon"]):
                if "icon" not in (tag.get("rel") or []):
                    continue
            url = normalize_url(val, base)
            if is_migratable_asset(url):
                found.add(url)

        if tag.has_attr("srcset"):
            srcset = tag["srcset"]
            if isinstance(srcset, str):
                for item in srcset.split(","):
                    part = item.strip().split()[0] if item.strip() else ""
                    url = normalize_url(part, base)
                    if is_migratable_asset(url):
                        found.add(url)

    for match in re.finditer(r"url\(([^)]+)\)", html):
        raw = match.group(1).strip("'\"")
        url = normalize_url(raw, base)
        if is_migratable_asset(url):
            found.add(url)

    return sorted(found)


def strip_legacy_blog_chrome(html: str) -> str:
    """Xóa khối chia sẻ / nút Top thừa từ web slimcrm cũ."""
    if not html or "btn-share" not in html and "cd-top" not in html:
        return html

    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one("#post_text") or soup.select_one(".post_text") or soup.body
    if not root:
        return html

    for el in root.select(".btn-share"):
        el.decompose()
    for el in root.select("a.cd-top"):
        el.decompose()
    for el in root.select("div.clearboth"):
        if not el.get_text(strip=True) and not el.find(True):
            el.decompose()

    if root.name in ("body", "html"):
        return "".join(str(child) for child in root.children).strip()
    return str(root)


def extract_meta(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    meta: dict[str, str] = {}

    title = soup.find("title")
    if title and title.string:
        meta["title"] = title.get_text(strip=True)

    for tag in soup.find_all("meta"):
        if tag.get("property") == "og:title" and tag.get("content"):
            meta["og_title"] = tag["content"].strip()
        if tag.get("property") == "og:description" and tag.get("content"):
            meta["og_description"] = tag["content"].strip()
        if tag.get("property") == "og:image" and tag.get("content"):
            meta["og_image"] = tag["content"].strip()
        if tag.get("name") == "description" and tag.get("content"):
            meta["description"] = tag["content"].strip()
        if tag.get("property") == "article:published_time" and tag.get("content"):
            meta["published_at"] = tag["content"].strip()

    link = soup.find("link", rel=lambda r: r and "canonical" in r)
    if link and link.get("href"):
        meta["canonical"] = link["href"].strip()

    return meta


def dedupe_assets(urls: Iterable[str]) -> list[dict[str, str]]:
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            items.append({"source_url": url})
    return items
