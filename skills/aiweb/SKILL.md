---
name: aiweb
description: >-
  Operate and automate any AIWeb/AIPage site through its Agent API and migration
  tools. Use when Codex needs to connect to an AIWeb site, inspect health and
  actions, manage landing pages, blog posts, categories, media, settings, shop
  products, or migrate landing/blog content from any source domain into any
  licensed AIWeb target. Also use for AIWeb video-to-blog publishing workflows.
---

# AIWeb Generic Agent

Use this skill for any AIWeb/AIPage instance. Do not assume a fixed domain such
as `ai.slim.vn`, `slimcrm.vn`, or localhost. Always derive the target from the
user's `AIWEB_BASE`/URL and API key.

## Required Inputs

- Target AIWeb base URL, for example `https://example.com`
- Agent API key, normally `aiw_...`
- Task scope: inspect, edit content, migrate, publish, settings, media, shop, or video-to-blog

Never print the full API key back to the user. Use it only in request headers or
temporary local env/config files.

## Connection Check

Prefer `/api/agent.php` for broad AIWeb actions. Use `/api/migration.php` only
for migration-compatible runners.

```powershell
$env:AIWEB_BASE = "https://example.com"
$env:MIGRATION_API_KEY = "aiw_..."
python tools/migration/runners/import_manifest.py --ping-only --env tools/migration/config.env
```

If `httpx` has TLS/network trouble on Windows but Python `requests` works, use a
small requests wrapper for API checks and report the transport issue clearly.

Core checks:

- `GET {AIWEB_BASE}/api/agent.php?action=ping`
- `GET {AIWEB_BASE}/api/agent.php?action=status`
- `GET {AIWEB_BASE}/api/agent.php?action=list_actions`

## Common Agent API Actions

Read actions before writing:

- Content read: `list_landings`, `get_landing`, `list_blog_posts`, `get_blog_post`, `list_categories`
- Content write: `upsert_landing`, `upsert_blog_post`, `upsert_category`, `publish_batch`, `set_default_index_page`
- Migration: `import_asset`, `import_assets`, `get_asset_map`, `rewrite_html`, `import_manifest`, `list_entities`
- Media: `upload_asset_base64`, `list_images`, `delete_image`
- Settings: `get_settings`, `patch_settings`
- Shop when enabled: `list_products`, `upsert_product`, `delete_product`

Use `dry_run: true` where supported before destructive or bulk writes. Require an
explicit user confirmation before deleting or purging content; destructive API
payloads must include the API's required confirmation field, such as
`"confirm": "DELETE"` when documented by AIWeb.

## Migration Workflow

Use the migration tools in `tools/migration` for source website import. The
workflow is intentionally gated:

1. Collect `source_domain`, one or more `start_url`, target `AIWEB_BASE`, and API key.
2. Run recon:
   `python tools/migration/scrapers/site_recon.py --domain {source_domain} --url {start_url} --sitemap`
3. Review inventory:
   `python tools/migration/runners/review_inventory_plan.py --file output/{domain_key}_inventory.json`
4. Ask the user to choose `all`, numbers like `1,3,5-8`, or `cancel`.
5. Extract only selected pages:
   `python tools/migration/scrapers/site_extract.py --domain {source_domain} --only key1,key2`
6. Review manifest:
   `python tools/migration/runners/review_manifest_plan.py --file output/{domain_key}_manifest.json`
7. Dry-run import:
   `python tools/migration/runners/import_manifest.py --env config.env --file output/{domain_key}_manifest.json --dry-run`
8. Import for real only after confirmation. Default to draft unless the user asks to publish.
9. Verify with `list_entities`, public URLs, and asset URLs.

Do not import real data before the user has seen the inventory plan and the
manifest plan.

## Environment File

Create a temporary `config.env` per target when useful:

```env
AIWEB_BASE=https://target-domain.com
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

For Nginx document roots where `/uploads/...` is not rewritten to
`aiweb_core/uploads/...`, add:

```env
MIGRATION_USE_NGINX_ROOT_PATH=1
```

or:

```env
MIGRATION_UPLOAD_PREFIX=aiweb_core/uploads
```

## Video To Blog

Use `tools/video_blog/video_to_aiweb_blog.py` when the user provides a YouTube
or source video and wants an AIWeb blog post.

1. Prepare artifacts:
   `python tools/video_blog/video_to_aiweb_blog.py prepare --url "VIDEO_URL" --output-root output/video_blogs`
2. Edit `article.html`, `article_meta.json`, and `frame_plan.json`.
3. Publish only when the user approves. Note: the command named
   `publish-draft` currently publishes with `status: published`.

## Reporting

Report:

- Target base URL and service version when available
- Counts before/after: landings, posts, categories, products
- URLs or slugs changed
- Whether writes were dry-run or real
- Any network, license, or auth issue without exposing secrets
