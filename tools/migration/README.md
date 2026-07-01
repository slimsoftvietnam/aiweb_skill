# Migration Tools - Any Domain To AIWeb

Generic pipeline for migrating landing pages, blog posts, assets, and optional
products from any source domain into any licensed AIWeb/AIPage target through
the Agent/Migration API.

## Setup

```bash
cd tools/migration
pip install -r requirements.txt
cp config.example.env config.env
```

`config.env`:

```env
AIWEB_BASE=https://target-aiweb.example
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

`AIWEB_BASE` is the public site root. Do not append `aiweb_core`; runners call
`{AIWEB_BASE}/api/migration.php`.

For Nginx hosts that serve uploads directly from `aiweb_core/uploads`, add:

```env
MIGRATION_USE_NGINX_ROOT_PATH=1
```

or:

```env
MIGRATION_UPLOAD_PREFIX=aiweb_core/uploads
```

## Workflow

```bash
# 1. Recon
python scrapers/site_recon.py --domain example.com --url https://example.com/ --sitemap

# 2. Review plan and ask the user to choose all, numbers, or cancel
python runners/review_inventory_plan.py --file output/example_com_inventory.json

# 3. Extract selected pages
python scrapers/site_extract.py --domain example.com --only home,about

# 4. Review manifest
python runners/review_manifest_plan.py --file output/example_com_manifest.json

# 5. Dry-run import
python runners/import_manifest.py --env config.env --file output/example_com_manifest.json --dry-run

# 6. Real import after explicit confirmation
python runners/import_manifest.py --env config.env --file output/example_com_manifest.json --force
```

Add `--publish` only when the user explicitly wants imported landings/posts to
be public immediately. Otherwise preserve draft status from the manifest.

## Assets

The generic extractor imports assets from the selected source domain and its
subdomains, excluding common external hosts such as Google Fonts, GTM, GA,
jsdelivr, and cdnjs. Assets are stored by AIWeb under:

```text
uploads/migrate/{source_domain}/{css|js|fonts|img}/...
```

The import runner reuses existing asset mappings and can rewrite HTML through
the API or client-side for Nginx upload prefixes.

## Domain-Specific Scrapers

Use `site_recon.py` and `site_extract.py` first. Add a domain-specific scraper
only when a source site has unusual routing, hidden APIs, or markup that the
generic extractor cannot classify reliably. Domain-specific scrapers must output
the same manifest schema used by `site_extract.py`.
