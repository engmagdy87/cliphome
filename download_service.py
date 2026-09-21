"""Talk to yt-dlp. This is a service: the downloader is an external tool, not our data."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import yt_dlp
from yt_dlp.utils import sanitize_filename

from youtube_urls import is_playlist_url

EventFn = Callable[[dict[str, Any]], None]
CancelFn = Callable[[], bool]

VIDEO_FORMATS = {
    "best": "bv*+ba/b",
    "1080": "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b",
    "720": "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b",
    "480": "bv*[height<=480]+ba/b[height<=480]/b",
    "360": "bv*[height<=360]+ba/b[height<=360]/b",
}

QUALITY_CANVAS = {
    "best": (1920, 1080),
    "1080": (1920, 1080),
    "720": (1280, 720),
    "480": (854, 480),
    "360": (640, 360),
}

ALLOWED_QUALITIES = frozenset(VIDEO_FORMATS)
ALLOWED_MEDIA = frozenset({"video", "audio"})
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class DownloadCancelled(Exception):
    pass


def plain(message: str) -> str:
    return ANSI_RE.sub("", str(message)).strip()


def js_runtimes() -> dict[str, dict[str, str]]:
    runtimes: dict[str, dict[str, str]] = {}
    for name in ("node", "deno"):
        path = shutil.which(name)
        if path:
            runtimes[name] = {"path": path}
    return runtimes


class YtLogger:
    def __init__(self, on_event: EventFn) -> None:
        self.on_event = on_event

    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            return
        self.info(msg)

    def info(self, msg: str) -> None:
        text = plain(msg)
        if text:
            self.on_event({"type": "log", "message": text})

    def warning(self, msg: str) -> None:
        text = plain(msg)
        if text:
            self.on_event({"type": "log", "message": text})

    def error(self, msg: str) -> None:
        text = plain(msg)
        if text:
            self.on_event({"type": "log", "message": text})


def _percent(data: dict[str, Any]) -> float | None:
    total = data.get("total_bytes") or data.get("total_bytes_estimate")
    downloaded = data.get("downloaded_bytes")
    if total and downloaded:
        return round(min(downloaded / total * 100, 100), 1)
    return None


def _downloaded_path(ydl: yt_dlp.YoutubeDL, info: dict[str, Any] | None) -> Path | None:
    if not info:
        return None
    downloads = info.get("requested_downloads") or []
    for item in reversed(downloads):
        filepath = item.get("filepath")
        if filepath and Path(filepath).exists():
            return Path(filepath)
    name = info.get("filename") or ydl.prepare_filename(info)
    path = Path(name)
    if path.exists():
        return path
    for ext in (".mp4", ".mkv", ".webm", ".mov"):
        candidate = path.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


def _video_size(path: Path) -> tuple[int, int] | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    streams = json.loads(result.stdout).get("streams") or []
    if not streams:
        return None
    width = streams[0].get("width")
    height = streams[0].get("height")
    if not width or not height:
        return None
    return int(width), int(height)


def _unique_dest(directory: Path, name: str) -> Path:
    dest = directory / name
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    n = 1
    while True:
        candidate = directory / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _safe_folder_name(title: str) -> str:
    name = sanitize_filename(title, restricted=False).strip() or "Playlist"
    name = name.replace("/", "-").replace("\\", "-").replace(":", " -")
    return name[:120]


def _playlist_dest(directory: Path, info: dict[str, Any]) -> Path:
    title = info.get("title") or info.get("playlist_title") or info.get("id") or "Playlist"
    folder = directory / _safe_folder_name(str(title))
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _move_finished(path: Path, directory: Path) -> Path:
    name = path.name
    if ".scaling." in name:
        name = f"{path.stem.replace('.scaling', '')}{path.suffix}"
    dest = _unique_dest(directory, name)
    shutil.move(str(path), str(dest))
    return dest


def upscale_if_needed(
    path: Path,
    quality: str,
    on_event: EventFn,
    should_cancel: CancelFn,
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return path
    canvas = QUALITY_CANVAS.get(quality)
    if not canvas:
        return path
    size = _video_size(path)
    if not size:
        return path
    width, height = size
    target_w, target_h = canvas
    if height >= target_h * 0.9 and width >= target_w * 0.5:
        return path
    if should_cancel():
        raise DownloadCancelled("Download cancelled.")
    on_event(
        {
            "type": "log",
            "message": (
                f"YouTube gave {width}x{height}. Scaling to {target_w}x{target_h} "
                "so it fills the player the way the website does."
            ),
        }
    )
    fd, tmp_name = tempfile.mkstemp(prefix=".ytdl-", suffix=".mp4", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    out = path.with_suffix(".mp4")
    scale = (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
    )
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(path),
            "-vf",
            scale,
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(tmp),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        tmp.unlink(missing_ok=True)
        on_event({"type": "log", "message": f"Could not scale video: {plain(result.stderr[-400:])}"})
        return path
    tmp.replace(out)
    if path.resolve() != out.resolve():
        path.unlink(missing_ok=True)
    return out


def download(
    urls: list[str],
    directory: Path,
    quality: str,
    media_type: str,
    on_event: EventFn,
    should_cancel: CancelFn,
) -> dict[str, int]:
    if quality not in ALLOWED_QUALITIES:
        raise ValueError("Unknown quality.")
    if media_type not in ALLOWED_MEDIA:
        raise ValueError("Choose video or audio.")

    runtimes = js_runtimes()
    if not runtimes:
        raise RuntimeError(
            "YouTube needs a JavaScript runtime. Install Node 22+ (or Deno) and restart."
        )

    def hook(data: dict[str, Any]) -> None:
        if should_cancel():
            raise DownloadCancelled("Download cancelled.")
        status = data.get("status")
        filename = data.get("filename") or data.get("info_dict", {}).get("title")
        if filename:
            filename = Path(str(filename)).name
        if status == "downloading":
            event: dict[str, Any] = {
                "type": "progress",
                "filename": filename,
                "speed": (data.get("_speed_str") or "").strip(),
                "eta": (data.get("_eta_str") or "").strip(),
            }
            percent = _percent(data)
            if percent is not None:
                event["percent"] = percent
            on_event(event)

    total = len(urls)
    on_event({"type": "batch", "total": total, "succeeded": 0, "failed": 0})
    on_event(
        {
            "type": "log",
            "message": f"Saving {total} item(s) as {media_type} to {directory}",
        }
    )

    failures = 0
    failed_urls: list[str] = []
    for index, url in enumerate(urls, start=1):
        if should_cancel():
            raise DownloadCancelled("Download cancelled.")
        on_event({"type": "log", "message": f"[{index}/{total}] {url}"})
        work_dir = Path(tempfile.mkdtemp(prefix="ytdl-"))
        opts: dict[str, Any] = {
            "format": VIDEO_FORMATS[quality] if media_type == "video" else "bestaudio/best",
            "outtmpl": str(work_dir / "%(title)s.%(ext)s"),
            "noplaylist": not is_playlist_url(url),
            "ignoreerrors": is_playlist_url(url),
            "progress_hooks": [hook],
            "logger": YtLogger(on_event),
            "noprogress": True,
            "no_color": True,
            "overwrites": False,
            "continuedl": True,
            "restrictfilenames": False,
            "windowsfilenames": False,
            "js_runtimes": runtimes,
        }
        if media_type == "video":
            opts["merge_output_format"] = "mp4"
        else:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        try:
            paths: list[Path] = []
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                entries = info.get("entries") if info and info.get("_type") == "playlist" else [info]
                for entry in entries or []:
                    if not entry:
                        continue
                    path = _downloaded_path(ydl, entry)
                    if path:
                        paths.append(path)
            dest_dir = directory
            if info and info.get("_type") == "playlist":
                dest_dir = _playlist_dest(directory, info)
                on_event(
                    {
                        "type": "log",
                        "message": f"Playlist folder: {dest_dir.name}",
                    }
                )
            finished: list[Path] = []
            for path in paths:
                if media_type == "video":
                    path = upscale_if_needed(path, quality, on_event, should_cancel)
                finished.append(_move_finished(path, dest_dir))
            succeeded = index - failures
            on_event(
                {
                    "type": "item_ok",
                    "index": index,
                    "total": total,
                    "succeeded": succeeded,
                    "failed": failures,
                }
            )
        except DownloadCancelled:
            raise
        except Exception as exc:
            failures += 1
            failed_urls.append(url)
            on_event(
                {
                    "type": "log",
                    "message": f"Failed [{index}/{total}] {url}: {plain(str(exc))}",
                }
            )
            on_event(
                {
                    "type": "item_fail",
                    "index": index,
                    "total": total,
                    "succeeded": index - failures,
                    "failed": failures,
                    "url": url,
                }
            )
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    succeeded = total - failures
    return {
        "succeeded": succeeded,
        "failed": failures,
        "total": total,
        "failed_urls": failed_urls,
    }
