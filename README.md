# AIWeb Skills - Agent & Migration Tools

Generic Codex/Cursor skills and Python tools for operating any licensed
AIWeb/AIPage site through Agent API and for migrating landing/blog content from
any source domain into any AIWeb target.

This repository does **not** contain the AIWeb PHP application. Install the
separate `aiweb` repo for the runtime.

## Structure

```text
aiweb_skill/
├── skills/aiweb/           # Generic AIWeb Agent API + migration skill
├── skills/aiweb-migrate/   # Migration-focused workflow skill
├── tools/migration/        # Any source domain -> any AIWeb target
└── tools/video_blog/       # Video/YouTube -> AIWeb blog workflow
```

## Quick Install

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

Target AIWeb sites must be licensed. Missing license usually returns HTTP 403.

| Endpoint | Purpose |
| --- | --- |
| `/api/agent.php` | Recommended; full Agent API action surface |
| `/api/migration.php` | Migration-compatible alias for older runners |

```bash
curl "http://localhost/aiweb/api/agent.php?action=list_actions" \
  -H "Authorization: Bearer aiw_KEY"
```

Prefer API keys with `agent` scope for full automation. Destructive API actions
require the confirmation field documented by AIWeb, for example
`"confirm": "DELETE"`.

## Skills

Copy `skills/aiweb/` into Codex/Cursor skills for general AIWeb operation:
health checks, content read/write, media, settings, shop, migration, and
video-to-blog.

Copy `skills/aiweb-migrate/` when you only want migration-specific triggering.

## Use Cases And Simple Prompts

Use `$aiweb` for normal AIWeb operations. Use `$aiweb-migrate` when the main
task is moving content from another website into AIWeb.

| Use case | What it does | Simple prompt |
| --- | --- | --- |
| Connect to a site | Checks API health, version, enabled modules, and content counts. | `Use $aiweb to connect to https://my-site.com with API key aiw_... and show me the site status.` |
| List content | Shows current landing pages, blog posts, categories, products, or media. | `Use $aiweb to list all landing pages on https://my-site.com.` |
| Create a landing page | Creates or updates a landing page from provided HTML/content. | `Use $aiweb to create a draft landing page called "AI Consulting" on https://my-site.com.` |
| Edit a landing page | Reads an existing page, updates copy/HTML/SEO, then saves it. | `Use $aiweb to improve the SEO and headline of landing page /home.` |
| Set homepage | Sets the default index page for the AIWeb site. | `Use $aiweb to set /home as the homepage.` |
| Write a blog post | Creates a category if needed, writes a post, and saves as draft or published. | `Use $aiweb to write and publish a blog post about AI automation for small businesses.` |
| Fix blog content | Reads a post and patches title, body, SEO description, images, or category. | `Use $aiweb to update the blog post /blog/my-post and make the intro clearer.` |
| Upload media | Uploads an image/file and returns the usable AIWeb URL. | `Use $aiweb to upload this image and give me the public URL.` |
| Update settings | Reads or patches brand, SEO, tracking code, schema, shop, or module settings. | `Use $aiweb to update the site title, meta description, and brand name.` |
| Manage shop products | Lists, creates, updates, or deletes products when shop actions are enabled. | `Use $aiweb to create a product called "Starter Package" with price 990000.` |
| Migrate a website | Recons source URLs, shows a plan, extracts selected pages, dry-runs, then imports after approval. | `Use $aiweb-migrate to migrate https://old-site.com into https://my-aiweb.com. Start with the homepage only.` |
| Migrate selected pages | Imports only the URLs or plan numbers that the user approves. | `Use $aiweb-migrate to recon https://old-site.com, then migrate pages 1,3,5-8 only.` |
| Migrate blog posts | Imports old blog posts into AIWeb blog with categories and images. | `Use $aiweb-migrate to migrate the blog from https://old-site.com/blog into my AIWeb site as drafts.` |
| Video to blog | Turns a YouTube/source video into an AIWeb blog post with video frames as images. | `Use $aiweb to turn this YouTube video into a draft AIWeb blog post: https://youtube.com/watch?v=...` |
| Verify imported content | Checks migrated entities, public URLs, and asset URLs after import. | `Use $aiweb to verify all pages imported from old-site.com and report broken assets.` |
| Clean up migrated content | Deletes or purges migrated entities only after explicit confirmation. | `Use $aiweb to show me what was imported from old-site.com before I decide whether to delete it.` |

Human-friendly Vietnamese examples:

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

Required input:

- `source_domain`
- one or more `start_url`
- target `AIWEB_BASE`
- target API key

Workflow:

1. Recon source URLs.
2. Review inventory plan with the user.
3. Extract selected pages to manifest.
4. Review manifest plan with the user.
5. Dry-run import.
6. Import for real only after confirmation.
7. Verify entities and public URLs.

```bash
cd tools/migration
python scrapers/site_recon.py --domain example.com --url https://example.com/ --sitemap
python runners/review_inventory_plan.py --file output/example_com_inventory.json
python scrapers/site_extract.py --domain example.com --only home,about
python runners/review_manifest_plan.py --file output/example_com_manifest.json
python runners/import_manifest.py --env config.env --file output/example_com_manifest.json --dry-run
```

## More

- `tools/migration/README.md` - migration script details
- `tools/video_blog/README.md` - video-to-blog details
- AIWeb API docs live in the `aiweb` repo: `README.md` and `guide_public.php`
