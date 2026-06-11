# Migration Tools → AI Web / AIPage

Pipeline migrate nội dung từ domain cũ (vd. slimcrm.vn) vào [AIPage](https://github.com/slimsoftvietnam/aiweb).

Repo skill: [aiweb_skill](https://github.com/slimsoftvietnam/aiweb_skill).

## Cài đặt

```bash
pip install -r requirements.txt
cp config.example.env config.env
```

Chỉnh `config.env`:

- `AIWEB_BASE` — URL core (vd. `http://localhost/aiweb/aiweb_core`)
- `AIWEB_ROOT` — đường dẫn repo **aiweb** (có `aiweb_core/`)
- `MIGRATION_API_KEY` — tạo trong AIPage → Cài đặt → API Agent

## Ping API

```bash
python runners/import_manifest.py --ping-only --env config.env
```

## Ví dụ SlimCRM landing

```bash
python scrapers/slimcrm_recon.py
python scrapers/slimcrm_extract.py
python runners/import_manifest.py --env config.env --file output/slimcrm_manifest_landing.json --publish
```

## Blog

```bash
python scrapers/slimcrm_blog_scan.py
python runners/import_blog_all.py --env config.env
```

URL công khai sau migrate: `https://your-domain/{slug}`
