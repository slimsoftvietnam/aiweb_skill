---
name: aiweb
description: >-
  Hướng dẫn chủ site AI Web (AIPage) vận hành landing, blog, shop, sản phẩm số,
  biểu mẫu, helpdesk, affiliate qua giao diện admin và Agent API. Dùng khi user
  là khách hàng AI Web cần cấu hình site, tạo nội dung, hoặc tự động hóa qua API key
  của họ — không dùng cho sửa mã nguồn PHP.
---

# AI Web (AIPage) — Skill cho chủ site

**Phiên bản app:** 2.3.11 · **Tài liệu trong admin:** menu **Hướng dẫn** (`guide_public.php`)  
**Migrate / video→blog:** skill `aiweb-migrate` trong repo [aiweb_skill](https://github.com/slimsoftvietnam/aiweb_skill)

Skill này dành cho **người vận hành site** (đã mua license), không phải developer
sửa core PHP. Luôn ưu tiên **menu Cài đặt và trang admin** trước khi đụng API.

---

## 1. Bạn cần chuẩn bị

| Cần có | Ghi chú |
|--------|---------|
| URL site | Ví dụ `https://myshop.com` |
| Đăng nhập admin | `/login` — mật khẩu do chủ site tạo khi cài |
| API key (tùy chọn) | **Cài đặt → API Agent** — key `aiw_…` để agent tự động hóa |

**Bảo mật — không làm:**

- Không gửi **full API key**, mật khẩu admin, token Telegram, OAuth secret vào chat công cộng.
- Không yêu cầu agent **in lại** key/mật khẩu; chỉ dùng trong header API hoặc file cấu hình local của bạn.
- Chỉ kết nối Agent API tới **site của bạn** (domain đã kích hoạt license).

---

## 2. Địa chỉ thường dùng (khách & admin)

| URL | Ai dùng |
|-----|---------|
| `/`, `/{slug}` | Trang landing đã publish |
| `/blog`, `/blog/{slug}` | Blog công khai |
| `/shop`, `/shop/{slug}` | Shop |
| `/digital`, `/digital/{slug}` | Sản phẩm số |
| `/form/embed/{slug}` | Biểu mẫu nhúng (module bật) |
| `/api/submit_form.php` | Gửi biểu mẫu công khai (POST, có captcha + rate limit) |
| `/support` | Helpdesk khách |
| `/aff/login`, `/aff` | Cổng affiliate |
| `/login` | Admin |
| `/manage` | Quản lý landing |
| `/create`, `/create_secion` | Tạo/sửa landing |
| `/blog`, `/products`, `/orders` | Blog, sản phẩm, đơn hàng |
| `/digital_products`, `/digital_orders` | Sản phẩm số & đơn |
| `/forms`, `?action=form_submissions` | Biểu mẫu & phản hồi |
| `/settings` | Toàn bộ cấu hình |
| `/sitemap.xml`, `/robots.txt` | SEO |

**Đa ngôn ngữ:** **Cài đặt → Cài đặt chung → Ngôn ngữ UI** (`vi` / `en`) — đổi nhãn admin và trang blog/shop/helpdesk.

---

## 3. Use cases — làm trong admin

### UC-01 · Site mới (landing + blog + shop)

1. Cài site (wizard `/install` lần đầu) → kích hoạt license
2. **Cài đặt → Cài đặt chung:** trang chủ, ngôn ngữ
3. **Thương hiệu + SEO**
4. **Trang web → Tạo trang** → sửa trong editor → publish
5. Thêm bài blog, sản phẩm; **Thanh toán** (VietQR) nếu bán hàng

### UC-02 · Landing từ HTML (ChatGPT / Cursor)

1. **Tạo trang** → slug mới
2. Editor → tab **HTML** hoặc **Sửa** → dán HTML
3. Chèn widget **Blog / Sản phẩm / SP số / Biểu mẫu** nếu cần
4. ⚙ SEO trang → **Lưu** → publish từ **Quản lý trang**

### UC-03 · Migrate web cũ

→ Skill **`aiweb-migrate`** + API key trong **Cài đặt → API Agent**.

### UC-04 · Video YouTube → blog

→ Skill **`aiweb-migrate`** (công cụ `video_to_aiweb_blog.py`).

### UC-05 · Sản phẩm số

**Cài đặt → Sản phẩm số** → thêm SP → khách mua tại `/digital` → duyệt đơn trong admin.

### UC-06 · Shop + VietQR + Telegram

**Thiết lập Shop + Thanh toán + Thông báo đơn hàng** → khách đặt `/shop` → quản lý `/orders`.

### UC-07 · Helpdesk

**Cài đặt → Helpdesk** → khách `/support`, admin xử lý ticket trong menu Helpdesk.

### UC-08 · Affiliate

**Cài đặt → Affiliate** → đối tác `/aff/login`.

### UC-09 · SlimEmail

**Cài đặt → SlimEmail** — đồng bộ list khi đơn hàng thay đổi.

### UC-10 · Đổi ngôn ngữ VI ↔ EN

**Cài đặt → Cài đặt chung → Ngôn ngữ UI → Lưu.**

### UC-11 · Tự động hóa (Agent API)

1. **Cài đặt → API Agent** → tạo key (scope mặc định `agent` = full quyền)
2. Gọi `https://your-site.com/api/agent.php?action=ping` với header `Authorization: Bearer …`
3. Việc thường gặp: liệt kê landing/blog, **`upsert_landing_page`** (tạo/sửa trang), `upsert_product`, upload ảnh, `patch_settings` — migrate web cũ dùng skill `aiweb-migrate` + `upsert_landing`
4. Xóa dữ liệu qua API: **chỉ khi bạn chủ động yêu cầu** và gửi `"confirm": "DELETE"` trong JSON body

Kiểm tra kết nối trong **Cài đặt → API Agent** (nút kiểm tra) hoặc nhờ agent gọi `action=status`.

### UC-12 · SEO

**Cài đặt → SEO** + SEO riêng từng landing/bài/SP. Audit sâu: skill `seo`.

### UC-13 · Backup & cập nhật

**Cài đặt → Cơ sở dữ liệu** (backup) và **Cài đặt → Cập nhật** (upload patch ZIP từ SlimSoft).

### UC-14 · Biểu mẫu (admin)

1. **Cài đặt → Biểu mẫu** → bật module; cấu hình captcha nếu cần
2. Menu **Biểu mẫu** → tạo form và field
3. Chèn vào landing: toolbar **Biểu mẫu** trong editor, hoặc link `/form/embed/{slug}`
4. Xem phản hồi: **Biểu mẫu → Phản hồi** (export CSV)

### UC-15 · Biểu mẫu (Agent API — 2.3.11+)

Dùng khi cần agent/script tự động tạo form, đồng bộ lead, xuất đăng ký — **không thay** luồng khách gửi form công khai.

1. Bật module **Cài đặt → Biểu mẫu**
2. Key API có scope `forms.read` / `forms.write` / `forms.delete` (hoặc `agent`)
3. Gọi `/api/agent.php` — xem mục **4b** bên dưới
4. Khách vẫn gửi qua `/api/submit_form.php` hoặc widget embed (có captcha); Agent API **không** đi qua captcha vì đã xác thực bằng key

---

## 4. Agent API — gợi ý nhanh

- **Endpoint:** `POST /api/agent.php?action={action}` (cần license + key hợp lệ)
- **Auth:** header `Authorization: Bearer aiw_…` hoặc body `api_key`
- **Body:** JSON (`Content-Type: application/json`) hoặc form fields
- **Khám phá:** `action=list_actions` — trả về toàn bộ action + scope
- **Đọc trước khi ghi:** `status`, `list_landings`, `list_blog_posts`, `list_forms`, …
- **Ghi landing (trang đã có hoặc mới):** `upsert_landing_page` — scope `content.write` (xem **4c**)
- **Ghi khác:** `upsert_product`, `upsert_form`, `patch_blog_content`, …
- **Migrate web cũ:** `upsert_landing`, `import_manifest`, `import_assets` — skill `aiweb-migrate`; nên `dry_run: true` trước
- **Xóa nguy hiểm:** bắt buộc `"confirm": "DELETE"` trong JSON body

Chi tiết đầy đủ: `guide_public.php` hoặc `action=list_actions` trên site của bạn.

### 4a. Scope thường gặp

| Scope | Nhóm action |
|-------|-------------|
| `migration` | import landing/blog, assets |
| `content.read` / `content.write` / `content.delete` | landing, blog |
| `shop.read` / `shop.write` / `shop.delete` | sản phẩm, đơn hàng |
| `digital.read` / `digital.write` / `digital.delete` | sản phẩm số |
| `forms.read` / `forms.write` / `forms.delete` | biểu mẫu, đăng ký |
| `media.read` / `media.write` / `media.delete` | ảnh |
| `settings.read` / `settings.write` | cài đặt site |
| `agent` | full quyền (key mặc định khi tạo trong admin) |

### 4c. Landing — action & scope

**Phân biệt:**

| Mục đích | Action | Scope |
|----------|--------|-------|
| Tạo/sửa trang trên site hiện tại (admin hoặc agent) | `upsert_landing_page` | `content.write` |
| Migrate / map `source_domain` + `source_key` | `upsert_landing` | `migration` |

**Luồng sửa trang đã tạo trong admin (khuyến nghị):**

1. `get_landing` với `slug`, `page_id`, hoặc `url` (URL public `https://site.com/{slug}` — API lấy segment cuối path)
2. Chỉnh HTML → `upsert_landing_page` với **toàn bộ** `html_content` hoặc mảng `sections` (ghi đè section, không merge từng đoạn)
3. Chỉ đổi SEO/title: gửi field metadata, **không** gửi `html_content`/`sections`

| Action | Scope | Mô tả |
|--------|-------|--------|
| `list_landings` | `content.read` | Danh sách trang |
| `get_landing` | `content.read` | Chi tiết + sections (`include_sections`) |
| `export_landing` | `content.read` | Export JSON |
| `upsert_landing_page` | `content.write` | Tạo (`title` + `slug` + HTML) hoặc sửa (`slug` / `page_id` / `url` + nội dung hoặc metadata) |
| `publish_batch` | `content.write` | Publish theo slug (`type`: `landing`) |
| `delete_landing` | `content.delete` | Xóa — cần `confirm: DELETE` |

**Nhận diện trang khi ghi:** `page_id`, `slug`, `page_url`, `url` / `landing_url` (URL đầy đủ).

**Ví dụ sửa theo link user đưa:**

```json
{
  "action": "upsert_landing_page",
  "url": "https://tenmien.com/gioi-thieu",
  "html_content": "<main>...</main>"
}
```

**Ví dụ tạo mới:**

```json
{
  "action": "upsert_landing_page",
  "title": "Giới thiệu",
  "slug": "gioi-thieu",
  "html_content": "<main>...</main>",
  "is_published": false
}
```

Dùng `dry_run: true` để xem `action` `create` | `update` trước khi ghi.

### 4b. Biểu mẫu — action & scope

**Điều kiện:** module Biểu mẫu đã bật (`module_forms_enabled`). Nếu chưa bật → API trả lỗi.

| Action | Scope | Mô tả |
|--------|-------|--------|
| `list_forms` | `forms.read` | Danh sách form (`status`, `search`, `limit`, `offset`, `include_fields`) |
| `get_form` | `forms.read` | Chi tiết 1 form + fields (`id` hoặc `slug`) |
| `list_form_submissions` | `forms.read` | Danh sách đăng ký (`form_id` / `form_slug`, `search`, `limit`, `offset`) |
| `get_form_submission` | `forms.read` | Chi tiết 1 đăng ký (`id`; `include_meta` cho IP/UA) |
| `get_form_submission_stats` | `forms.read` | Thống kê theo ngày/tháng/năm |
| `upsert_form` | `forms.write` | Tạo/sửa form + `fields` array; hỗ trợ `dry_run` |
| `create_form_submission` | `forms.write` | Thêm đăng ký (import/sync); `data` theo field_key hoặc label |
| `delete_form` | `forms.delete` | Xóa form + fields + toàn bộ đăng ký — cần `confirm: DELETE` |
| `delete_form_submission` | `forms.delete` | Xóa 1 đăng ký — cần `confirm: DELETE` |

**Bảo mật biểu mẫu qua API:**

- IP/User-Agent chỉ trả khi `include_meta: true` (dữ liệu cá nhân)
- `create_form_submission` validate giống form công khai; form `inactive` bị từ chối
- `skip_notifications: true` — không gửi email/Telegram/auto-reply khi import hàng loạt
- `upsert_form` tự sanitize `redirect_url`, `auto_reply_body`; bật captcha khi có notify/auto-reply

**Ví dụ `upsert_form`:**

```json
{
  "name": "Liên hệ",
  "slug": "lien-he",
  "status": "active",
  "notify_emails": "admin@example.com",
  "fields": [
    {"label": "Họ tên", "type": "text", "required": true},
    {"label": "Email", "type": "email", "required": true},
    {"label": "Nội dung", "type": "textarea"}
  ]
}
```

**Ví dụ `create_form_submission`:**

```json
{
  "form_slug": "lien-he",
  "data": {
    "ho_ten": "Nguyễn A",
    "email": "a@example.com"
  },
  "skip_notifications": false
}
```

**Ví dụ xóa an toàn:**

```json
{
  "id": 42,
  "confirm": "DELETE"
}
```

**Phân biệt 2 API gửi form:**

| API | Ai dùng | Captcha | Auth |
|-----|---------|---------|------|
| `/api/submit_form.php` | Khách trên web | Có | Không |
| `create_form_submission` | Agent/script đã có key | Không | API key + `forms.write` |

---

## 5. Skill liên quan

| Skill | Khi dùng |
|-------|----------|
| **aiweb-migrate** | Import landing/blog từ web cũ, video→blog |
| **seo** | Audit SEO site |
| **slimemail-ai-agent** | Điều khiển SlimEmail (nếu dùng SlimEmail) |

---

## 6. Trước khi kết thúc (agent)

- [ ] Hướng dẫn qua **menu admin**, không đề xuất sửa file PHP/core
- [ ] Không lộ API key, mật khẩu, token Telegram/OAuth
- [ ] Xóa/xuất bulk: hỏi xác nhận rõ; API xóa form/đăng ký cần `confirm: DELETE`
- [ ] Landing: dùng `upsert_landing_page` (không `upsert_landing` trừ migrate); sửa HTML thì `get_landing` trước hoặc gửi full `html_content`
- [ ] Biểu mẫu qua Agent API: kiểm tra module đã bật; lead công khai vẫn qua `submit_form.php`
- [ ] Nếu app &lt; 2.3.11: nhắc cập nhật qua **Cài đặt → Cập nhật** trước khi dùng Agent API biểu mẫu
