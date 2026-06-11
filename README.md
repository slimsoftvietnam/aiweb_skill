# AI Web Skill — Agent & Migration Tools

Repo chứa **skill** và **công cụ Python** để agent (Cursor, Codex, …) migrate/thao tác với [AI Web / AIPage](https://github.com/slimsoftvietnam/aiweb).

**Không** chứa mã nguồn PHP của AIPage — cài riêng repo `aiweb`.

## Cấu trúc

```
aiweb_skill/
├── skills/aiweb-migrate/   # Skill cho agent (Cursor/Codex)
└── tools/migration/        # Pipeline migrate domain → AI Web
```

## Cài đặt

```bash
git clone https://github.com/slimsoftvietnam/aiweb_skill.git
git clone https://github.com/slimsoftvietnam/aiweb.git   # cùng thư mục cha (khuyến nghị)

cd aiweb_skill/tools/migration
pip install -r requirements.txt
cp config.example.env config.env
```

Chỉnh `config.env`:

```env
AIWEB_BASE=http://localhost/aiweb/aiweb_core
AIWEB_ROOT=D:/path/to/aiweb
MIGRATION_API_KEY=aiw_...   # Tạo trong AIPage → Cài đặt → API Agent
```

## Kiểm tra kết nối

```bash
python runners/import_manifest.py --ping-only --env config.env
```

## Skill cho agent

Copy hoặc symlink `skills/aiweb-migrate` vào:

- Cursor: `.cursor/skills/aiweb-migrate/`
- Codex: theo cấu hình skill của môi trường bạn dùng

Đọc `skills/aiweb-migrate/SKILL.md` để biết pipeline đầy đủ.

## Tài liệu chi tiết

Xem `tools/migration/README.md`.
