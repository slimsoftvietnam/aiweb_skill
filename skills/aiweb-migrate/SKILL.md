---
name: aiweb-migrate
description: >-
  Migrate landing pages, blog posts, assets, and optional product data from any
  source website into any licensed AIWeb/AIPage target through Agent API or
  Migration API. Use when the user provides a source domain/start URL and wants
  Codex to recon, plan, extract, dry-run, import, publish, verify, or convert a
  source video/YouTube video into an AIWeb blog post.
---

# AIWeb Migration

Use this skill for migration work only. For general AIWeb operations, use the
generic `aiweb` skill in this repo.

Do not assume any fixed source or target domain. Treat `slimcrm.vn` and
`ai.slim.vn` only as examples or optional domain-specific scrapers.

## Required Inputs

- `source_domain`: source website host, for example `example.com`
- `start_url`: one or more source URLs to recon
- `AIWEB_BASE`: target AIWeb root URL, for example `https://target.com`
- `MIGRATION_API_KEY`: target AIWeb Agent API key
- Scope: landing only, blog only, both, or selected URLs

Never print the full API key back to the user.

## Gate Rule

Do not import real data until the user has approved both:

1. Inventory plan after recon
2. Manifest plan after extract and dry-run

If the user says "migrate all", still show the plans before writing.

## Standard Workflow

Run commands from `tools/migration`.

```bash
python scrapers/site_recon.py \
  --domain {source_domain} \
  --url {start_url} \
  --sitemap
```

Review and ask the user to choose `all`, numbers like `1,3,5-8`, or `cancel`:

```bash
python runners/review_inventory_plan.py \
  --file output/{source_domain_with_dots_as_underscores}_inventory.json
```

Extract selected pages:

```bash
python scrapers/site_extract.py --domain {source_domain} --only key1,key2
```

Review manifest:

```bash
python runners/review_manifest_plan.py \
  --file output/{source_domain_with_dots_as_underscores}_manifest.json
```

Dry-run:

```bash
python runners/import_manifest.py --env config.env \
  --file output/{source_domain_with_dots_as_underscores}_manifest.json \
  --dry-run
```

Real import after confirmation:

```bash
python runners/import_manifest.py --env config.env \
  --file output/{source_domain_with_dots_as_underscores}_manifest.json \
  --force
```

Add `--publish` only when the user explicitly wants imported content public.

## Config

`config.env`:

```env
AIWEB_BASE=https://target-aiweb.example
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

`AIWEB_BASE` is the public site root. Do not append `aiweb_core`.

For Nginx hosts where `/uploads/...` is not rewritten to
`aiweb_core/uploads/...`, add:

```env
MIGRATION_USE_NGINX_ROOT_PATH=1
```

## Manifest Contract

Generic extractors write:

- `source_domain`
- `assets[]` with `source_url`
- `categories[]`
- `landing_pages[]` with `source_key`, `source_url`, `slug`, `title`, `html_content`, `is_published`
- `blog_posts[]` with `source_key`, `source_url`, `slug`, `title`, `content`, `category_slug`, `status`
- optional `product_categories[]` and `products[]`

Use `source_domain + source_key` as the idempotent identity.

## Verification

After import, verify:

- `list_entities` for the manifest `source_domain`
- public landing URLs like `/{slug}`
- public blog URLs like `/blog/{slug}`
- migrated asset URLs return HTTP 200
- no required image/CSS/JS still points to the old source domain unless intentionally external

Report counts, slugs, status, skipped URLs, dry-run result, and any auth/license
or network issue.

## Video To Blog

Use `tools/video_blog/video_to_aiweb_blog.py` when the input is a video or
YouTube URL.

```bash
python tools/video_blog/video_to_aiweb_blog.py prepare \
  --url "VIDEO_URL" \
  --output-root output/video_blogs
```

Review/edit `article.html`, `article_meta.json`, and `frame_plan.json`, then
publish only after approval:

```bash
python tools/video_blog/video_to_aiweb_blog.py publish-draft \
  --workdir output/video_blogs/VIDEO_ID \
  --env tools/migration/config.env
```

Note: the command name is `publish-draft` for compatibility, but the current
tool publishes with `status: published`.
