---
name: aiweb-migrate
description: >-
  Migrate landing pages và blog từ web cũ sang AI Web qua Migration API.
  Dùng khi user muốn import/chuyển nội dung domain cũ (slimcrm.vn, v.v.)
  vào aiweb: cào dữ liệu bằng script riêng (Python hoặc công cụ khác do user/agent viết),
  gọi API migration.php, map ảnh, upsert landing/blog. Không dùng Playwright để cào.
---

# AI Web — Migration Pipeline (Agent)

Migrate nội dung từ **web cũ** (landing + blog) vào **AI Web / AIPage** qua **Migration API**.  
Agent **không cào web trực tiếp bằng Playwright** — user/agent viết **Python (hoặc tool khác) theo từng domain** để extract; agent điều phối pipeline và gọi API.

**Repo:** Skill + script nằm trong [aiweb_skill](https://github.com/slimsoftvietnam/aiweb_skill).  
Mã PHP AIPage: [aiweb](https://github.com/slimsoftvietnam/aiweb).

---

## 0. Chuẩn bị một lần

### Clone & cấu hình

```bash
git clone https://github.com/slimsoftvietnam/aiweb.git
git clone https://github.com/slimsoftvietnam/aiweb_skill.git
cd aiweb_skill/tools/migration
cp config.example.env config.env
```

`config.env`:

```env
AIWEB_BASE=http://localhost/aiweb/aiweb_core
AIWEB_ROOT=/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

### Cấu hình API key

**Khuyến nghị:** AIPage → **Cài đặt → API Agent** → Tạo API key → copy vào `MIGRATION_API_KEY`.

Vẫn hỗ trợ key cũ: `migration_api_key` trong SQLite hoặc `MIGRATION_API_KEY` trong `aiweb_core/config/config.php`.

### Base URL & Auth

- **Endpoint:** `{AIWEB_BASE}/api/migration.php`
- **Header:** `Authorization: Bearer {api_key}` hoặc `X-Api-Key: {api_key}`
- **Body:** JSON `Content-Type: application/json`

### Kiểm tra kết nối

```bash
python runners/import_manifest.py --ping-only --env config.env
```

Kỳ vọng: `Migration API OK` và `{"success":true,"service":"aiweb-migration",...}`

---

## 1. Pipeline tổng thể (bắt buộc theo thứ tự)

```
[Domain cũ]
    → (1) Khảo sát URL / phân loại
    → (2) Extract → manifest.json (script Python ngoài repo hoặc do agent viết)
    → (3) Import ảnh → Migration API (asset map)
    → (4) Rewrite link ảnh trong HTML (API hoặc trước khi gửi)
    → (5) Upsert categories → landing → blog posts
    → (6) dry_run=false → verify → publish (nếu user yêu cầu)
```

**Không** import HTML trước khi có asset map cho ảnh nội bộ domain cũ.

---

## 2. Manifest (hợp đồng giữa scraper và API)

Scraper (Python theo domain) xuất JSON. Agent validate trước khi gọi API.

```json
{
  "source_domain": "slimcrm.vn",
  "categories": [
    { "source_key": "tin-tuc", "name": "Tin tức", "slug": "tin-tuc", "description": "" }
  ],
  "assets": [
    { "source_url": "https://slimcrm.vn/wp-content/uploads/2024/a.jpg" }
  ],
  "landing_pages": [
    {
      "source_key": "home",
      "slug": "home",
      "title": "Trang chủ",
      "html_content": "<!DOCTYPE html>...",
      "seo_description": "",
      "language": "vi",
      "is_published": false
    }
  ],
  "blog_posts": [
    {
      "source_key": "bai-gioi-thieu",
      "slug": "bai-gioi-thieu",
      "title": "Giới thiệu",
      "content": "<p>...</p>",
      "category_slug": "tin-tuc",
      "featured_image": "https://slimcrm.vn/.../cover.jpg",
      "status": "draft",
      "published_at": "2024-01-15 10:00:00"
    }
  ]
}
```

**Quy ước:**

| Field | Ý nghĩa |
|-------|---------|
| `source_domain` | Domain gốc, dùng cho map ảnh & idempotent |
| `source_key` | ID ổn định từ web cũ (slug hoặc ID) — upsert lần sau không duplicate |
| `slug` | Slug trên aiweb (giữ nếu có thể) |

---

## 3. Migration API — Actions

Tất cả POST JSON với field `"action"`.

| action | Mục đích |
|--------|----------|
| `ping` / `status` | Health check |
| `import_asset` | Tải 1 ảnh từ URL → `uploads/upload/` + lưu `migration_assets` |
| `import_assets` | Batch `{ "items": [{ "source_url": "..." }, ...] }` |
| `get_asset_map` | Lấy map `source_url → local_path` theo `source_domain` |
| `rewrite_html` | Thay URL ảnh trong HTML theo map đã import |
| `upsert_category` | Tạo/cập nhật danh mục blog |
| `upsert_landing` | Tạo/cập nhật landing (+ sections) |
| `upsert_blog_post` | Tạo/cập nhật bài viết |
| `list_entities` | Xem đã migrate entity nào (`source_domain`, optional `entity_type`) |

**Dry-run:** thêm `"dry_run": true` vào payload — validate, không ghi DB/file (trừ đọc map có sẵn).

### Ví dụ: import ảnh

```bash
curl -s -X POST "http://localhost/aiweb/api/migration.php" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "import_asset",
    "source_domain": "slimcrm.vn",
    "source_url": "https://slimcrm.vn/path/to/image.jpg"
  }'
```

Response: `local_path` (vd. `upload/mig_abc123.jpg`), `public_url`.

### Ví dụ: rewrite HTML

```bash
curl -s -X POST "http://localhost/aiweb/api/migration.php" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "rewrite_html",
    "source_domain": "slimcrm.vn",
    "html": "<img src=\"https://slimcrm.vn/old.jpg\">"
  }'
```

### Ví dụ: upsert landing

```bash
curl -s -X POST "http://localhost/aiweb/api/migration.php" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "upsert_landing",
    "source_domain": "slimcrm.vn",
    "source_key": "home",
    "slug": "home",
    "title": "Trang chủ",
    "html_content": "<!DOCTYPE html>...",
    "rewrite_assets": true,
    "is_published": false,
    "dry_run": true
  }'
```

- `html_content`: full HTML 1 section (giống export landing kiểu `lab.json`)
- Hoặc `sections`: `[{ "html_content": "...", "section_order": 0 }]`
- `rewrite_assets: true` (mặc định): tự thay ảnh theo `migration_assets`

### Ví dụ: upsert blog

```bash
curl -s -X POST "http://localhost/aiweb/api/migration.php" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "upsert_blog_post",
    "source_domain": "slimcrm.vn",
    "source_key": "bai-1",
    "slug": "bai-1",
    "title": "Tiêu đề",
    "content": "<p>Nội dung</p>",
    "category_slug": "tin-tuc",
    "featured_image": "https://slimcrm.vn/.../cover.jpg",
    "status": "draft",
    "rewrite_assets": true
  }'
```

---

## 4. Vai trò Agent (từng bước)

### Bước A — Khảo sát domain

- Liệt kê URL (sitemap, menu, hoặc list user cung cấp)
- Phân loại: `landing` | `blog_post` | `bỏ qua` (shop, login, admin…)
- Báo cáo ngắn cho user trước khi import hàng loạt

### Bước B — Extract (KHÔNG Playwright trong agent)

- Viết hoặc cập nhật **script Python theo domain** (ngoài `aiweb_core`, ví dụ `tools/migration/scrapers/slimcrm_vn.py`)
- Output: `manifest.json` đúng schema §2
- User chạy script; agent review output

### Bước C — Import ảnh

1. Gọi `import_assets` (batch 20–50 URL/lần) hoặc từng `import_asset`
2. `get_asset_map` để kiểm tra
3. Lỗi URL → ghi log, tiếp tục (không dừng cả job)

### Bước D — Import nội dung (dry-run trước)

1. `upsert_category` cho từng category (`dry_run: true` rồi `false`)
2. `upsert_landing` từng trang (`dry_run` → thật)
3. `upsert_blog_post` từng bài (`dry_run` → thật)
4. Mặc định `status: draft`, `is_published: false` — user duyệt rồi publish

### Bước E — Verify

- `list_entities` với `source_domain`
- Mở admin aiweb: Trang web, Bài viết
- Mở URL công khai: `/p/{slug}`, `/blog/{slug}`
- Kiểm tra ảnh không còn trỏ domain cũ

---

## 5. Idempotent (chạy lại an toàn)

- Cùng `source_domain` + `source_key` → **update** entity đã map (`migration_entities`)
- Cùng `source_url` ảnh → **skip**, trả `local_path` cũ
- Slug trùng trên aiweb nhưng chưa map → **link** bản có sẵn

---

## 6. Bảng DB migration (tự tạo khi gọi API)

| Bảng | Lưu gì |
|------|--------|
| `migration_assets` | `source_url` → `local_path` |
| `migration_entities` | `source_key` → `local_id` (landing/blog/category) |

Không lưu file ảnh trong DB — chỉ đường dẫn.

---

## 7. Lỗi thường gặp

| Lỗi | Xử lý |
|-----|--------|
| `401 Unauthorized` | Sai API key hoặc thiếu header |
| `503` chưa cấu hình key | Chạy SQL §0 |
| Ảnh vỡ sau import | Chưa `import_asset` hoặc chưa `rewrite_assets` |
| Landing trống | Thiếu `html_content` / `sections` |
| Slug `*-import-1` | Slug đã tồn tại trên aiweb |

---

## 8. Phạm vi KHÔNG migrate qua API này

- Shop / sản phẩm / đơn hàng
- Cài đặt hệ thống (SEO global, GA, theme)
- User/account web cũ

Landing đã có sẵn **import JSON** (`import_pages.php`) — Migration API bổ sung **upsert theo source_key**, **ảnh**, **blog**.

---

## 9. Checklist agent trước khi báo xong

- [ ] `ping` OK
- [ ] Manifest validate đủ field
- [ ] Ảnh domain cũ đã trong `migration_assets`
- [ ] `dry_run` pass cho mẫu 1 landing + 1 blog
- [ ] Import thật + `list_entities` khớp số lượng
- [ ] User xác nhận publish (nếu cần)
