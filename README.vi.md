# AIWeb Skills - Công cụ Agent và Migration

[English](README.md) | Tiếng Việt

Repo này chứa skill cho Codex/Cursor và các công cụ Python để vận hành mọi site
AIWeb/AIPage đã có license qua Agent API, đồng thời migrate landing/blog từ bất
kỳ domain nguồn nào vào bất kỳ site AIWeb đích nào.

Repo này **không** chứa mã nguồn PHP của AIWeb. Cài repo `aiweb` riêng để chạy
runtime.

## Cấu Trúc

```text
aiweb_skill/
|-- skills/aiweb/           # Skill tổng quát: Agent API + migration
|-- skills/aiweb-migrate/   # Skill riêng cho migration
|-- tools/migration/        # Migrate mọi domain nguồn -> mọi AIWeb đích
`-- tools/video_blog/       # Video/YouTube -> bài blog AIWeb
```

## Cài Đặt Nhanh

```bash
git clone https://github.com/slimsoftvietnam/aiweb_skill.git
git clone https://github.com/slimsoftvietnam/aiweb.git

cd aiweb_skill/tools/migration
pip install -r requirements.txt
cp config.example.env config.env
```

`config.env`:

```env
AIWEB_BASE=http://localhost/aiweb
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

## Agent API

Site AIWeb đích phải được kích hoạt license. Nếu thiếu license, API thường trả
HTTP 403.

| Endpoint | Mục đích |
| --- | --- |
| `/api/agent.php` | Khuyến nghị dùng; có đầy đủ action Agent API |
| `/api/migration.php` | Alias tương thích cho runner migration cũ |

```bash
curl "http://localhost/aiweb/api/agent.php?action=list_actions" \
  -H "Authorization: Bearer aiw_KEY"
```

Nên dùng API key có scope `agent` để tự động hóa đầy đủ. Các thao tác xóa/purge
cần field xác nhận theo API, ví dụ `"confirm": "DELETE"` khi AIWeb yêu cầu.

## Skill

Copy `skills/aiweb/` vào thư mục skill của Codex/Cursor khi muốn dùng đầy đủ:
kiểm tra kết nối, đọc/ghi nội dung, media, settings, shop, migration và
video-to-blog.

Copy `skills/aiweb-migrate/` nếu chỉ muốn trigger riêng cho migration.

## Use Case Và Prompt Mẫu

Dùng `$aiweb` cho vận hành AIWeb thông thường. Dùng `$aiweb-migrate` khi nhiệm
vụ chính là chuyển nội dung từ website khác vào AIWeb.

| Use case | Làm gì | Prompt đơn giản |
| --- | --- | --- |
| Kết nối site | Kiểm tra API, version, module đang bật và số lượng nội dung. | `Dùng $aiweb kết nối https://my-site.com với API key aiw_... và báo tình trạng site.` |
| Liệt kê nội dung | Xem landing page, bài blog, danh mục, sản phẩm hoặc media hiện có. | `Dùng $aiweb liệt kê toàn bộ landing page trên https://my-site.com.` |
| Tạo landing page | Tạo hoặc cập nhật landing page từ nội dung/HTML được cung cấp. | `Dùng $aiweb tạo landing page nháp tên "Tư vấn AI" trên https://my-site.com.` |
| Sửa landing page | Đọc trang hiện có, sửa copy/HTML/SEO rồi lưu lại. | `Dùng $aiweb tối ưu SEO và headline của landing page /home.` |
| Đặt trang chủ | Đặt default index page cho site AIWeb. | `Dùng $aiweb đặt /home làm trang chủ.` |
| Viết blog | Tạo danh mục nếu cần, viết bài và lưu nháp hoặc publish. | `Dùng $aiweb viết và đăng bài blog về tự động hóa AI cho doanh nghiệp nhỏ.` |
| Sửa blog | Sửa title, nội dung, SEO description, ảnh hoặc danh mục bài viết. | `Dùng $aiweb cập nhật bài /blog/my-post và làm phần mở đầu rõ hơn.` |
| Upload media | Upload ảnh/file và trả về URL dùng được trên AIWeb. | `Dùng $aiweb upload ảnh này và gửi tôi public URL.` |
| Cập nhật settings | Đọc hoặc sửa brand, SEO, tracking code, schema, shop hoặc module settings. | `Dùng $aiweb cập nhật site title, meta description và brand name.` |
| Quản lý sản phẩm shop | Liệt kê, tạo, sửa hoặc xóa sản phẩm khi shop action được bật. | `Dùng $aiweb tạo sản phẩm "Gói Starter" giá 990000.` |
| Migrate website | Quét URL nguồn, đưa plan, extract, dry-run rồi import sau khi được duyệt. | `Dùng $aiweb-migrate migrate https://old-site.com vào https://my-aiweb.com, bắt đầu với trang chủ.` |
| Migrate trang được chọn | Chỉ import URL hoặc số thứ tự trang mà user duyệt. | `Dùng $aiweb-migrate quét https://old-site.com rồi migrate trang 1,3,5-8.` |
| Migrate blog | Import bài blog cũ vào blog AIWeb, gồm danh mục và ảnh. | `Dùng $aiweb-migrate migrate blog từ https://old-site.com/blog vào AIWeb, lưu nháp trước.` |
| Video thành blog | Chuyển video/YouTube thành bài blog AIWeb có ảnh cắt từ video. | `Dùng $aiweb chuyển video YouTube này thành bài blog AIWeb nháp: https://youtube.com/watch?v=...` |
| Verify nội dung import | Kiểm tra entity, URL public và asset sau import. | `Dùng $aiweb kiểm tra các trang import từ old-site.com và báo ảnh nào lỗi.` |
| Dọn nội dung migrate | Xem hoặc xóa nội dung migrate, chỉ xóa khi có xác nhận rõ. | `Dùng $aiweb cho tôi xem những gì đã import từ old-site.com trước khi quyết định xóa.` |

Prompt tiếng Việt ngắn:

- `Kết nối site https://my-site.com bằng API key aiw_... và báo tình trạng.`
- `Liệt kê toàn bộ landing page và bài blog hiện có.`
- `Tạo landing page nháp cho dịch vụ tư vấn AI.`
- `Tối ưu SEO trang /home, giữ nguyên bố cục hiện tại.`
- `Viết 5 bài blog về tự động hóa AI, lưu nháp trước.`
- `Migrate trang chủ từ https://old-site.com sang AIWeb, dry-run trước rồi hỏi tôi xác nhận.`
- `Quét website cũ và cho tôi chọn trang nào cần migrate.`
- `Chuyển video YouTube này thành bài blog AIWeb, có ảnh cắt từ video.`
- `Kiểm tra các trang đã migrate từ old-site.com có ảnh nào lỗi không.`

## Migration

Input cần có:

- `source_domain`
- một hoặc nhiều `start_url`
- `AIWEB_BASE` của site đích
- API key của site đích

Quy trình:

1. Quét URL nguồn.
2. Hiển thị inventory plan để user chọn.
3. Extract các trang đã chọn thành manifest.
4. Hiển thị manifest plan để user duyệt.
5. Dry-run import.
6. Chỉ import thật sau khi user xác nhận.
7. Verify entity và URL public.

```bash
cd tools/migration
python scrapers/site_recon.py --domain example.com --url https://example.com/ --sitemap
python runners/review_inventory_plan.py --file output/example_com_inventory.json
python scrapers/site_extract.py --domain example.com --only home,about
python runners/review_manifest_plan.py --file output/example_com_manifest.json
python runners/import_manifest.py --env config.env --file output/example_com_manifest.json --dry-run
```

## Tài Liệu Thêm

- `tools/migration/README.md` - chi tiết script migration
- `tools/video_blog/README.md` - quy trình video-to-blog
- Tài liệu Agent API nằm trong repo `aiweb`: `README.md` và `guide_public.php`
