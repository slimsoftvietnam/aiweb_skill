#!/usr/bin/env python3
"""
Video source to AIWeb blog pipeline.

This tool prepares video-derived assets and publishes a SlimAI-style article
to AIWeb. The default post status is published.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


DEFAULT_BASE = "http://localhost/aiweb"
DEFAULT_FRAME_COUNT = 8
DEFAULT_CATEGORY_NAME = "AI Agent"
DEFAULT_CATEGORY_SLUG = "ai-agent"
DEFAULT_LOGO_URL = ""
BRAND_FRAME_SIZE = (1200, 750)


class PipelineError(RuntimeError):
    pass


@dataclass
class ApiConfig:
    base_url: str
    api_key: str


def log(message: str) -> None:
    print(message, flush=True)


def read_env_file(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_api_config(env_path: Path | None) -> ApiConfig:
    env = read_env_file(env_path)
    base = (
        os.environ.get("AIWEB_BASE")
        or env.get("AIWEB_BASE")
        or DEFAULT_BASE
    ).rstrip("/")
    key = os.environ.get("MIGRATION_API_KEY") or env.get("MIGRATION_API_KEY") or ""
    if not key:
        raise PipelineError("Missing MIGRATION_API_KEY. Pass --env or set MIGRATION_API_KEY.")
    return ApiConfig(base_url=base, api_key=key)


def api_post(config: ApiConfig, payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    endpoint = f"{config.base_url}/api/agent.php"
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json; charset=utf-8",
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise PipelineError(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def require_executable(name: str) -> None:
    if not shutil.which(name):
        raise PipelineError(f"Required executable not found on PATH: {name}")


def import_yt_dlp():
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise PipelineError("Missing dependency yt-dlp. Run: python -m pip install -r tools/video_blog/requirements.txt") from exc
    return yt_dlp


def video_id_from_info(info: dict[str, Any], url: str) -> str:
    if info.get("id"):
        return str(info["id"])
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    if match:
        return match.group(1)
    return re.sub(r"[^A-Za-z0-9_-]+", "-", url).strip("-")[:60]


def fetch_metadata(url: str) -> dict[str, Any]:
    yt_dlp = import_yt_dlp()
    opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise PipelineError("Could not read video metadata.")
    return info


def fetch_transcript(video_id: str) -> list[dict[str, Any]]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    except ImportError as exc:
        raise PipelineError("Missing dependency youtube-transcript-api.") from exc

    api = YouTubeTranscriptApi()
    transcripts = api.list(video_id)
    preferred = ["vi", "en"]
    try:
        transcript = transcripts.find_transcript(preferred)
    except Exception:
        available = list(transcripts)
        if not available:
            raise
        transcript = available[0]

    items = transcript.fetch()
    return [
        {
            "start": float(item.start),
            "duration": float(item.duration),
            "text": str(item.text).strip(),
        }
        for item in items
        if str(item.text).strip()
    ]


def download_video(url: str, out_path: Path) -> None:
    yt_dlp = import_yt_dlp()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "merge_output_format": "mp4",
        "outtmpl": str(out_path.with_suffix(".%(ext)s")),
        "noplaylist": True,
        "quiet": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    merged = out_path.with_suffix(".mp4")
    if merged != out_path and merged.exists():
        merged.replace(out_path)
    if not out_path.exists():
        candidates = sorted(out_path.parent.glob(out_path.stem + ".*"))
        if not candidates:
            raise PipelineError("Video download completed but no output file was found.")
        candidates[0].replace(out_path)


def seconds_to_hhmmss(seconds: float) -> str:
    seconds_i = max(0, int(seconds))
    h = seconds_i // 3600
    m = (seconds_i % 3600) // 60
    s = seconds_i % 60
    return f"{h:02}:{m:02}:{s:02}"


def slugify(text: str) -> str:
    value = text.lower()
    replacements = {
        "đ": "d",
        "à": "a", "á": "a", "ả": "a", "ã": "a", "ạ": "a",
        "ă": "a", "ằ": "a", "ắ": "a", "ẳ": "a", "ẵ": "a", "ặ": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ẩ": "a", "ẫ": "a", "ậ": "a",
        "è": "e", "é": "e", "ẻ": "e", "ẽ": "e", "ẹ": "e",
        "ê": "e", "ề": "e", "ế": "e", "ể": "e", "ễ": "e", "ệ": "e",
        "ì": "i", "í": "i", "ỉ": "i", "ĩ": "i", "ị": "i",
        "ò": "o", "ó": "o", "ỏ": "o", "õ": "o", "ọ": "o",
        "ô": "o", "ồ": "o", "ố": "o", "ổ": "o", "ỗ": "o", "ộ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ở": "o", "ỡ": "o", "ợ": "o",
        "ù": "u", "ú": "u", "ủ": "u", "ũ": "u", "ụ": "u",
        "ư": "u", "ừ": "u", "ứ": "u", "ử": "u", "ữ": "u", "ự": "u",
        "ỳ": "y", "ý": "y", "ỷ": "y", "ỹ": "y", "ỵ": "y",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "video-blog"


def build_frame_plan(transcript: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not transcript:
        return []
    start = transcript[0]["start"]
    end = max(item["start"] + item["duration"] for item in transcript)
    safe_start = min(end, start + 30)
    usable = max(1.0, end - safe_start)
    count = max(1, min(count, 12))
    plan = []
    for i in range(count):
        target = safe_start + usable * ((i + 0.5) / count)
        nearest = min(transcript, key=lambda item: abs(item["start"] - target))
        text = nearest["text"].replace("\n", " ")
        short = text[:90].rstrip()
        plan.append(
            {
                "id": f"section-{i + 1:02d}",
                "timestamp": seconds_to_hhmmss(nearest["start"]),
                "heading_contains": "",
                "caption": f"Ảnh cắt từ video tại {seconds_to_hhmmss(nearest['start'])}, minh họa phần: {short}.",
                "alt": f"Ảnh minh họa từ video cho phần {i + 1}",
                "redactions": [],
            }
        )
    return plan


def run_ffmpeg_extract(video_path: Path, timestamp: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        timestamp,
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        "-vf",
        "scale=1280:-1",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        raise PipelineError(f"ffmpeg failed for {timestamp}: {result.stderr[-1000:]}")


def crop_to_aspect(img: Image.Image, aspect: float = 16 / 9) -> Image.Image:
    width, height = img.size
    current = width / height
    if abs(current - aspect) < 0.02:
        return img
    if current > aspect:
        new_width = int(height * aspect)
        x0 = (width - new_width) // 2
        return img.crop((x0, 0, x0 + new_width, height))
    new_height = int(width / aspect)
    y0 = (height - new_height) // 2
    return img.crop((0, y0, width, y0 + new_height))


def load_font(size: int, bold: bool = False) -> Any:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            if candidate and Path(candidate).exists():
                from PIL import ImageFont

                return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    from PIL import ImageFont

    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: Any) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def fit_inside(img: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    out = img.copy()
    out.thumbnail(max_size, Image.Resampling.LANCZOS)
    return out


def draw_dotted_corner(draw: ImageDraw.ImageDraw, x0: int, y0: int, cols: int, rows: int, color: tuple[int, int, int, int]) -> None:
    for y in range(rows):
        for x in range(cols):
            radius = max(2, 8 - int((x + y) * 0.35))
            cx = x0 + x * 18
            cy = y0 + y * 18
            draw.ellipse((cx, cy, cx + radius, cy + radius), fill=color)


def draw_decorations(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    draw.ellipse((width - 125, -65, width + 80, 140), fill=(255, 166, 82, 95))
    draw.ellipse((-70, height - 120, 90, height + 40), fill=(255, 166, 82, 70))
    draw_dotted_corner(draw, 0, 0, 13, 9, (246, 154, 62, 95))
    draw_dotted_corner(draw, width - 160, height - 170, 11, 9, (246, 154, 62, 70))
    for box in [(78, 178, 104, 204), (1080, 343, 1106, 369)]:
        draw.ellipse(box, outline=(255, 255, 255, 150), width=2)
    draw.rectangle((55, 405, 76, 426), outline=(255, 255, 255, 125), width=2)


def download_logo(workdir: Path, logo_url: str = DEFAULT_LOGO_URL) -> Path:
    assets_dir = workdir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    logo_path = assets_dir / "aiweb-logo.png"
    if logo_path.exists() and logo_path.stat().st_size > 0:
        return logo_path
    if not logo_url:
        img = Image.new("RGBA", (320, 96), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((4, 8, 316, 88), radius=22, fill=(255, 255, 255, 230))
        draw.text((34, 30), "AIWeb", fill=(193, 95, 60, 255))
        img.save(logo_path)
        return logo_path
    response = requests.get(logo_url, timeout=30)
    response.raise_for_status()
    logo_path.write_bytes(response.content)
    return logo_path


def step_number_from_id(frame_id: str) -> str:
    match = re.search(r"(\d+)$", frame_id)
    if not match:
        return ""
    return str(int(match.group(1)))


def clean_heading_title(title: str, max_chars: int = 42) -> str:
    title = re.sub(r"^Bước\s+\d+\s*:\s*", "", title, flags=re.IGNORECASE).strip()
    if len(title) <= max_chars:
        return title
    return title[: max_chars - 1].rstrip() + "…"


def compose_branded_frame(screenshot: Image.Image, logo_path: Path, title: str, step_number: str) -> Image.Image:
    width, height = BRAND_FRAME_SIZE
    canvas = Image.new("RGB", (width, height), (255, 235, 212))
    draw = ImageDraw.Draw(canvas, "RGBA")

    for y in range(height):
        tint = int(18 * (y / height))
        draw.line((0, y, width, y), fill=(255, 235 - tint, 212 - tint, 255))
    draw_decorations(draw, width, height)

    logo = Image.open(logo_path).convert("RGBA")
    logo = fit_inside(logo, (190, 58))
    badge_w = logo.width + 58
    badge_h = 58
    badge_x = (width - badge_w) // 2
    badge_y = 10
    draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + badge_h), radius=16, fill=(255, 255, 255, 235))
    canvas.paste(logo, (badge_x + 29, badge_y + (badge_h - logo.height) // 2), logo)

    title_font = load_font(35, bold=True)
    num_font = load_font(52, bold=True)
    title = clean_heading_title(title)
    title_w, title_h = text_size(draw, title, title_font)
    pill_h = 66
    pill_w = min(690, max(390, title_w + 104))
    pill_x = (width - pill_w) // 2 + 70
    pill_y = 82
    circle_size = 80
    circle_x = pill_x - 62
    circle_y = pill_y - 8
    draw.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + pill_h), radius=32, fill=(255, 121, 22, 255))
    draw.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + pill_h // 2), radius=32, fill=(255, 162, 19, 145))
    draw.ellipse((circle_x, circle_y, circle_x + circle_size, circle_y + circle_size), fill=(255, 255, 255, 255), outline=(255, 126, 25, 255), width=5)
    if step_number:
        n_w, n_h = text_size(draw, step_number, num_font)
        draw.text((circle_x + (circle_size - n_w) / 2, circle_y + (circle_size - n_h) / 2 - 4), step_number, font=num_font, fill=(255, 118, 22, 255))
    draw.text((pill_x + 70, pill_y + (pill_h - title_h) / 2 - 3), title, font=title_font, fill=(255, 255, 255, 255))
    for x1, y1, x2, y2 in [(930, 88, 947, 61), (958, 110, 987, 118), (937, 139, 956, 164)]:
        draw.line((x1, y1, x2, y2), fill=(255, 102, 23, 255), width=6)

    browser_x, browser_y = 138, 174
    browser_w, browser_h = 924, 548
    chrome_h = 40
    draw.rounded_rectangle((browser_x - 4, browser_y - 4, browser_x + browser_w + 4, browser_y + browser_h + 4), radius=15, fill=(255, 255, 255, 170))
    draw.rounded_rectangle((browser_x, browser_y, browser_x + browser_w, browser_y + browser_h), radius=14, fill=(255, 255, 255, 255))
    draw.rectangle((browser_x, browser_y + chrome_h, browser_x + browser_w, browser_y + browser_h), fill=(245, 245, 245, 255))
    for i, color in enumerate([(255, 91, 83), (255, 190, 68), (42, 201, 83)]):
        cx = browser_x + 28 + i * 25
        cy = browser_y + 20
        draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(*color, 255))

    shot = fit_inside(screenshot.convert("RGB"), (browser_w, browser_h - chrome_h))
    shot_x = browser_x + (browser_w - shot.width) // 2
    shot_y = browser_y + chrome_h + (browser_h - chrome_h - shot.height) // 2
    canvas.paste(shot, (shot_x, shot_y))
    return canvas


def edit_frame(
    raw_path: Path,
    edited_path: Path,
    redactions: list[dict[str, Any]],
    frame_title: str = "",
    step_number: str = "",
    logo_path: Path | None = None,
    brand_frame: bool = True,
) -> None:
    edited_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(raw_path).convert("RGB")
    img = crop_to_aspect(img)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Color(img).enhance(1.03)
    img = ImageEnhance.Sharpness(img).enhance(1.12)

    draw = ImageDraw.Draw(img)
    for redaction in redactions:
        x = int(redaction.get("x", 0))
        y = int(redaction.get("y", 0))
        w = int(redaction.get("w", 0))
        h = int(redaction.get("h", 0))
        if w <= 0 or h <= 0:
            continue
        box = (x, y, x + w, y + h)
        region = img.crop(box).filter(ImageFilter.GaussianBlur(radius=12))
        img.paste(region, box)
        draw.rectangle(box, outline=(20, 20, 20), width=2)

    if brand_frame and logo_path:
        img = compose_branded_frame(img, logo_path, frame_title or "Ảnh minh họa", step_number)

    img.save(edited_path, quality=88, optimize=True)


def write_prepare_artifacts(workdir: Path, url: str, metadata: dict[str, Any], transcript: list[dict[str, Any]], frame_plan: list[dict[str, Any]]) -> None:
    title = str(metadata.get("title") or "Video blog")
    author = str(metadata.get("uploader") or metadata.get("channel") or "")
    source_url = str(metadata.get("webpage_url") or url)
    transcript_text = "\n".join(item["text"] for item in transcript)

    (workdir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (workdir / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    (workdir / "transcript.txt").write_text(transcript_text, encoding="utf-8")
    (workdir / "frame_plan.json").write_text(json.dumps(frame_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    slug = slugify(title)
    meta_template = {
        "title": title,
        "slug": slug,
        "seo_description": f"Tóm tắt và biên tập theo giọng SlimAI từ video {title}.",
        "category_name": DEFAULT_CATEGORY_NAME,
        "category_slug": DEFAULT_CATEGORY_SLUG,
        "source_url": source_url,
        "source_title": title,
        "source_author": author,
        "status": "published",
    }
    (workdir / "article_meta.template.json").write_text(json.dumps(meta_template, ensure_ascii=False, indent=2), encoding="utf-8")

    brief = f"""# SlimAI Video Blog Brief

Source video: {title}
Channel: {author}
URL: {source_url}

## Writing Rules
- Write in SlimAI voice: expert, clear, practical, lightly inspiring, low-hype.
- Follow the SlimAI tutorial pattern:
  1. Short intro: what this tool/process helps with and what the reader can do after reading.
  2. A simple "what is it?" section before the setup.
  3. Numbered step sections ("Bước 1...", "Bước 2...") that are just detailed enough to follow.
  4. Images immediately after the relevant step heading.
  5. One or two practical warning notes in blockquotes.
  6. A short conclusion that nudges the reader to try one small next step.
- Explain what each major step means, how to do it, and what to watch out for.
- Do not copy long transcript passages.
- Do not embed the YouTube iframe.
- End with a source credit link.
- Publish the post on AIWeb after local article/frame review is complete.

## Image Rules
- Use frames from `edited/`.
- Place each figure immediately after the matching H2/H3.
- Use absolute `/uploads/...` paths after upload.
- Redact secrets or private identifiers before upload.

## Transcript

{transcript_text[:12000]}
"""
    (workdir / "slimai_article_brief.md").write_text(brief, encoding="utf-8")

    article_template = f"""<p><em>{html_escape(title)}</em>{' của ' + html_escape(author) if author else ''} là một video hướng dẫn thực tế dành cho người muốn bắt đầu với AI Agent. Bài viết này biên tập lại nội dung chính theo giọng SlimAI: dễ hiểu, đủ chi tiết để làm theo và tập trung vào bước tiếp theo bạn có thể thử ngay.</p>

<h2>{{Tên công cụ/quy trình}} là gì?</h2>
<p>Giải thích ngắn gọn công cụ/quy trình là gì, khác gì so với cách làm thông thường và phù hợp với ai.</p>

<h2>Bước 1: Chuẩn bị trước khi bắt đầu</h2>
<p>Nêu điều kiện cần có, tài khoản/công cụ cần chuẩn bị và lựa chọn an toàn cho người mới.</p>

<h2>Bước 2: Thiết lập phần quan trọng nhất</h2>
<p>Viết lại các thao tác chính theo trình tự dễ làm theo. Chỉ giữ chi tiết đủ để người đọc không bị lạc.</p>

<h2>Bước 3: Kiểm tra kết quả đầu tiên</h2>
<p>Hướng dẫn cách biết setup đã chạy đúng và lỗi phổ biến cần kiểm tra.</p>

<blockquote><p>Nếu mới bắt đầu, bạn nên thử với một tác vụ nhỏ trước. Cách này giúp kiểm soát chi phí, quyền truy cập và chất lượng đầu ra tốt hơn.</p></blockquote>

<h2>Cách dùng hiệu quả hơn</h2>
<p>Tóm tắt các mẹo sau khi đã setup xong: chia nhỏ việc, kiểm tra kết quả, lưu quy trình, theo dõi chi phí hoặc quyền truy cập.</p>

<h2>Kết luận</h2>
<p>Đưa ra khuyến nghị thực tế theo giọng SlimAI. Kết thúc bằng một lời khuyến khích nhẹ: bắt đầu từ một use case nhỏ, kiểm tra kết quả rồi mở rộng.</p>
"""
    (workdir / "article.template.html").write_text(article_template, encoding="utf-8")


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def command_prepare(args: argparse.Namespace) -> None:
    require_executable("ffmpeg")
    url = args.url
    metadata = fetch_metadata(url)
    video_id = video_id_from_info(metadata, url)
    workdir = Path(args.output_root) / video_id
    workdir.mkdir(parents=True, exist_ok=True)

    log(f"Preparing video {video_id}: {metadata.get('title', '')}")
    transcript = fetch_transcript(video_id)
    frame_plan = build_frame_plan(transcript, args.frame_count)

    video_path = workdir / "video.mp4"
    if args.skip_download and video_path.exists():
        log(f"Using existing video: {video_path}")
    else:
        download_video(url, video_path)

    logo_path = None if args.no_brand_frame else download_logo(workdir, args.logo_url)
    frames_dir = workdir / "frames"
    edited_dir = workdir / "edited"
    for item in frame_plan:
        raw = frames_dir / f"{item['id']}.jpg"
        edited = edited_dir / f"{item['id']}.jpg"
        run_ffmpeg_extract(video_path, item["timestamp"], raw)
        edit_frame(
            raw,
            edited,
            item.get("redactions", []),
            frame_title=item.get("heading_contains") or item.get("caption") or "",
            step_number=step_number_from_id(item["id"]),
            logo_path=logo_path,
            brand_frame=not args.no_brand_frame,
        )

    write_prepare_artifacts(workdir, url, metadata, transcript, frame_plan)
    log(f"Prepared artifacts in {workdir}")
    log("Review frame_plan.json, then copy article_meta.template.json/article.template.html to article_meta.json/article.html before publishing.")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def upload_image(config: ApiConfig, path: Path, source_url: str) -> dict[str, Any]:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return api_post(
        config,
        {
            "action": "upload_asset_base64",
            "source_domain": "video-blog",
            "source_url": source_url,
            "filename": path.name,
            "mime_type": mime,
            "data": data,
        },
    )


def figure_html(src: str, alt: str, caption: str) -> str:
    return f'<figure><img src="{src}" alt="{html_escape(alt)}" loading="lazy"><figcaption>{html_escape(caption)}</figcaption></figure>'


def insert_after_heading(content: str, heading_contains: str, block: str, fallback_before_source: bool = True) -> str:
    if heading_contains:
        pattern = re.compile(r"(<h[23][^>]*>[^<]*" + re.escape(heading_contains) + r"[^<]*</h[23]>)", re.IGNORECASE)
        match = pattern.search(content)
        if match:
            return content[: match.end()] + "\n" + block + content[match.end() :]
    if fallback_before_source:
        source_match = re.search(r"<h2[^>]*>Nguồn video</h2>", content, re.IGNORECASE)
        if source_match:
            return content[: source_match.start()] + block + "\n" + content[source_match.start() :]
    return content + "\n" + block


def ensure_source_credit(content: str, meta: dict[str, Any]) -> str:
    if "youtube.com/embed/" in content or "<iframe" in content.lower():
        raise PipelineError("Article contains an iframe. Remove video embeds before publishing.")
    source_url = meta.get("source_url", "")
    source_title = meta.get("source_title") or meta.get("title") or "video gốc"
    source_author = meta.get("source_author", "")
    if source_url and source_url in content:
        return content
    if not source_url:
        return content
    author = f" - {html_escape(str(source_author))}" if source_author else ""
    credit = (
        "\n<h2>Nguồn video</h2>\n"
        f'<p>Bài viết được biên tập từ video gốc: <a href="{html_escape(str(source_url))}" target="_blank" rel="noopener">{html_escape(str(source_title))}</a>{author}.</p>\n'
    )
    return content.rstrip() + credit


def command_publish_draft(args: argparse.Namespace) -> None:
    workdir = Path(args.workdir)
    config = load_api_config(Path(args.env) if args.env else None)
    meta_path = workdir / "article_meta.json"
    article_path = workdir / "article.html"
    if not meta_path.exists():
        raise PipelineError(f"Missing {meta_path}. Copy/edit article_meta.template.json first.")
    if not article_path.exists():
        raise PipelineError(f"Missing {article_path}. Copy/edit article.template.html first.")

    meta = load_json(meta_path)
    content = article_path.read_text(encoding="utf-8")
    frame_plan = json.loads((workdir / "frame_plan.json").read_text(encoding="utf-8"))

    logo_path = None if args.no_brand_frame else download_logo(workdir, args.logo_url)
    edited_dir = workdir / "edited"
    uploads: dict[str, dict[str, Any]] = {}
    for item in frame_plan:
        image_path = edited_dir / f"{item['id']}.jpg"
        raw_path = workdir / "frames" / f"{item['id']}.jpg"
        if not raw_path.exists():
            raise PipelineError(f"Missing frame image: {raw_path}")
        edit_frame(
            raw_path,
            image_path,
            item.get("redactions", []),
            frame_title=item.get("heading_contains") or item.get("caption") or "",
            step_number=step_number_from_id(item["id"]),
            logo_path=logo_path,
            brand_frame=not args.no_brand_frame,
        )
        upload = upload_image(config, image_path, f"{meta.get('source_url', 'video')}/frame/{item['id']}.jpg")
        absolute_src = "/uploads/" + str(upload["local_path"]).lstrip("/")
        uploads[item["id"]] = {**upload, "src": absolute_src}
        block = figure_html(
            absolute_src,
            item.get("alt") or item.get("caption") or f"Ảnh minh họa {item['id']}",
            item.get("caption") or "",
        )
        content = insert_after_heading(content, item.get("heading_contains", ""), block)

    content = ensure_source_credit(content, meta)

    category_name = meta.get("category_name") or DEFAULT_CATEGORY_NAME
    category_slug = meta.get("category_slug") or slugify(str(category_name))
    api_post(
        config,
        {
            "action": "upsert_category",
            "source_domain": "video-blog",
            "source_key": category_slug,
            "name": category_name,
            "slug": category_slug,
            "description": meta.get("category_description", ""),
        },
    )

    featured = next(iter(uploads.values()))["local_path"] if uploads else None
    payload = {
        "action": "upsert_blog_post",
        "source_domain": "video-blog",
        "source_key": meta.get("source_key") or meta.get("source_url") or meta["slug"],
        "slug": meta["slug"],
        "title": meta["title"],
        "content": content,
        "seo_description": meta.get("seo_description", ""),
        "language": meta.get("language", "vi"),
        "featured_image": featured,
        "category_slug": category_slug,
        "status": "published",
        "is_featured": bool(meta.get("is_featured", False)),
        "published_at": meta.get("published_at"),
        "rewrite_assets": False,
    }
    post = api_post(config, payload)
    verify = api_post(
        config,
        {
            "action": "get_blog_post",
            "slug": meta["slug"],
            "include_content": True,
        },
    )
    verify_post = verify["post"]
    if verify_post.get("status") != "published":
        raise PipelineError(f"Expected published status, got {verify_post.get('status')}")
    if "youtube.com/embed/" in str(verify_post.get("content", "")):
        raise PipelineError("Verification failed: iframe still present.")
    if 'src="uploads/' in str(verify_post.get("content", "")):
        raise PipelineError("Verification failed: relative upload src found.")

    manifest = {
        "post": post,
        "verify": {
            "id": verify_post.get("id"),
            "slug": verify_post.get("slug"),
            "status": verify_post.get("status"),
            "title": verify_post.get("title"),
            "figure_count": str(verify_post.get("content", "")).count("<figure>"),
            "has_source_credit": str(meta.get("source_url", "")) in str(verify_post.get("content", "")),
        },
        "uploads": uploads,
    }
    (workdir / "upload_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(json.dumps(manifest, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare and publish SlimAI-style AIWeb blog posts from video sources.")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Fetch metadata/transcript/video and create frame/article artifacts.")
    prepare.add_argument("--url", required=True, help="YouTube video URL.")
    prepare.add_argument("--output-root", default="output/video_blogs", help="Output root directory.")
    prepare.add_argument("--frame-count", type=int, default=DEFAULT_FRAME_COUNT, help="Number of section frames to suggest.")
    prepare.add_argument("--skip-download", action="store_true", help="Reuse existing video.mp4 in workdir if present.")
    prepare.add_argument("--logo-url", default=DEFAULT_LOGO_URL, help="Logo URL used in branded image frames.")
    prepare.add_argument("--no-brand-frame", action="store_true", help="Export plain edited screenshots without the SlimAI frame.")
    prepare.set_defaults(func=command_prepare)

    publish = sub.add_parser("publish-draft", help="Upload edited frames and create/update a published AIWeb blog post.")
    publish.add_argument("--workdir", required=True, help="Prepared video blog workdir.")
    publish.add_argument("--env", default="tools/migration/config.env", help="AIWeb env file with AIWEB_BASE and MIGRATION_API_KEY.")
    publish.add_argument("--logo-url", default=DEFAULT_LOGO_URL, help="Logo URL used in branded image frames.")
    publish.add_argument("--no-brand-frame", action="store_true", help="Upload plain edited screenshots without the SlimAI frame.")
    publish.set_defaults(func=command_publish_draft)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
