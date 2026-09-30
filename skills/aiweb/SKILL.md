---
name: aiweb
description: >-
  Guide AIWeb/AIPage site owners to manage landing, blog, shop, digital products,
  forms, helpdesk, and affiliate through the admin UI and their own Agent API key.
  Use for licensed customers configuring content and automation — not for editing
  PHP source code. Synced with AIWeb 2.3.11.
---

# AIWeb — Skill for site owners (sync: app **2.3.11**)

For **licensed site owners** using AIWeb admin or their **Agent API key** in
Cursor/Codex. Not for PHP core development.

Prefer **Settings and admin menus** before API calls. In-app help: **Guide**
(`guide_public.php`). Migration / video→blog: skill **`aiweb-migrate`** in this repo.

---

## 1. What you need

| Item | Notes |
| --- | --- |
| Site URL | e.g. `https://myshop.com` |
| Admin login | `/login` — password you set at install |
| API key (optional) | **Settings → API Agent** — `aiw_…` for automation |

**Security — do not:**

- Paste full **API keys**, admin passwords, Telegram tokens, or OAuth secrets into public chats.
- Ask the agent to **repeat** your key/password; use headers or a local config file only.
- Connect Agent API only to **your** licensed domain.

---

## 2. URLs owners use

| URL | Purpose |
| --- | --- |
| `/`, `/{slug}` | Published landing |
| `/blog`, `/shop`, `/digital` | Public blog / shop / digital store |
| `/form/embed/{slug}` | Embedded form (module on) |
| `/api/submit_form.php` | Public form submit (POST, captcha + rate limit) |
| `/support`, `/aff` | Helpdesk, affiliate portal |
| `/login`, `/manage`, `/create`, `/create_secion` | Admin |
| `/blog`, `/products`, `/orders` | Content & orders |
| `/forms`, `?action=form_submissions` | Forms admin & submissions |
| `/settings` | All configuration |
| `/sitemap.xml` | SEO |

**Language:** **Settings → General → UI language** (`vi` / `en`).

---

## 3. Common tasks (admin UI)

| Task | Where in admin |
| --- | --- |
| New site setup | Install wizard → license → Settings → create landing → blog/products |
| Paste HTML landing | Create page → editor HTML tab → widgets → publish |
| Migrate old website | Skill `aiweb-migrate` + API key in Settings |
| Video → blog | Skill `aiweb-migrate` (`video_to_aiweb_blog.py`) |
| Digital products | Settings → Digital → products/orders |
| Shop + VietQR | Settings → Shop, Payments, order notifications |
| Helpdesk / Affiliate / SlimEmail | Matching Settings tabs |
| Forms | Settings → Forms → Forms menu → embed via editor or `/form/embed/{slug}` |
| Backup / update app | Settings → Database, Settings → Update (patch ZIP) |
| SEO | Settings → SEO + per-page SEO in editor |

---

## 4. Agent API (owners with API key)

- **Endpoint:** `POST {your-site}/api/agent.php?action={action}` (license + valid key)
- **Auth:** `Authorization: Bearer aiw_…` or body `api_key`
- **Discover:** `action=list_actions` — all actions + scopes
- **Test:** **Settings → API Agent** test button, or `action=ping` / `action=status`
- **Read before write:** `list_landings`, `list_blog_posts`, `list_forms`, …
- **Landing create/update on your site:** `upsert_landing_page` — scope `content.write` (see **4c**)
- **Other writes:** `upsert_product`, `upsert_form`, `patch_blog_content`, …
- **Migrate old site:** `upsert_landing`, `import_manifest` — skill `aiweb-migrate`; use **dry_run** first
- **Destructive:** send `"confirm": "DELETE"` in JSON body

Full action list: `guide_public.php` on your site or `action=list_actions`.

Never print the owner's full API key in responses.

### 4a. Common scopes

| Scope | Area |
| --- | --- |
| `migration` | import landing/blog, assets |
| `content.read` / `content.write` / `content.delete` | landing, blog |
| `shop.read` / `shop.write` / `shop.delete` | products, orders |
| `digital.read` / `digital.write` / `digital.delete` | digital products |
| `forms.read` / `forms.write` / `forms.delete` | forms, submissions |
| `media.*`, `settings.*` | images, site settings |
| `agent` | full access (default key scope in admin) |

### 4c. Landing — Agent API

| Goal | Action | Scope |
| --- | --- | --- |
| Create/update pages on the live site (admin or agent) | `upsert_landing_page` | `content.write` |
| Migrate with `source_domain` + `source_key` | `upsert_landing` | `migration` |

**Recommended edit flow (page already in admin):**

1. `get_landing` with `slug`, `page_id`, or `url` (public URL `https://site.com/{slug}` — API uses the last path segment)
2. Edit HTML → `upsert_landing_page` with full `html_content` or `sections` array (replaces sections; not a partial merge)
3. SEO/title only: send metadata fields; omit `html_content` / `sections`

| Action | Scope | Purpose |
| --- | --- | --- |
| `list_landings` | `content.read` | List pages |
| `get_landing` | `content.read` | Page + sections (`include_sections`) |
| `export_landing` | `content.read` | JSON export |
| `upsert_landing_page` | `content.write` | Create (`title` + `slug` + HTML) or update (`slug` / `page_id` / `url` + content or metadata) |
| `publish_batch` | `content.write` | Publish by slug (`type`: `landing`) |
| `delete_landing` | `content.delete` | Delete — needs `confirm: DELETE` |

**Identify page:** `page_id`, `slug`, `page_url`, `url` / `landing_url` (full public URL).

```json
{
  "action": "upsert_landing_page",
  "url": "https://example.com/about",
  "html_content": "<main>...</main>"
}
```

Use `dry_run: true` to preview `create` vs `update`. Vietnamese detail: `SKILL.vi.md`.

### 4b. Forms — Agent API (2.3.11+)

**Requires:** Forms module enabled in **Settings → Forms**.

| Action | Scope | Purpose |
| --- | --- | --- |
| `list_forms` | `forms.read` | List forms (`status`, `search`, pagination, `include_fields`) |
| `get_form` | `forms.read` | One form + fields (`id` or `slug`) |
| `list_form_submissions` | `forms.read` | Submissions (`form_id` / `form_slug`, `search`) |
| `get_form_submission` | `forms.read` | One submission (`include_meta` for IP/UA) |
| `get_form_submission_stats` | `forms.read` | Stats by day/month/year |
| `upsert_form` | `forms.write` | Create/update form + `fields`; supports `dry_run` |
| `create_form_submission` | `forms.write` | Add submission (import/sync); `data` by field_key or label |
| `delete_form` | `forms.delete` | Delete form + fields + all submissions — needs `confirm: DELETE` |
| `delete_form_submission` | `forms.delete` | Delete one submission — needs `confirm: DELETE` |

**Security:**

- IP/User-Agent only when `include_meta: true`
- `create_form_submission` validates like public submit; rejects `inactive` forms
- `skip_notifications: true` — no email/Telegram/auto-reply on bulk import
- Public visitors still use `/api/submit_form.php` (captcha + rate limit)

**Example `upsert_form`:**

```json
{
  "name": "Contact",
  "slug": "contact",
  "status": "active",
  "fields": [
    {"label": "Name", "type": "text", "required": true},
    {"label": "Email", "type": "email", "required": true}
  ]
}
```

---

## 5. Version note

- **Latest sync:** `upsert_landing_page` for direct landing create/update via Agent API (`content.write`).
- **2.3.11+:** Forms Agent API (`forms.read` / `forms.write` / `forms.delete`).
- **2.3.10+:** Forms module, embed URLs.
- Older app: update via **Settings → Update** before using new features.
- After update: log in once so the database upgrades, then `action=status` to confirm version.

---

## 6. Related skills

| Skill | Use |
| --- | --- |
| **aiweb-migrate** | Import from another website, video→blog |
| **seo** | SEO audit |
| **slimemail-ai-agent** | SlimEmail (if used) |

---

## 7. Agent checklist

- [ ] Guide via **admin UI**, not PHP file edits
- [ ] Do not expose API keys, passwords, or integration secrets
- [ ] Confirm before bulk delete; API deletes need `confirm: DELETE`
- [ ] Landing: use `upsert_landing_page` (not `upsert_landing` except migrate); full `html_content` when replacing HTML
- [ ] Forms via Agent API: module must be on; public leads still use `submit_form.php`
- [ ] Match guidance to the site's reported version from `status`
