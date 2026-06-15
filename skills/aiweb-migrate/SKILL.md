---
name: aiweb-migrate
description: >-
  Migrate landing pages/blog từ web cũ sang AI Web qua Migration API, hoặc chế bài blog
  SlimAI từ video gốc/YouTube rồi đăng lên AIWeb. Dùng khi user muốn import/chuyển nội dung
  domain cũ (slimcrm.vn, v.v.) vào aiweb; hoặc muốn lấy transcript video, cắt ảnh minh họa
  từ video, đóng khung SlimAI, viết bài blog theo giọng SlimAI và đăng public lên AIWeb.
  Với migration web cũ: cào dữ liệu bằng script riêng, gọi API migration.php, map ảnh,
  upsert landing/blog. Không dùng Playwright để cào.
---

# AI Web — Migration Pipeline (Agent)

Migrate nội dung từ **web cũ** (landing + blog) vào **AI Web / AIPage** qua **Migration API**, hoặc tạo **blog SlimAI từ video gốc** rồi đăng lên AIWeb.
Agent **không cào web trực tiếp bằng Playwright** — user/agent viết **Python (hoặc tool khác) theo từng domain** để extract; agent điều phối pipeline và gọi API.

**Repo:** Skill + script nằm trong [aiweb_skill](https://github.com/slimsoftvietnam/aiweb_skill).  
Mã PHP AIPage: [aiweb](https://github.com/slimsoftvietnam/aiweb).

---

## A. Video gốc → Blog SlimAI → AIWeb

Dùng phần này khi user đưa URL video/YouTube và yêu cầu “xem video”, “bóc tách nội dung”, “chế bài blog”, “theo giọng SlimAI”, “ảnh cắt từ video”, “đăng lên AIWeb”.

### A.1. Tool chuẩn trong repo

Ưu tiên dùng tool trong repo AIWeb:

```bash
python tools/video_blog/video_to_aiweb_blog.py prepare --url "YOUTUBE_URL" --output-root output/video_blogs --frame-count 8
```

Sau khi review/chỉnh `article.html`, `article_meta.json`, `frame_plan.json`:

```bash
python tools/video_blog/video_to_aiweb_blog.py publish-draft --workdir output/video_blogs/VIDEO_ID --env D:/Xampp/htdocs/aiweb_skill/tools/migration/config.env
```

Tên lệnh `publish-draft` được giữ vì tương thích, nhưng flow hiện tại **đăng public luôn** (`status: published`). Không dùng config local `tools/migration/config.env` nếu mục tiêu là `https://ai.slim.vn`; dùng config của `aiweb_skill` hoặc env có `AIWEB_BASE=https://ai.slim.vn`.

### A.2. Chuẩn nội dung SlimAI

- Viết lại thành bài gốc, không chép transcript dài.
- Giọng văn: chuyên gia, dễ hiểu, thực dụng, ít hype nhưng có cảm hứng để user làm bước tiếp theo.
- Cấu trúc ưu tiên:
  1. Mở bài ngắn: công cụ/quy trình giúp gì, đọc xong làm được gì.
  2. Mục “X là gì?” hoặc “Tổng quan” trước khi vào setup.
  3. Các heading dạng `Bước 1`, `Bước 2` cho thao tác user làm theo.
  4. Ảnh minh họa ngay sau heading tương ứng.
  5. Blockquote cảnh báo thực tế khi có rủi ro về API key, chi phí, quyền truy cập.
  6. Checklist ngắn và kết luận khuyến khích bắt đầu từ một use case nhỏ.
- Không nhúng iframe YouTube trong bài. Chỉ ghi nguồn video/link video ở cuối.

### A.3. Chuẩn ảnh minh họa

- Ảnh phải cắt từ video gốc theo timestamp tương ứng với từng section chính.
- Mặc định dùng ảnh đã đóng khung SlimAI bằng tool:
  - nền cam nhạt,
  - logo SlimAI từ `https://ai.slim.vn/uploads/upload/mig_37637ef12e8e.png`,
  - thanh tiêu đề bước,
  - screenshot thực tế nằm giữa trong khung browser.
- Có thể crop, tăng nét/sáng, che email/API key/mật khẩu, xóa chi tiết thừa nhỏ; không được làm sai nội dung hướng dẫn gốc.
- Luôn dùng `src="/uploads/upload/..."` trong HTML, không dùng `src="uploads/..."` để tránh vỡ ảnh ở `/blog/{slug}`.
- Nếu user yêu cầu ảnh raw, chạy tool với `--no-brand-frame`.

### A.4. Quy trình bắt buộc

1. `prepare`: lấy metadata, transcript, tải video, cắt frame, tạo `frame_plan.json`, `article.template.html`, `article_meta.template.json`.
2. Đọc transcript và viết lại bài trong `article.html` theo giọng SlimAI.
3. Tạo/chỉnh `article_meta.json`: title SEO, slug, seo_description, category, source URL.
4. Chỉnh `frame_plan.json`: mỗi ảnh có `heading_contains`, caption, alt, timestamp; thêm `redactions` nếu có thông tin nhạy cảm.
5. `publish-draft` để upload ảnh, chèn figure, upsert category, upsert blog post với `status: published`.
6. Verify qua API và public URL:
   - bài `status=published`,
   - có 6–10 `<figure>` tùy độ dài bài,
   - không có `<iframe>`,
   - có nguồn video cuối bài,
   - không có `src="uploads/`,
   - ảnh public trả HTTP 200.

### A.5. Output local

Tool phải lưu artifact tại:

```text
output/video_blogs/{video_id}/
  metadata.json
  transcript.json
  transcript.txt
  video.mp4
  frame_plan.json
  frames/*.jpg
  edited/*.jpg
  article.html
  article_meta.json
  upload_manifest.json
```

Nếu cần báo kết quả, đưa link bài public, post ID, số ảnh, trạng thái verify, và đường dẫn artifact local.

---

## B. Migration web cũ → AIWeb

### B.0. Chuẩn bị một lần

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

### B.1. Pipeline tổng thể (bắt buộc theo thứ tự)

```
[Domain cũ]
    → (1) Khảo sát URL / phân loại
    → (2) Extract → manifest.json (script Python ngoài repo hoặc do agent viết)
    → (3) Trình bày migration plan: URL, loại trang, tiêu đề, target slug, URL bị skip
    → (4) Chờ user chọn/xác nhận trước khi import thật
    → (5) Import ảnh → Migration API (asset map)
    → (6) Rewrite link ảnh trong HTML (API hoặc trước khi gửi)
    → (7) Upsert categories → landing → blog posts
    → (8) dry_run=false → verify → publish (nếu user yêu cầu)
```

**Không** import HTML trước khi có asset map cho ảnh nội bộ domain cũ.
**Không** chạy import thật (`dry_run=false`, `--publish`, `publish_batch`, `import_manifest` thật) cho đến khi user đã chọn trang hoặc xác nhận `all`.

---

### B.2. Manifest (hợp đồng giữa scraper và API)

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

### B.3. Migration API — Actions

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

### B.4. Vai trò Agent (từng bước)

### Bước A — Khảo sát domain

- Liệt kê URL (sitemap, menu, hoặc list user cung cấp)
- Phân loại: `landing` | `blog_post` | `bỏ qua` (shop, login, admin…)
- Báo cáo ngắn cho user trước khi extract/import hàng loạt

### Bước B — Extract (KHÔNG Playwright trong agent)

- Viết hoặc cập nhật **script Python theo domain** (ngoài `aiweb_core`, ví dụ `tools/migration/scrapers/slimcrm_vn.py`)
- Output: `manifest.json` đúng schema §2
- User chạy script; agent review output

### Bước B.1 — User approval gate (bắt buộc)

Sau khi có `manifest.json` và trước mọi import thật:

1. Trình bày danh sách migrate theo số thứ tự: `#`, `type`, `source_url`, `title`, `target_slug`, `status`.
2. Trình bày danh sách bỏ qua riêng: URL + lý do (`401`, `403`, `404`, login/admin, không hỗ trợ).
3. Hỏi user chọn một trong các cách: `all`, danh sách số `1,3,5-8`, hoặc `cancel`.
4. Nếu user chọn một phần, tạo manifest filtered mới chỉ chứa các trang đã chọn; chỉ import asset liên quan nếu có thể xác định.
5. Dry-run có thể chạy sau khi user chọn; import thật chỉ chạy khi dry-run pass và user đã cho phép import/publish.

Ưu tiên in plan bằng helper:

```bash
python runners/review_manifest_plan.py --file output/manifest.json
```

Không suy đoán thay user. Nếu prompt ban đầu nói "migrate tất cả", vẫn phải hiển thị plan và chờ xác nhận trước import thật.

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

### B.5. Idempotent (chạy lại an toàn)

- Cùng `source_domain` + `source_key` → **update** entity đã map (`migration_entities`)
- Cùng `source_url` ảnh → **skip**, trả `local_path` cũ
- Slug trùng trên aiweb nhưng chưa map → **link** bản có sẵn

---

### B.6. Bảng DB migration (tự tạo khi gọi API)

| Bảng | Lưu gì |
|------|--------|
| `migration_assets` | `source_url` → `local_path` |
| `migration_entities` | `source_key` → `local_id` (landing/blog/category) |

Không lưu file ảnh trong DB — chỉ đường dẫn.

---

### B.7. Lỗi thường gặp

| Lỗi | Xử lý |
|-----|--------|
| `401 Unauthorized` | Sai API key hoặc thiếu header |
| `503` chưa cấu hình key | Chạy SQL §0 |
| Ảnh vỡ sau import | Chưa `import_asset` hoặc chưa `rewrite_assets` |
| Landing trống | Thiếu `html_content` / `sections` |
| Slug `*-import-1` | Slug đã tồn tại trên aiweb |

---

### B.8. Phạm vi KHÔNG migrate qua API này

- Shop / sản phẩm / đơn hàng
- Cài đặt hệ thống (SEO global, GA, theme)
- User/account web cũ

Landing đã có sẵn **import JSON** (`import_pages.php`) — Migration API bổ sung **upsert theo source_key**, **ảnh**, **blog**.

---

### B.9. Checklist agent trước khi báo xong

- [ ] `ping` OK
- [ ] Manifest validate đủ field
- [ ] Đã trình bày migration plan và user đã chọn/xác nhận
- [ ] Ảnh domain cũ đã trong `migration_assets`
- [ ] `dry_run` pass cho mẫu 1 landing + 1 blog
- [ ] Import thật + `list_entities` khớp số lượng
- [ ] User xác nhận publish (nếu cần)
