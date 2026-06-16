# Migration Tools — domain bất kỳ → AI Web

Pipeline migrate **landing + blog** từ **bất kỳ domain** sang AI Web qua Migration API.

## Input

| Tham số | Ví dụ |
|---------|-------|
| `--domain` | `example.com` |
| `--url` | `https://example.com/` (có thể lặp) |

## Asset migrate

Import từ domain cũ: **ảnh, CSS, JS, font** → `uploads/migrate/{domain}/`.

**Giữ nguyên CDN (không import):** Google Fonts, GA, GTM, jsdelivr, cdnjs.

Catalog read-only: `aiweb_core/data/migration/{domain}.json` + tab **Tài nguyên migrate** (Quản lý ảnh).

## Cài đặt

```bash
pip install -r tools/migration/requirements.txt
cp tools/migration/config.example.env tools/migration/config.env
```

```env
AIWEB_BASE=http://localhost/aiweb
AIWEB_ROOT=D:/Xampp/htdocs/aiweb
MIGRATION_API_KEY=aiw_...
```

## Quy trình (mọi domain)

```bash
cd tools/migration

# 1. Khảo sát
python scrapers/site_recon.py --domain example.com --url https://example.com/ --sitemap

# 2. Xem kế hoạch — chờ user chọn trang
python runners/review_inventory_plan.py --file output/example_com_inventory.json

# 3. Extract manifest
python scrapers/site_extract.py --domain example.com --pilot 5
python scrapers/site_extract.py --domain example.com   # full sau khi user chọn all

# 4. Import
python runners/review_manifest_plan.py --file output/example_com_manifest.json
python runners/import_manifest.py --env config.env \
  --file output/example_com_manifest.json --force --publish
```

## URL công khai sau migrate

`https://your-domain/{slug}` — ví dụ `/home`, `/tinhnang` (tùy cấu hình site).

### Nginx root (không có rewrite `/uploads/`)

Trong `config.env`:

```env
MIGRATION_USE_NGINX_ROOT_PATH=1
# hoặc MIGRATION_UPLOAD_PREFIX=aiweb_core/uploads
```

Import sẽ ghi HTML với `/aiweb_core/uploads/migrate/...` và tắt `rewrite_assets` phía server.

**Site đã import trước đó** — chạy một lần:

```bash
python runners/reprocess_upload_urls.py --env config.env --dry-run
python runners/reprocess_upload_urls.py --env config.env
```

Local Apache/XAMPP: **không** bật flag trên (giữ mặc định `uploads/`).

## Scraper theo domain (tuỳ chọn)

Nếu site phức tạp, dùng scraper riêng trong `scrapers/` — vẫn xuất cùng schema manifest.

| Domain | Script |
|--------|--------|
| slimcrm.vn | `slimcrm_recon.py` + `slimcrm_extract.py` |
| ai.slim.vn | `ai_slim_extract.py` |
| *generic* | `site_recon.py` + `site_extract.py` |
