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
