# Video Blog Pipeline for AIWeb

Turn a source YouTube video into a SlimAI-style AIWeb blog post with section images cut from the video.

Default policy:

- Blog status is `published`.
- No YouTube iframe is embedded.
- Video source is credited at the end of the article.
- Images are cut from the source video, lightly edited, and uploaded to AIWeb.
- Edited images use a SlimAI branded frame by default: warm background, top logo, step title, and the real video screenshot in the center.
- Article image paths use absolute `/uploads/...` URLs to avoid broken images under `/blog/{slug}`.

## Install

```powershell
python -m pip install -r tools/video_blog/requirements.txt
```

`ffmpeg` must be available on `PATH`.

## Prepare Video Assets

```powershell
python tools/video_blog/video_to_aiweb_blog.py prepare `
  --url "https://www.youtube.com/watch?v=Z0YO9KyVhVg" `
  --output-root output/video_blogs
```

The default SlimAI logo is loaded from:

```text
https://ai.slim.vn/uploads/upload/mig_37637ef12e8e.png
```

Use `--logo-url` to override it, or `--no-brand-frame` to keep plain screenshots.

This creates:

- `metadata.json`
- `transcript.json`
- `transcript.txt`
- `video.mp4`
- `frame_plan.json`
- `frames/*.jpg`
- `edited/*.jpg`
- `slimai_article_brief.md`
- `article_meta.template.json`
- `article.template.html`

Before publishing, review `frame_plan.json`. You can adjust timestamps, captions, `heading_contains`, or add `redactions` rectangles:

```json
{
  "redactions": [
    { "x": 100, "y": 80, "w": 420, "h": 60, "label": "email" }
  ]
}
```

Coordinates are in source image pixels after extraction. Redactions are applied to edited images during publish.

Set `heading_contains` to a distinctive part of the H2/H3 where the image belongs, for example:

```json
{
  "id": "section-03",
  "timestamp": "00:08:23",
  "heading_contains": "Kết nối OpenRouter",
  "caption": "Đoạn video cấu hình OpenRouter và chuẩn bị API key.",
  "alt": "Cấu hình OpenRouter cho Hermes Agent",
  "redactions": []
}
```

If `heading_contains` is empty or no heading matches, the figure is appended near the end of the article before the source credit.

## Publish to AIWeb

Create or edit:

- `article.html`: final SlimAI-style article body
- `article_meta.json`: title, slug, SEO description, category

Then run:

```powershell
python tools/video_blog/video_to_aiweb_blog.py publish-draft `
  --workdir output/video_blogs/Z0YO9KyVhVg `
  --env tools/migration/config.env
```

`publish-draft` is kept as the command name for compatibility, but it now publishes the article immediately with `status: published`. It uploads edited frames, inserts figures after matching headings, adds a source credit section, and calls AIWeb Agent API:

- `upload_asset_base64`
- `upsert_category`
- `upsert_blog_post`
- `get_blog_post`

## Article HTML Rules

- Write original prose; do not paste long transcript passages.
- Use the SlimAI tutorial pattern:
  - short intro that says what the tool helps with and what the reader can do after the article
  - "X là gì?" or "Tổng quan" before setup steps
  - numbered "Bước 1, Bước 2..." sections for actions the reader can follow
  - short paragraphs, concrete bullets, and one practical warning where needed
  - conclusion that encourages the reader to start from one small task
- Keep the tone: expert, clear, practical, lightly inspiring, low-hype.
- Do not include a YouTube iframe.
- Do not manually add upload URLs unless necessary; the tool inserts figures from `frame_plan.json`.
- Keep the branded image frame unless the article explicitly needs raw screenshots.
