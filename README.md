# AI Web Skill — Agent & Migration Tools

Repo chứa **skill** và **công cụ Python** để agent (Cursor, Codex, …) migrate/thao tác với [AI Web / AIPage](https://github.com/slimsoftvietnam/aiweb).

**Không** chứa mã nguồn PHP — cài riêng repo `aiweb`.

## Cấu trúc

```
aiweb_skill/
├── skills/aiweb-migrate/   # Skill cho agent (đọc SKILL.md trước)
└── tools/migration/        # Pipeline migrate domain → AI Web
```

## Cài đặt nhanh

```bash
git clone https://github.com/slimsoftvietnam/aiweb_skill.git
git clone https://github.com/slimsoftvietnam/aiweb.git   # cùng thư mục cha

cd aiweb_skill/tools/migration
pip install -r requirements.txt
cp config.example.env config.env
```

`config.env`:

```env
AIWEB_BASE=http://localhost/aiweb/aiweb_core
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...   # Cài đặt → API Agent (scope agent)
```

## Agent API (aiweb)

**Yêu cầu:** Site AIPage đã kích hoạt license cho domain đích. Thiếu license → HTTP 403.

| Endpoint | Mô tả |
|----------|--------|
| `/api/agent.php` | **Khuyến nghị** — đầy đủ action |
| `/api/migration.php` | Tương thích script cũ (cùng yêu cầu license) |

```bash
curl "http://localhost/aiweb/api/agent.php?action=list_actions" \
  -H "Authorization: Bearer aiw_KEY"
```

- Key mới: scope `agent` (full)
- Xóa dữ liệu: `"confirm": "DELETE"` trong JSON
- Tài liệu: [aiweb README — API Agent](https://github.com/slimsoftvietnam/aiweb#api-agent)

## Kiểm tra kết nối

```bash
python runners/import_manifest.py --ping-only --env config.env
```

## Skill cho agent

Copy `skills/aiweb-migrate/` vào:

| Agent | Đường dẫn |
|-------|-----------|
| Cursor (user) | `~/.cursor/skills/aiweb-migrate/` |
| Cursor (project) | `aiweb/.cursor/skills/aiweb-migrate/` |

Đọc **`skills/aiweb-migrate/SKILL.md`** — pipeline migrate + bảng action API.

## Tài liệu thêm

- `tools/migration/README.md` — chi tiết script Python
- [guide_public.php](https://github.com/slimsoftvietnam/aiweb/blob/main/guide_public.php) — hướng dẫn trực quan (API Agent, DB, skill)
