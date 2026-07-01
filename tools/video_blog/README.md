# Video Blog Pipeline for AIWeb

Turn a source YouTube video into an AIWeb blog post with section images cut from
the video.

Default policy:

- Blog status is `published` when `publish-draft` runs.
- No YouTube iframe is embedded.
- Video source is credited at the end of the article.
- Images are cut from the source video, lightly edited, and uploaded to AIWeb.
- Edited images use a neutral AIWeb branded frame by default.
- Article image paths use absolute `/uploads/...` URLs to avoid broken images
  under `/blog/{slug}`.

## Install

```powershell
python -m pip install -r tools/video_blog/requirements.txt
```

`ffmpeg` must be available on `PATH`.

## Prepare Video Assets

```powershell
python tools/video_blog/video_to_aiweb_blog.py prepare `
  --url "https://www.youtube.com/watch?v=VIDEO_ID" `
  --output-root output/video_blogs
```

Use `--logo-url` to provide a target-site logo, or `--no-brand-frame` to keep
plain screenshots.

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

Before publishing, review `frame_plan.json`. Adjust timestamps, captions,
`heading_contains`, or add redaction rectangles.

## Publish To AIWeb

Create or edit:

- `article.html`
- `article_meta.json`

Then run:

```powershell
python tools/video_blog/video_to_aiweb_blog.py publish-draft `
  --workdir output/video_blogs/VIDEO_ID `
  --env tools/migration/config.env
```

`publish-draft` is kept as the command name for compatibility, but it publishes
the article immediately with `status: published`.
