import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bs4 import BeautifulSoup
from lib.http_client import HttpClient

url = "https://slimcrm.vn/blog/bmc-hoa-binh-bit-lo-ro-hoa-don-bang-can-dien-tu-slimcrm-misa-amis-ke-toan-me-invoice-81880.html"
with HttpClient() as c:
    html = c.get_text(url)
soup = BeautifulSoup(html, "lxml")
for sel in [".blog-content", ".post-content", "article", ".content", "#content", "main", ".container .row"]:
    n = soup.select_one(sel)
    print(sel, len(n.get_text(strip=True)) if n else 0)
for m in soup.find_all("meta"):
    p = m.get("property") or m.get("name")
    if p in ("og:title", "og:image", "og:description", "description"):
        print(p, (m.get("content") or "")[:100])
