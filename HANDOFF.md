# Handoff

## Goal

Local personal YouTube downloader: FastAPI + static UI on this Mac.
Paste one URL, many URLs, or a playlist; pick an OS folder; quality cached; video default vs audio.
User asked to publish it to GitHub with a plain-language README.

## Done

Local app at `http://127.0.0.1:8765`. Separate project from the shop API.

Browser-verified early: `https://www.youtube.com/watch?v=jNQXAC9IVRw` saved as video and as MP3 under `tmp-downloads/`. Reload restored 720p / audio / folder from `localStorage`.

User log at 1:19 PM: all 15 items failed with
`No supported JavaScript runtime could be found. Only deno is enabled by default`.
Fix: `js_runtimes` Node on the downloader service + `yt-dlp[default]` (EJS).
Probed `hULoNg1QcAg` with `extract_info` → title **Lesson 15, 16 Families of the Numbers**.
User: "great, works now".

Later batch of 15 to `/Users/mm/YT Videos`: 14 ok, 1 fail.
Failed URL: `https://www.youtube.com/watch?v=wbAnah83rbo`
Error: HTTP 403 on format 136+251.

Git (verified):
- Branch `main`, tracks `origin/main`, working tree clean (before this HANDOFF.md).
- Commit `21d65f0` `Add a local YouTube downloader with a simple web UI.`
- Remote `git@github.com:engmagdy87/youtube-downloader.git`
- `gh repo create youtube-downloader --public --source=. --remote=origin --push`
- Live: https://github.com/engmagdy87/youtube-downloader
- Ignored: `.venv/`, `tmp-downloads/`, `node_modules/`

Start: `npm run setup` then `npm start` (`.venv/bin/python app.py`). Parent process opens the browser after port 8765 is up, not on uvicorn reload.

## In progress

This `HANDOFF.md` is new and uncommitted.

Coded after the working download, **not confirmed by the user in chat**:
- Tally `x/total` + success/fail summary, title-only filenames, tab favicon
- ffmpeg canvas upscale so 360p files fill the player (default quality 1080)
- Stage merge in temp dir (`ytdl-` mkdtemp), hide scaling tempfile as `.ytdl-*.mp4`
- Playlist `playlist?list=` → `saveDir / playlistTitle /`
- Failed-URL list with copy + **Retry failed** (`failed_urls` on SSE `done`)
- Night amber CSS (`--bg #0f1012`, `--accent #e8b86d`, `--ink #1c1915`, `--bad #e08a7a`)

Dummy URLs given for retry UI (user asked; result not reported):
```
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://www.youtube.com/watch?v=zzzzzzzzzzz
https://www.youtube.com/watch?v=_not_a_vid_
```

Cookie probe (`cookiesfrombrowser` chrome/safari/…) hung on macOS keychain; process killed. Not wired into the app.

## Files

- `app.py` — FastAPI, jobs, SSE, folder picker route, open browser in `__main__`
- `download_service.py` — yt-dlp wrapper: Node runtime, temp merge, upscale, playlist dest, `failed_urls`
- `youtube_urls.py` — parse/validate; `watch?v=&list=` is one video, not a playlist
- `folder_picker.py` — macOS `osascript` native folder dialog
- `static/index.html` / `static/app.js` / `static/styles.css` / `static/favicon.svg` — UI
- `package.json` — `setup` / `start` launchers only (no Node app)
- `requirements.txt` — `fastapi`, `uvicorn[standard]`, `yt-dlp[default]`
- `README.md` — human setup/run/ToS
- `.gitignore` — venv, tmp-downloads, node_modules
- `BACKEND-REFERENCE.md` — mentor notes for this repo
- `LEARNING.md` — dated bullets
- Transcript: `658072cc-b251-45c0-937b-d0cc8ca11818`

## Decisions

- Local FastAPI + page, not Electron/Tauri/CLI. Browser cannot pick an arbitrary OS folder or fetch YouTube media.
- No Download model / no DB. yt-dlp is an external **service**. Prefs in `localStorage`.
- Long work = job id + SSE, not one blocking POST.
- `npm start` is a Python launcher. Do not add Node deps for that.
- Node JS runtime, not Deno: Node v22 already on the machine.
- Do not mux to 360p just to get one file; merge off-screen then move.
- Upscale is display size, not extra detail. Anonymous yt-dlp often maxes at 720/360.
- Do not default to cookies-from-browser (keychain hang).
- GitHub public. User never said public vs private; created public.
- Do not use Cursor origin skill; user asked for GitHub (`engmagdy87`).

## Constraints

- Personal local tool. YouTube ToS: only keep what they are allowed to keep.
- GitHub: `engmagdy87` / Mohamed Magdy / `mohamed.magdy.abdelhamid@gmail.com`
- Do not commit `.venv`, secrets, download leftovers
- Video is default vs audio
- Quality cached after choose; 1080 is the UI default after later work
- `watch` + `list` stays one video; full set needs `youtube.com/playlist?list=…`
- Kill leftover server on 8765 if “address already in use”
- User explicitly asked to create the GitHub repo and push

## Blocked / open

None blocking.

Unverified: failed-list copy/retry, playlist folder, night amber, merge/upscale filename in the user’s real folders.

403s can still happen (e.g. `wbAnah83rbo`). Retry first; no cookie login in the app.

Whether to commit this `HANDOFF.md` to GitHub: not asked.

## Next

1. Hard-refresh `http://127.0.0.1:8765` and paste the three dummy URLs to confirm Failed URLs / Copied / Retry failed.
2. Paste a real `playlist?list=` URL and confirm a folder named after the playlist.
3. Leave cookies-from-browser off unless the user opts in after a 403 that retry does not clear.
