# SlimCRM → AI Web Migration Tools

Pipeline migrate **landing slimcrm.vn** (không gồm blog.slimcrm.vn mặc định).

## Asset migrate

Import từ domain cũ: **ảnh, CSS, JS, font** → `uploads/migrate/{domain}/`.

**Giữ nguyên CDN (không import):** Google Fonts, GA, GTM, jsdelivr, cdnjs.

Catalog read-only: `aiweb_core/data/migration/{domain}.json` + tab **Tài nguyên migrate** (Quản lý ảnh).

URL trùng giữa nhiều trang → import **một lần**, các trang sau **reuse** qua `migration_assets`.

## Cài đặt

```bash
pip install -r tools/migration/requirements.txt
cp tools/migration/config.example.env tools/migration/config.env
```

Tạo API key: AIPage → **Cài đặt → API Agent** (scope migration) → copy vào `MIGRATION_API_KEY`.

```env
AIWEB_BASE=http://localhost/aiweb
AIWEB_ROOT=D:/Xampp/htdocs/aiweb
MIGRATION_API_KEY=aiw_...
```

## Chạy slimcrm.vn (full landing)

```bash
cd tools/migration

# 1. Inventory
python scrapers/slimcrm_recon.py

# 2. Extract manifest (pilot trước nếu cần)
python scrapers/slimcrm_extract.py --pilot
python scrapers/slimcrm_extract.py

# 3. Import + publish
python runners/import_manifest.py --env config.env \
  --file output/slimcrm_manifest_landing.json --force --publish
```

## URL công khai sau migrate

`https://your-domain/{slug}` — ví dụ `/home`, `/tinhnang` (không phải `/p/{slug}`).

## Blog

Thêm `--include-blog` cho `slimcrm_recon.py` / `slimcrm_extract.py` nếu cần blog.slimcrm.vn.
