# Handoff

## Goal

Local personal video downloader (Cliphome) on this Mac: FastAPI + static UI.
YouTube, Facebook, and X. GitHub: https://github.com/engmagdy87/cliphome
Paste video(s) or a playlist, pick an OS folder, cache quality, video default vs audio.
Stay a local tool; GitHub holds the code.

## Done

App: `http://127.0.0.1:8765`. Not the shop API.

Browser-verified early: `https://www.youtube.com/watch?v=jNQXAC9IVRw` as video and MP3 in `tmp-downloads/`.

1:19 PM: all 15 failed
`No supported JavaScript runtime could be found. Only deno is enabled by default`.
Node `js_runtimes` + `yt-dlp[default]`. User: "great, works now".

Batch to `/Users/mm/YT Videos`: 14 ok, 1 fail
`https://www.youtube.com/watch?v=wbAnah83rbo` HTTP 403 format 136+251.

GitHub (on origin):
- https://github.com/engmagdy87/cliphome **public**
- `21d65f0` initial; `680bf3c` first HANDOFF; `bb04998` playlist incremental + URL detect
- No secrets in git

Playlist incremental (local test, not user Finder):
- `PL7qU_liavgB2kgJJIzRgtn_PRr7zyBO46` → **Prim 1 2023**, 19 videos
- Folder `/tmp/ytdl-playlist-test2/Prim 1 2023` then `Me at the zoo.mp4`

URL detect (browser `/?detect=1`):
- `watch?v=0EkGFz-1WDg&list=PLA2Wns-dg9lfsl4TTdrWN784O3upmiHKr` → video inside playlist
- **Whole playlist** rewrites to `playlist?list=`

User screenshot 3:37 PM: Whole playlist on, Save to `/Users/mm/YT Videos`, Quality Best, **Downloaded 0/6**, log
`YouTube gave 1152x720. Scaling to 1920x1080 so it fills the player the way the website does.`
Stop looked dead during that ffmpeg scale.

Import check after Stop code: `from download_service import _run_cancellable, DownloadCancelled` → `ok`.
User has **not** confirmed Stop in the UI.

## In progress

Branch `main`, tracks `origin/main` at `bb04998`.
Uncommitted (5 files, + this HANDOFF.md):

- `app.py` — DELETE emits `Stop requested. Finishing the current step…`
- `download_service.py` — `_run_cancellable` kills ffmpeg; no `move` after cancel
- `static/app.js` — **Stopping…** immediately; ignore progress while `stopping`
- `LEARNING.md` / `BACKEND-REFERENCE.md` notes

Seam: yt-dlp’s **own** merge ffmpeg (`[Merger] Merging formats`) is still `subprocess.run` inside yt-dlp. Stop during merge may wait until that merge ends. Our scale ffmpeg is interruptible.

## Files

- `app.py` — FastAPI, SSE, `playlist_scope`, cancel emit
- `download_service.py` — list playlist, `_save_one`, temp merge, upscale, `_run_cancellable`
- `youtube_urls.py` — `url_kind`, `to_playlist_url`, `validate_urls(..., watch_playlists)`
- `folder_picker.py` — macOS folder dialog
- `static/index.html` / `static/app.js` / `static/styles.css` / `static/favicon.svg`
- `package.json` — `setup` / `start`
- `requirements.txt` — fastapi, uvicorn, `yt-dlp[default]`
- `README.md`
- `.gitignore` — `.venv/`, `tmp-downloads/`, `node_modules/`
- Transcript: `658072cc-b251-45c0-937b-d0cc8ca11818`

## Decisions

- Local only. Do not deploy this as a public downloader (Cloudflare/Vercel cannot run it).
- `/playlist?list=` = playlist. `/watch?v=` = one video. `/watch?v=&list=` = video in a playlist; default **this video only**. Opt-in **Whole playlist**.
- Stage merge/scale in temp; mkdir playlist folder as soon as listed; move each finished file.
- Temp `ytdl-*` deleted in `finally` (success/fail/cancel). Crash leftovers can remain in `/var/folders/…/T/`.
- Do not default cookies-from-browser (keychain hang).
- Stop must ack in the UI even if the worker is blocked; kill **our** ffmpeg; do not move the in-progress file.

## Constraints

- Personal local use. YouTube ToS: only keep what they are allowed to keep.
- GitHub: `engmagdy87` / Mohamed Magdy / `mohamed.magdy.abdelhamid@gmail.com`
- Do not commit `.venv`, secrets, download leftovers
- Video default vs audio; quality cached
- Kill leftover process on 8765 if address already in use
- Shorts `/shorts/…` are videos

## Blocked / open

None blocking.

Uncommitted Stop fix not user-tested.
Finder one-by-one playlist not user-confirmed (screenshot did show 0/6 and a scale log, so listing + per-item path is running).
Retry failed watch URLs use the folder in **Save to**, not auto the playlist subfolder.
No startup sweep of leftover `ytdl-*` dirs.
yt-dlp internal merge not killed by Stop yet.

## Next

1. Hard-refresh, run a download, hit **Stop** during “Scaling to …” — expect Stopping… and no new file for that item.
2. If Stop during `[Merger] Merging formats` still lags, interrupt yt-dlp’s ffmpeg next.
3. Commit/push the Stop fix when the user asks (not committed now).
