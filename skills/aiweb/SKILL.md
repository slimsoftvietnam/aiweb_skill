---
name: aiweb
description: >-
  Operate and automate any AIWeb/AIPage site (v2.3.10+) through Agent API and
  migration tools. Covers landing, blog, shop, digital products, forms (lead
  capture), helpdesk, affiliate, security pages, i18n VI/EN, and video-to-blog.
  Use when connecting to an AIWeb site, managing content/settings/media, or when
  the user works in the aiweb PHP repo. Synced with aiweb 2.3.10.
---

# AIWeb Generic Agent (skill sync: AIWeb **2.3.10**)

Use this skill for any licensed AIWeb/AIPage instance. Do **not** assume a fixed
domain (`ai.slim.vn`, localhost, …). Derive `AIWEB_BASE` and API key from the
user.

**PHP app repo:** [github.com/slimsoftvietnam/aiweb](https://github.com/slimsoftvietnam/aiweb)  
**This repo:** skills + Python migration tools only (no PHP runtime).

Vietnamese dev/ops reference (same version): `aiweb` repo →
`.cursor/skills/aiweb/SKILL.md` and `docs/TINH_NANG.md`.

---

## 0. Version compatibility (read first)

Many customers still run **old AIWeb + old skill**. Match skill to app version.

| AIWeb app | This skill | What changes |
| --- | --- | --- |
| **2.3.10+** | **Current** (2026-07-31) | Forms module, `/security`, `security.txt`, login rate limit, editor image API auth |
| 2.3.6 – 2.3.9 | Mostly OK | No forms tables/UI; ignore forms URLs and `module_forms_enabled` |
| 2.2.x – 2.3.5 | Partial | Digital/helpdesk may differ; always call `action=status` first |
| &lt; 2.2 | Upgrade app first | Legacy section-builder UI removed; use **Cài đặt → Cập nhật** patch ZIP |

**After upgrading AIWeb:**

1. Pull latest `aiweb_skill` (`git pull`) and re-copy `skills/aiweb/` into Cursor/Codex skills.
2. Open the site once (admin login) so SQLite migrations run (`forms`, `login_attempts`, …).
3. `GET …/api/agent.php?action=status` — confirm `version` ≥ `2.3.10`.
4. Re-test Agent API key scopes in **Settings → API Agent**.

---

## 1. Architecture quick reference

| Piece | Path (inside `aiweb` repo) |
| --- | --- |
| Front controller | `index.php` → `?action=` |
| Pretty URLs | `.htaccess` |
| Admin pages | `aiweb_core/pages/*.php` |
| Logic | `aiweb_core/includes/` |
| Public API | `aiweb_core/api/*.php` → `/api/{name}.php` |
| SQLite DB | `aiweb_core/data/landing_pages.db` |
| Uploads | `aiweb_core/uploads/` |
| Local config | `aiweb_core/config/config.php` (gitignored) |

**PHP 7.4+**, no framework. License via `slim.vn` or local `dev_mode.php` (dev only;
exclude from production zip).

**New DB tables (2.3.10):** `forms`, `form_fields`, `form_submissions`, `login_attempts`.

---

## 2. Public URLs (frequent)

| URL | Purpose |
| --- | --- |
| `/`, `/{slug}` | Published landing |
| `/blog`, `/blog/{slug}` | Blog |
| `/shop`, `/shop/{slug}` | Physical shop |
| `/digital`, `/digital/{slug}` | Digital products |
| `/digital-access?token=` | Digital delivery |
| `/order-access?token=` | Shop order management (Telegram link) |
| `/form/embed/{slug}` | Standalone form embed (2.3.10+, module on) |
| `/support` | Public helpdesk |
| `/security` | Security policy + disclosure (2.3.10+) |
| `/.well-known/security.txt` | RFC 9116 (`security_txt.php`) |
| `/api/agent.php` | Agent REST API |
| `/api/submit_form.php` | POST public form submission (2.3.10+) |
| `/login` | Admin |

**i18n:** single setting `public_ui_lang` (`vi` \| `en`) in Settings. Public scopes
include `blog`, `shop`, `digital`, `helpdesk`, `support`, `license`, `security`.

---

## 3. Required inputs

- Target **AIWEB_BASE** (public site root, **no** `/aiweb_core` suffix)
- Agent API key (`aiw_…`)
- Task: inspect, content, settings, shop, digital, migration, video-to-blog, or PHP dev

Never print the full API key. Use headers or local `config.env` only.

---

## 4. Connection check

Prefer `/api/agent.php`. Use `/api/migration.php` only for legacy runners.

```powershell
$env:AIWEB_BASE = "https://example.com"
$env:MIGRATION_API_KEY = "aiw_..."
python tools/migration/runners/import_manifest.py --ping-only --env tools/migration/config.env
```

Core checks:

- `GET {AIWEB_BASE}/api/agent.php?action=ping`
- `GET {AIWEB_BASE}/api/agent.php?action=status` → read `version`, module flags, counts
- `GET {AIWEB_BASE}/api/agent.php?action=list_actions`

If Windows `httpx` TLS fails but `requests` works, use requests and report clearly.

---

## 5. Agent API actions

Read `list_actions` before writes. Prefer `dry_run: true` when supported.

| Group | Examples |
| --- | --- |
| Read | `list_landings`, `get_landing`, `list_blog_posts`, `get_blog_post`, `list_categories`, `list_products`, `list_images` |
| Write | `upsert_landing`, `upsert_blog_post`, `upsert_category`, `publish_batch`, `set_default_index_page` |
| Migration | `import_asset`, `import_assets`, `import_manifest`, `rewrite_html`, `get_asset_map`, `list_entities` |
| Media | `upload_asset_base64`, `list_images`, `delete_image` |
| Settings | `get_settings`, `patch_settings` |
| Shop | `upsert_product`, `delete_product` (when shop enabled) |
| Digital | scopes `digital.read/write/delete` on keys (when digital module on) |

Destructive calls need explicit user confirmation and API fields such as
`"confirm": "DELETE"` when documented.

**Forms (2.3.10):** managed in admin UI (`/forms`, `/form_submissions`), **not** Agent API
yet. Public submit: `POST /api/submit_form.php` with `form_slug`, `field_{key}`, captcha fields.

---

## 6. Forms module (2.3.10+)

Admin-only automation unless using public submit API.

1. **Settings → Forms:** enable `module_forms_enabled`; optional reCAPTCHA/Turnstile keys.
2. Admin `?action=forms` — create form, fields: text, email, phone, textarea, select, checkbox.
3. Captcha per form: `math`, `checkbox`, `recaptcha_v2/v3`, `turnstile`.
4. Notifications: admin email + Telegram; optional auto-reply (`{{form_name}}`, `{{email}}`, …).
5. Embed in landing (editor toolbar **Form** or HTML):
   - `data-aiweb-widget="form" data-form="{slug}"`
   - `<!-- AIWEB:FORM slug="{slug}" -->`
   - iframe URL: `/form/embed/{slug}`
6. Submissions: `?action=form_submissions` (CSV export).
7. Rate limit: 5 submissions / IP / 10 minutes.

If `module_forms_enabled` is off or version &lt; 2.3.10, skip this section.

---

## 7. Security notes (2.3.10)

For operators and PHP developers:

- Login redirect sanitized (`aiweb_sanitize_redirect_url`) — no open redirect on `?redirect=`.
- Admin login rate limit: 8 attempts / 15 min / IP (`login_attempts` table).
- `get_all_images.php` requires **session auth** (`requireAuthApi`) — unauthenticated → 401.
- Emergency break-glass login: `config.php` constants `EMERGENCY_ACCESS_*`; CLI
  `php aiweb_core/scripts/generate_emergency_access.php --password "…" --write-config`.
- `security_contact_email` setting (fallback admin notify email) feeds `/security` and `security.txt`.

Do not commit `config.php`, `license.key`, or emergency password hashes.

---

## 8. Human prompt examples

- "Connect to https://example.com with API key aiw_… and show status and version."
- "List all landing pages and blog posts."
- "Create a draft landing page for AI consulting."
- "Improve SEO for /home without changing layout."
- "Write and publish a blog post about AI automation."
- "Upload this image and return the public URL."
- "Patch site title and meta description via patch_settings."
- "Create shop product Starter Package price 990000."
- "Migrate https://old-site.com — dry-run first, wait for my approval."
- "Turn this YouTube video into an AIWeb blog post."
- "On 2.3.10 site, enable forms module and describe how to embed form slug contact-us."

---

## 9. Migration workflow

Use `tools/migration`. Gated workflow — see skill `aiweb-migrate` for details.

1. Collect `source_domain`, `start_url`, target `AIWEB_BASE`, API key.
2. Recon → inventory plan → **user chooses** pages.
3. Extract → manifest plan → dry-run → import after confirmation.
4. Default **draft** unless user asks to publish.
5. Verify `list_entities`, public URLs, asset HTTP 200.

Do not import before user approves inventory and manifest plans.

---

## 10. Environment file

```env
AIWEB_BASE=https://target-domain.com
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...
```

`AIWEB_BASE` = public root (e.g. `http://localhost/aiweb`), **not** `…/aiweb_core`.

Nginx docroot without upload rewrite:

```env
MIGRATION_USE_NGINX_ROOT_PATH=1
```

or `MIGRATION_UPLOAD_PREFIX=aiweb_core/uploads`.

---

## 11. Video to blog

`tools/video_blog/video_to_aiweb_blog.py`:

1. `prepare --url "VIDEO_URL" --output-root output/video_blogs`
2. Edit `article.html`, `article_meta.json`, `frame_plan.json`.
3. `publish-draft` after user approval (command name legacy; publishes `status: published`).

Use `src="/uploads/upload/..."` in HTML (leading slash) for blog URLs.

---

## 12. PHP dev conventions (aiweb repo)

| Task | Hint |
| --- | --- |
| Admin label | `ui_lang_admin.php` (vi + en), `ui_admin()` |
| Public label | `ui_lang.php`, `ui_t()` |
| New route | `.htaccess` + `pages/` |
| New API | `api/` + auth/license as needed |
| Editor image APIs | session auth for list endpoints |
| Widget | `includes/widgets/` + `widget_resolver.php` |

```powershell
php -l aiweb_core\pages\settings.php
php aiweb_core\scripts\check_ui_admin_lang_keys.php
php aiweb_core\scripts\seed_forms_demo.php
```

---

## 13. Reporting

Report to the user:

- Target base URL and **app version** from `status`
- Counts: landings, posts, categories, products (if applicable)
- Whether forms module is enabled (2.3.10+)
- URLs/slugs changed; dry-run vs real writes
- Auth, license, or network issues **without** exposing secrets
