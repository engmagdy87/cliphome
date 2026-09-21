"""Talk to yt-dlp. This is a service: the downloader is an external tool, not our data."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
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


def _run_cancellable(
    args: list[str],
    should_cancel: CancelFn,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        while proc.poll() is None:
            if should_cancel():
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                raise DownloadCancelled("Download cancelled.")
            time.sleep(0.2)
        stderr = proc.stderr.read() if proc.stderr else ""
        return subprocess.CompletedProcess(args, proc.returncode or 0, "", stderr)
    except DownloadCancelled:
        raise
    finally:
        if proc.poll() is None:
            proc.kill()


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


def _video_url_from_entry(entry: dict[str, Any] | None) -> str | None:
    if not entry:
        return None
    for key in ("webpage_url", "original_url", "url"):
        value = entry.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    vid = entry.get("id")
    if isinstance(vid, str) and vid:
        return f"https://www.youtube.com/watch?v={vid}"
    return None


def _list_playlist(
    url: str,
    runtimes: dict[str, dict[str, str]],
    on_event: EventFn,
    should_cancel: CancelFn,
) -> tuple[dict[str, Any], list[str]]:
    if should_cancel():
        raise DownloadCancelled("Download cancelled.")
    opts = {
        "extract_flat": "in_playlist",
        "skip_download": True,
        "noplaylist": False,
        "ignoreerrors": True,
        "logger": YtLogger(on_event),
        "no_color": True,
        "js_runtimes": runtimes,
        "noprogress": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("Could not read playlist.")
    videos: list[str] = []
    seen: set[str] = set()
    for entry in info.get("entries") or []:
        video_url = _video_url_from_entry(entry)
        if not video_url or video_url in seen:
            continue
        seen.add(video_url)
        videos.append(video_url)
    return info, videos


def _expand_jobs(
    urls: list[str],
    directory: Path,
    runtimes: dict[str, dict[str, str]],
    on_event: EventFn,
    should_cancel: CancelFn,
) -> tuple[list[tuple[str, Path]], list[str]]:
    jobs: list[tuple[str, Path]] = []
    listing_failed: list[str] = []
    for url in urls:
        if should_cancel():
            raise DownloadCancelled("Download cancelled.")
        if not is_playlist_url(url):
            jobs.append((url, directory))
            continue
        on_event({"type": "log", "message": f"Listing playlist {url}"})
        try:
            info, videos = _list_playlist(url, runtimes, on_event, should_cancel)
            dest = _playlist_dest(directory, info)
            on_event({"type": "log", "message": f"Playlist folder: {dest}"})
            if not videos:
                raise RuntimeError("Playlist has no videos.")
            on_event(
                {
                    "type": "log",
                    "message": f"Found {len(videos)} video(s). Each file appears in that folder when it finishes.",
                }
            )
            for video_url in videos:
                jobs.append((video_url, dest))
        except DownloadCancelled:
            raise
        except Exception as exc:
            listing_failed.append(url)
            on_event(
                {
                    "type": "log",
                    "message": f"Failed to list playlist {url}: {plain(str(exc))}",
                }
            )
    return jobs, listing_failed


def _save_one(
    url: str,
    dest_dir: Path,
    quality: str,
    media_type: str,
    runtimes: dict[str, dict[str, str]],
    on_event: EventFn,
    should_cancel: CancelFn,
    hook: Callable[[dict[str, Any]], None],
) -> Path:
    work_dir = Path(tempfile.mkdtemp(prefix="ytdl-"))
    opts: dict[str, Any] = {
        "format": VIDEO_FORMATS[quality] if media_type == "video" else "bestaudio/best",
        "outtmpl": str(work_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
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
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = _downloaded_path(ydl, info)
        if not path:
            raise RuntimeError("Download finished but the file was not found.")
        if should_cancel():
            raise DownloadCancelled("Download cancelled.")
        if media_type == "video":
            path = upscale_if_needed(path, quality, on_event, should_cancel)
        if should_cancel():
            raise DownloadCancelled("Download cancelled.")
        return _move_finished(path, dest_dir)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


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
    try:
        result = _run_cancellable(
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
            should_cancel,
        )
    except DownloadCancelled:
        tmp.unlink(missing_ok=True)
        raise
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

    jobs, listing_failed = _expand_jobs(
        urls, directory, runtimes, on_event, should_cancel
    )
    failed_urls = list(listing_failed)
    failures = len(listing_failed)
    total = len(jobs) + failures
    on_event({"type": "batch", "total": total, "succeeded": 0, "failed": failures})
    on_event(
        {
            "type": "log",
            "message": f"Saving {total} item(s) as {media_type} to {directory}",
        }
    )

    index = 0
    for url in listing_failed:
        index += 1
        on_event(
            {
                "type": "item_fail",
                "index": index,
                "total": total,
                "succeeded": 0,
                "failed": failures,
                "url": url,
            }
        )

    for url, dest_dir in jobs:
        if should_cancel():
            raise DownloadCancelled("Download cancelled.")
        index += 1
        on_event({"type": "log", "message": f"[{index}/{total}] {url}"})
        try:
            _save_one(
                url,
                dest_dir,
                quality,
                media_type,
                runtimes,
                on_event,
                should_cancel,
                hook,
            )
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

    succeeded = total - failures
    return {
        "succeeded": succeeded,
        "failed": failures,
        "total": total,
        "failed_urls": failed_urls,
    }
