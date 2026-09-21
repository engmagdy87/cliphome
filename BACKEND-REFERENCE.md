# Backend reference

Living mentor notes for this downloader. Newest inbox first.

---

## Inbox

### 2026-09-21 — Playlist → one folder named after the playlist

- A `playlist?list=` URL is one album, not a pile of files in the save directory. Create `saveDir / playlistTitle / video.mp4`. Reuse the folder on a second run (`exist_ok`). Watch URLs with `&list=` stay one video unless they paste the playlist link.

### 2026-09-21 — Merge off-screen, then move one file

- yt-dlp downloads video and audio as two files, then ffmpeg merges. Do that in a temp dir and `shutil.move` the result into the user’s folder. Do not switch to a muxed 360p format just to get one file.

### 2026-09-21 — YouTube watch size vs file pixels

- The website **scales** the stream to fill the player. A 360p file is 640×298; QuickTime shows those pixels, so it looks tiny. If yt-dlp cannot get a taller format (no login / no HLS), scale the file to the chosen canvas (1080/720) with ffmpeg after download. That is display size, not new detail.
- Do not treat cookies-from-browser as the next default: it can hang on the macOS keychain.

### 2026-09-21 — YouTube extraction needs a JS runtime

- yt-dlp can no longer fully talk to YouTube with Python alone. Enable **Node** (`js_runtimes: {node: {path}}`) or Deno, and install `yt-dlp[default]` so the EJS solver scripts are present. “This video is not available” on every URL is often this missing runtime, not a deleted video.
- Do not put the runtime in FastAPI. It belongs on the **service** that wraps yt-dlp.

### 2026-09-21 — Open the browser from the parent process

- `npm start` waits until port 8765 accepts, then `webbrowser.open`. Do that in `if __name__ == "__main__"`, not FastAPI startup: reload would open a new tab on every save.

### 2026-09-21 — `npm start` is a launcher, not a Node app

- `package.json` `scripts.start` just runs `.venv/bin/python app.py`. Same muscle memory as other repos. The process is still Python / FastAPI / yt-dlp.
- Other ways to shorten a boot: Makefile, a `./start` shell script, Poetry/`uv run`. Switch when you already live in that toolchain. Do not add Node dependencies because the start command says `npm`.

### 2026-09-21 — Local web app wrapping an external downloader

- A browser page cannot pick a real OS folder and write YouTube media there. The app is a **local server** (`127.0.0.1`) plus a UI. yt-dlp does the fetch; the OS folder picker is a native dialog from the server.
- There is no Download **model**. Nothing is persisted. yt-dlp is an **external tool**, so the wrapper is a **service**. HTTP in `app.py` stays thin: validate, start a job, stream events.
- Long work is a **job id + SSE**, not one blocking request. Quality / last folder / video-vs-audio are **UI preferences** (`localStorage`), not a database.
- Validate URLs and the folder at the edge. `req.body` is untrusted even on localhost.

---

## Concepts

### Request flow (this app)

```
Request → Route/HTTP (`app.py`) → Service (`download_service.py`) → yt-dlp
```

- **HTTP** — status codes, JSON, SSE. No yt-dlp calls inlined in the handler beyond `await asyncio.to_thread(...)`.
- **Service** — format selection, progress hooks, cancel flag. Owns talking to the tool.
- **Utils** — URL parse, native folder dialog. No download policy.

**Do** — put a service in when the work is an external process or spans more than one entity.

**Don't** — add a database, queue, or auth because “real apps have them.”

**Why** — this is one user, one machine, no records to keep.

### Long-running work

| Approach | When |
| --- | --- |
| One HTTP request waits until the file is done | Tiny jobs; browsers and proxies time out |
| Job id + poll `GET /status` | Simple; a bit chatty |
| Job id + SSE (this app) | Server pushes percent/log lines |
| WebSocket | Two-way (chat, collab). Overkill here |
| Redis/queue/worker | Multiple machines, retries, crash recovery |

**Do** — give the client a job id, stream progress, allow cancel.

**Don't** — hold the original POST open for a 2 GB playlist.

### Preferences vs records

- Last quality / folder / media type = **client cache** (`localStorage`).
- A table of past downloads would be a **record**. Add it when you actually need history.

---

## Side notes

- ffmpeg is required to merge separate video+audio streams and to extract MP3.
- YouTube’s terms restrict downloading. This is a personal local tool, not a public site.
- yt-dlp breaks when YouTube changes; upgrade the package, don’t rewrite the app.

---

## Drafts

- [ ] Probe each URL and list real formats instead of 1080/720 presets
- [ ] Cookies for age-restricted / logged-in videos
- [ ] Download history table (only if you want to re-open past files)
- [ ] Queue several jobs at once
