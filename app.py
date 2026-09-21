from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from download_service import (
    ALLOWED_MEDIA,
    ALLOWED_QUALITIES,
    DownloadCancelled,
    download,
    js_runtimes,
)
from folder_picker import pick_folder, resolve_writable_dir
from youtube_urls import validate_urls

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
HOST = "127.0.0.1"
PORT = 8765
APP_URL = f"http://{HOST}:{PORT}"

app = FastAPI(title="YouTube Downloader")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class DownloadRequest(BaseModel):
    urls: str = Field(..., min_length=1)
    directory: str = Field(..., min_length=1)
    quality: str = "1080"
    media_type: Literal["video", "audio"] = "video"
    playlist_scope: Literal["video", "playlist"] = "video"


class Job:
    def __init__(self) -> None:
        self.id = uuid.uuid4().hex
        self.history: list[dict[str, Any]] = []
        self.updated = asyncio.Event()
        self.cancelled = False
        self.finished = False

    def emit(self, event: dict[str, Any]) -> None:
        self.history.append(event)
        self.updated.set()


jobs: dict[str, Job] = {}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    runtimes = js_runtimes()
    return {
        "ok": True,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "js_runtimes": list(runtimes),
    }


@app.post("/api/folder/pick")
async def folder_pick() -> dict[str, str]:
    path = await asyncio.to_thread(pick_folder)
    if not path:
        raise HTTPException(status_code=409, detail="No folder selected.")
    try:
        directory = resolve_writable_dir(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"path": str(directory)}


@app.post("/api/downloads")
async def start_download(body: DownloadRequest) -> dict[str, str]:
    if body.quality not in ALLOWED_QUALITIES:
        raise HTTPException(status_code=400, detail="Unknown quality.")
    if body.media_type not in ALLOWED_MEDIA:
        raise HTTPException(status_code=400, detail="Choose video or audio.")

    valid, invalid = validate_urls(
        body.urls,
        watch_playlists=body.playlist_scope == "playlist",
    )
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Not a YouTube URL: {', '.join(invalid[:3])}",
        )
    if not valid:
        raise HTTPException(status_code=400, detail="Paste at least one YouTube URL.")

    try:
        directory = resolve_writable_dir(body.directory)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = Job()
    jobs[job.id] = job
    asyncio.create_task(_run_job(job, valid, directory, body.quality, body.media_type))
    return {"id": job.id}


@app.delete("/api/downloads/{job_id}")
def cancel_download(job_id: str) -> dict[str, bool]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download not found.")
    job.cancelled = True
    return {"ok": True}


@app.get("/api/downloads/{job_id}/events")
async def download_events(job_id: str) -> StreamingResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Download not found.")

    async def stream():
        index = 0
        while True:
            while index < len(job.history):
                event = job.history[index]
                index += 1
                yield _sse(event)
                if event["type"] in {"done", "error"}:
                    return
            if job.finished:
                return
            job.updated.clear()
            if index < len(job.history) or job.finished:
                continue
            try:
                await asyncio.wait_for(job.updated.wait(), timeout=1.0)
            except TimeoutError:
                continue

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _run_job(
    job: Job,
    urls: list[str],
    directory: Path,
    quality: str,
    media_type: str,
) -> None:
    loop = asyncio.get_running_loop()

    def on_event(event: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(job.emit, event)

    try:
        result = await asyncio.to_thread(
            download,
            urls,
            directory,
            quality,
            media_type,
            on_event,
            lambda: job.cancelled,
        )
        if job.cancelled:
            job.emit({"type": "error", "message": "Download cancelled."})
        else:
            failed_urls = result.get("failed_urls") or []
            message = (
                f"Finished: {result['succeeded']} succeeded, "
                f"{result['failed']} failed (of {result['total']})"
            )
            if failed_urls:
                message += "\nFailed: " + " ".join(failed_urls)
            job.emit(
                {
                    "type": "done",
                    "succeeded": result["succeeded"],
                    "failed": result["failed"],
                    "total": result["total"],
                    "failed_urls": failed_urls,
                    "message": message,
                }
            )
    except DownloadCancelled:
        job.emit({"type": "error", "message": "Download cancelled."})
    except Exception as exc:
        job.emit({"type": "error", "message": str(exc)})
    finally:
        job.finished = True


def open_browser_when_ready() -> None:
    import socket
    import time
    import webbrowser

    for _ in range(50):
        try:
            with socket.create_connection((HOST, PORT), timeout=0.2):
                webbrowser.open(APP_URL)
                return
        except OSError:
            time.sleep(0.1)


if __name__ == "__main__":
    import threading

    import uvicorn

    if not shutil.which("ffmpeg"):
        print("Warning: ffmpeg not found. Video merge and audio extraction need it.")
    if not js_runtimes():
        print("Warning: no JS runtime found. YouTube downloads need Node 22+ or Deno.")
    threading.Thread(target=open_browser_when_ready, daemon=True).start()
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
