---
name: aiweb-migrate
description: >-
  Migrate landing/blog từ bất kỳ domain web cũ sang AI Web qua Migration API, hoặc chế bài blog
  SlimAI từ video gốc/YouTube rồi đăng lên AIWeb. Dùng khi user đưa domain + URL web cần migrate
  (vd. example.com, https://example.com/) — agent khảo sát, lập kế hoạch migrate, chờ user xác nhận,
  rồi extract/import qua API. Hoặc khi user muốn lấy transcript video, cắt ảnh, viết blog SlimAI.
  Không dùng Playwright để cào; dùng script Python trong aiweb_skill hoặc scraper theo domain.
---

# AI Web — Migration Pipeline (Agent)

Migrate nội dung từ **bất kỳ web cũ** (landing + blog) vào **AI Web / AIPage** qua **Migration API**, hoặc tạo **blog SlimAI từ video gốc** rồi đăng lên AIWeb.

Agent **không cào web trực tiếp bằng Playwright** — dùng **script Python** trong repo (generic hoặc theo domain) để extract; agent điều phối **input → kế hoạch → xác nhận → thực thi**.

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

## B. Migration web cũ → AIWeb (mọi domain)

### B.0. Input bắt buộc từ user

Trước khi chạy bất kỳ bước nào, agent **phải có**:

| Input | Ví dụ | Ghi chú |
|-------|-------|---------|
| `source_domain` | `example.com` | Domain gốc, không `www`, không path |
| `start_url` | `https://example.com/` | URL bắt đầu khảo sát — có thể nhiều URL |
| Phạm vi (tuỳ chọn) | landing only / gồm blog | Mặc định: cả landing + blog nếu phát hiện được |
| Đích AI Web | `AIWEB_BASE` trong `config.env` | Site đích phải có license + API key |

**Không** tự giả định domain (vd. slimcrm.vn) nếu user chưa cung cấp. Nếu thiếu input → hỏi user trước.

---

### B.0.1. Quy trình agent (input → plan → thực thi)

```
User: domain + start_url(s)
    → (1) Khảo sát (recon) → inventory JSON
    → (2) Trình migration plan (số thứ tự, URL, loại, target slug)
    → (3) Chờ user chọn: all | 1,3,5-8 | cancel
    → (4) Extract manifest (chỉ trang đã chọn)
    → (5) Trình lại plan từ manifest + dry-run
    → (6) Import asset (ảnh/css/js/font) → rewrite HTML → upsert
    → (7) Verify → publish (nếu user yêu cầu)
```

**Không** import thật (`dry_run=false`, `--publish`) cho đến khi user xác nhận plan.

---

### B.0.2. Lệnh chuẩn (domain bất kỳ)

Thay `{domain}` và `{url}` theo input user:

```bash
cd tools/migration

# 1. Khảo sát
python scrapers/site_recon.py \
  --domain {domain} \
  --url {url} \
  --sitemap

# 2. Xem kế hoạch (trước extract)
python runners/review_inventory_plan.py \
  --file output/{domain_underscore}_inventory.json

# 3. Extract manifest (pilot hoặc theo lựa chọn user)
python scrapers/site_extract.py --domain {domain} --pilot 5
python scrapers/site_extract.py --domain {domain} --only home,tinhnang
python scrapers/site_extract.py --domain {domain}          # full sau khi user chọn all

# 4. Xem plan manifest + import
python runners/review_manifest_plan.py \
  --file output/{domain_underscore}_manifest.json

python runners/import_manifest.py --env config.env \
  --file output/{domain_underscore}_manifest.json --force --publish
```

`{domain_underscore}` = domain thay `.` bằng `_` (vd. `example.com` → `example_com`).

---

### B.0.3. Chuẩn bị một lần

### Clone & cấu hình

```bash
git clone https://github.com/slimsoftvietnam/aiweb.git
git clone https://github.com/slimsoftvietnam/aiweb_skill.git
cd aiweb_skill/tools/migration
cp config.example.env config.env
```

`config.env`:

```env
AIWEB_BASE=http://localhost/aiweb
AIWEB_ROOT=/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

### Nginx document root (slimcrm.vn, ai.slim.vn, …)

Nginx **không đọc** `.htaccess`. URL `/uploads/...` sẽ 404 dù file nằm trong `aiweb_core/uploads/`.

**Local Apache / XAMPP:** không thêm gì (mặc định `uploads/` + `.htaccess` rewrite).

**Production Nginx root:** thêm vào `config.env`:

```env
MIGRATION_USE_NGINX_ROOT_PATH=1
# hoặc: MIGRATION_UPLOAD_PREFIX=aiweb_core/uploads
```

`import_manifest.py` sẽ:
- rewrite HTML phía client → `/aiweb_core/uploads/migrate/...`
- gửi `rewrite_assets: false` để API không ghi đè lại `uploads/`

**Site đã import trước khi bật flag:**

```bash
python runners/reprocess_upload_urls.py --env config.env --dry-run
python runners/reprocess_upload_urls.py --env config.env
```

File vật lý vẫn ở `aiweb_core/uploads/migrate/` — chỉ đổi URL trong HTML/DB.

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
[{source_domain} + start_url]
    → (1) Khảo sát URL / phân loại (site_recon.py hoặc scraper domain-specific)
    → (2) Trình migration plan từ inventory — chờ user chọn
    → (3) Extract → manifest.json
    → (4) Trình lại plan từ manifest; dry-run
    → (5) Import tài nguyên (ảnh, CSS, JS, font) → Migration API + JSON catalog
    → (6) Rewrite link trong HTML (Apache: `rewrite_assets: true` trên API; Nginx root: rewrite client + `rewrite_assets: false`)
    → (7) Upsert categories → landing → blog posts
    → (8) verify → publish (nếu user yêu cầu)
```

**Không** import HTML trước khi có asset map cho tài nguyên nội bộ domain cũ (ảnh, css, js, font).

**Giữ nguyên URL ngoài (không import):** Google Fonts, GA, GTM, cdn.jsdelivr.net, cdnjs.cloudflare.com.

**Lưu trữ file:** `uploads/migrate/{domain}/{css|js|fonts|img}/mig_{hash}.ext`  
**Catalog UI (read-only):** `aiweb_core/data/migration/{domain}.json` — tab **Tài nguyên migrate** tại Quản lý ảnh.

**Reuse:** Cùng `source_url` giữa nhiều landing → import một lần; `rewrite_assets` dùng chung map.

**Scraper theo domain:** Nếu site có cấu trúc đặc thù (Drupal, WordPress tùy biến, blog subdomain riêng), viết hoặc dùng scraper riêng trong `tools/migration/scrapers/` — vẫn xuất cùng schema manifest. `site_recon.py` / `site_extract.py` là điểm bắt đầu generic; slimcrm.vn là ví dụ đã tối ưu (§B.10).

---

### B.1.1. Trình migration plan (bắt buộc)

Sau recon, in plan cho user **trước extract/import**:

```bash
python runners/review_inventory_plan.py --file output/{domain}_inventory.json
```

Format trình bày:

```
Source domain: example.com
Landing pages: 12
Blog posts: 45

Migration plan (recon):
1. [landing] Trang chủ
   source: https://example.com/
   target: /home
2. [blog_post] Bài viết mẫu
   source: https://example.com/blog/bai-mau
   target: /bai-mau

Skipped URLs:
- https://example.com/admin (path_skip_rule)

Ask the user to choose: all, numbers like 1,3,5-8, or cancel.
```

Sau extract, lặp lại với `review_manifest_plan.py` trước import thật.

---

### B.2. Manifest (hợp đồng giữa scraper và API)

Scraper (Python theo domain) xuất JSON. Agent validate trước khi gọi API.

```json
{
  "source_domain": "example.com",
  "categories": [
    { "source_key": "tin-tuc", "name": "Tin tức", "slug": "tin-tuc", "description": "" }
  ],
  "assets": [
    { "source_url": "https://example.com/assets/logo.png" }
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
      "featured_image": "https://example.com/.../cover.jpg",
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
| `import_asset` | Tải 1 tài nguyên (ảnh/css/js/font) → `uploads/migrate/{domain}/` + DB + JSON catalog |
| `import_assets` | Batch `{ "items": [{ "source_url": "..." }, ...] }` — URL trùng **reuse** (`skipped: true`) |
| `get_asset_map` | Lấy map `source_url → local_path` theo `source_domain` |
| `rewrite_html` | Thay URL tài nguyên trong HTML theo map đã import |
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

Response: `local_path` (vd. `migrate/slimcrm.vn/img/mig_abc123.jpg`), `public_url`, `kind` (`css`|`js`|`font`|`image`).

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

### Bước A — Khảo sát domain (từ input user)

- Lấy `source_domain` + `start_url` từ user
- Chạy `site_recon.py` (generic) hoặc scraper domain-specific nếu có
- Phân loại: `landing` | `blog_post` | `bỏ qua` (shop, login, admin…)
- Báo cáo inventory + plan trước khi extract/import hàng loạt

### Bước B — Extract (KHÔNG Playwright trong agent)

- Generic: `site_extract.py --domain {domain}`
- Site đặc thù: scraper riêng (vd. `slimcrm_extract.py`) — output cùng schema manifest
- User/agent chạy script; agent review output

### Bước B.1 — User approval gate (bắt buộc, 2 lần)

**Lần 1 — sau recon (trước extract):**

```bash
python runners/review_inventory_plan.py --file output/{domain}_inventory.json
```

User chọn trang → extract với `--only` hoặc `--pilot`.

**Lần 2 — sau manifest (trước import thật):**

1. Trình bày danh sách migrate theo số thứ tự: `#`, `type`, `source_url`, `title`, `target_slug`, `status`.
2. Trình bày danh sách bỏ qua riêng: URL + lý do (`401`, `403`, `404`, login/admin, không hỗ trợ).
3. Hỏi user chọn: `all`, danh sách số `1,3,5-8`, hoặc `cancel`.
4. Dry-run trước import thật; import/publish chỉ khi user cho phép.

```bash
python runners/review_manifest_plan.py --file output/{domain}_manifest.json
```

Không suy đoán thay user. Nếu prompt ban đầu nói "migrate tất cả", vẫn phải hiển thị plan và chờ xác nhận trước import thật.

### Bước C — Import tài nguyên (ảnh, CSS, JS, font)

1. Gọi `import_assets` (batch 20–50 URL/lần) hoặc từng `import_asset`
2. `get_asset_map` hoặc đọc `data/migration/{domain}.json` để kiểm tra
3. Lỗi URL (404…) → ghi log, tiếp tục (không dừng cả job)

### Bước D — Import nội dung (dry-run trước)

1. `upsert_category` cho từng category (`dry_run: true` rồi `false`)
2. `upsert_landing` từng trang (`dry_run` → thật)
3. `upsert_blog_post` từng bài (`dry_run` → thật)
4. Mặc định `status: draft`, `is_published: false` — user duyệt rồi publish

### Bước E — Verify

- `list_entities` với `source_domain`
- Mở admin aiweb: Trang web, Bài viết
- Mở URL công khai landing: `/{slug}` hoặc `/p/{slug}` tùy cấu hình site
- Mở `/blog/{slug}` cho blog
- Tab **Quản lý ảnh → Tài nguyên migrate**: stats css/js/font/image khớp import
- DevTools Network: không còn request domain cũ cho asset đã migrate (GA/GTM/Fonts CDN OK)

---

### B.5. Idempotent (chạy lại an toàn)

- Cùng `source_domain` + `source_key` → **update** entity đã map (`migration_entities`)
- Cùng `source_url` tài nguyên → **skip**, trả `local_path` cũ (reuse giữa nhiều trang)
- Slug trùng trên aiweb nhưng chưa map → **link** bản có sẵn

---

### B.6. Lưu trữ migration (DB + JSON, không ALTER schema)

| Bảng / file | Lưu gì |
|------|--------|
| `migration_assets` | `source_url` → `local_path` (rewrite, idempotent) |
| `data/migration/{domain}.json` | Catalog UI: `kind`, stats, metadata — **chỉ API ghi** |
| `migration_entities` | `source_key` → `local_id` (landing/blog/category) |

File vật lý: `uploads/migrate/` — **không** sửa/xóa qua admin UI.

---

### B.7. Lỗi thường gặp

| Lỗi | Xử lý |
|-----|--------|
| `401 Unauthorized` | Sai API key hoặc thiếu header |
| `503` chưa cấu hình key | Chạy SQL §0 |
| Asset vỡ sau import | Chưa `import_asset` hoặc chưa `rewrite_assets`; URL 404 trên site cũ |
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

- [ ] Đã có `source_domain` + `start_url` từ user
- [ ] `ping` OK
- [ ] Đã recon + trình inventory plan; user đã chọn trang
- [ ] Manifest validate đủ field
- [ ] Đã trình bày manifest plan và user đã xác nhận import
- [ ] Ảnh/css/js/font domain cũ đã trong `migration_assets` + JSON catalog
- [ ] Tab **Tài nguyên migrate** hiển thị đúng số lượng
- [ ] `dry_run` pass cho mẫu 1 landing + 1 blog
- [ ] Import thật + `list_entities` khớp số lượng
- [ ] User xác nhận publish (nếu cần)

---

### B.10. Tham chiếu: slimcrm.vn (scraper tối ưu)

Khi user input `domain=slimcrm.vn`, dùng scraper chuyên biệt thay vì generic:

```bash
cd tools/migration
python scrapers/slimcrm_recon.py
python scrapers/slimcrm_extract.py          # hoặc --pilot trước
python runners/import_manifest.py --env config.env \
  --file output/slimcrm_manifest_landing.json --force --publish
```

Kỳ vọng: ~37 landing, hàng trăm asset. Blog: thêm `--include-blog` cho recon/extract.
