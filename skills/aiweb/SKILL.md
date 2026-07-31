---
name: aiweb
description: >-
  Guide AIWeb/AIPage site owners to manage landing, blog, shop, digital products,
  forms, helpdesk, and affiliate through the admin UI and their own Agent API key.
  Use for licensed customers configuring content and automation — not for editing
  PHP source code. Synced with AIWeb 2.3.10.
---

# AIWeb — Skill for site owners (sync: app **2.3.10**)

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
| `/form/embed/{slug}` | Embedded form (2.3.10+, module on) |
| `/support`, `/aff` | Helpdesk, affiliate portal |
| `/login`, `/manage`, `/create`, `/create_secion` | Admin |
| `/blog`, `/products`, `/orders` | Content & orders |
| `/forms` | Forms admin (2.3.10+) |
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
| Forms (2.3.10+) | Settings → Forms → Forms menu → embed via editor or `/form/embed/{slug}` |
| Backup / update app | Settings → Database, Settings → Update (patch ZIP) |
| SEO | Settings → SEO + per-page SEO in editor |

---

## 4. Agent API (owners with API key)

- Endpoint: `{your-site}/api/agent.php` (license + valid key required)
- Test: **Settings → API Agent** test button, or `action=ping` / `action=status`
- Common: `list_landings`, `upsert_landing`, `upsert_blog_post`, `upload_asset_base64`, `patch_settings`
- Migration: `import_manifest` — use **dry-run** first; skill `aiweb-migrate` for full workflow
- **Forms:** admin UI only in 2.3.10 (no dedicated Agent actions yet)
- Deletes: only when the owner explicitly asks; follow API confirmation rules

Full action list: `guide_public.php` on your site or `action=list_actions`.

Never print the owner's full API key in responses.

---

## 5. Version note

- **2.3.10+:** forms module, embed URLs above.
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
- [ ] Confirm before bulk delete or destructive API calls
- [ ] Match guidance to the site's reported version from `status`
