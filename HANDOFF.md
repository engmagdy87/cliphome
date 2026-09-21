# Handoff

## Goal

Local personal YouTube downloader on this Mac: FastAPI + static UI.
Paste video(s) or a playlist, pick an OS folder, cache quality, video default vs audio.
Stay a local tool; GitHub holds the code.

## Done

App: `http://127.0.0.1:8765`. Not the shop API.

Browser-verified early: `https://www.youtube.com/watch?v=jNQXAC9IVRw` as video and MP3 in `tmp-downloads/`. Reload restored 720p / audio / folder from `localStorage`.

1:19 PM user log: all 15 failed with
`No supported JavaScript runtime could be found. Only deno is enabled by default`.
Fix: Node `js_runtimes` + `yt-dlp[default]`. User: "great, works now".

Batch to `/Users/mm/YT Videos`: 14 ok, 1 fail.
Failed: `https://www.youtube.com/watch?v=wbAnah83rbo` HTTP 403 on format 136+251.

Git (already on origin before this turn):
- https://github.com/engmagdy87/youtube-downloader
- Public. `gh repo view` → `"visibility":"PUBLIC"`
- `21d65f0` initial app; `680bf3c` first HANDOFF.md
- No secrets in git (no `.env`, tokens, cookies). Commit author email is public identity.

Playlist incremental (code + local test, not user Finder):
- `_list_playlist` on `PL7qU_liavgB2kgJJIzRgtn_PRr7zyBO46` → title **Prim 1 2023**, 19 videos.
- Folder created before downloads: `/tmp/ytdl-playlist-test2/Prim 1 2023`
- `_save_one` of `jNQXAC9IVRw` landed `Me at the zoo.mp4` in that folder.

URL detect (python + browser on `127.0.0.1:8765/?detect=1`):
- `watch?v=0EkGFz-1WDg&list=PLA2Wns-dg9lfsl4TTdrWN784O3upmiHKr` → `video_in_playlist`
- UI: `Detected: 1 video inside a playlist. That’s a watch link with a playlist. Default is this video only.`
- **Whole playlist** → `Whole playlist is on — I’ll use the list= id and save into a playlist folder.`
- `validate_urls(watch, watch_playlists=True)` → `https://www.youtube.com/playlist?list=PLA2Wns-dg9lfsl4TTdrWN784O3upmiHKr`

Temp: `_save_one` `finally: shutil.rmtree(work_dir)`. Success / fail / cancel. Force-kill can leave `ytdl-*` in macOS `/var/folders/…/T/`.

Start: `npm start` → `.venv/bin/python app.py`. Opens browser after port 8765 is up.

## In progress

Branch `main`. At handoff write, origin was `680bf3c`; 9 files + this HANDOFF were local.
User asked to commit/push in the same turn.

User has **not** confirmed in Finder that a real playlist folder appears and files land one by one.

## Files

- `app.py` — FastAPI, SSE jobs, `playlist_scope` on POST `/api/downloads`
- `download_service.py` — list playlist, mkdir first, `_save_one` per video, temp merge/upscale
- `youtube_urls.py` — `url_kind`, `to_playlist_url`, `validate_urls(..., watch_playlists)`
- `folder_picker.py` — macOS folder dialog
- `static/index.html` / `static/app.js` / `static/styles.css` / `static/favicon.svg`
- `package.json` — `setup` / `start` launchers
- `requirements.txt` — fastapi, uvicorn, `yt-dlp[default]`
- `README.md` — human setup; watch+list vs playlist
- `.gitignore` — `.venv/`, `tmp-downloads/`, `node_modules/`
- `BACKEND-REFERENCE.md` / `LEARNING.md`
- Transcript: `658072cc-b251-45c0-937b-d0cc8ca11818`

## Decisions

- Local server + page, not Cloudflare/Vercel. Those cannot run yt-dlp/ffmpeg or write the user’s disk.
- Public YouTube-downloader hosting is a different product; do not deploy this as a site.
- `/playlist?list=` = playlist. `/watch?v=` = one video. `/watch?v=&list=` = video in a playlist; default **this video only** so 15 lesson watch links do not become 15 copies of the same playlist. Opt-in **Whole playlist** rewrites to `playlist?list=` and dedupes by list id.
- Stage merge/scale in temp; publish dest folder as soon as the list is known; move each finished file.
- Do not default cookies-from-browser (keychain hang).
- GitHub public under `engmagdy87`.

## Constraints

- Personal local use. YouTube ToS: only keep what they are allowed to keep.
- GitHub: `engmagdy87` / Mohamed Magdy / `mohamed.magdy.abdelhamid@gmail.com`
- Do not commit `.venv`, secrets, download leftovers
- Video default vs audio; quality cached; UI default 1080
- Kill leftover process on 8765 if address already in use
- Shorts `/shorts/…` are videos (already in `canonical_key`)

## Blocked / open

None blocking.

Unverified by the user: Finder playlist one-by-one; night amber; failed-list retry on their real downloads.

Retry of a failed **watch** URL uses the folder currently in **Save to**, not automatically the playlist subfolder.

No startup sweep of leftover `ytdl-*` temp dirs after a crash.

## Next

1. Hard-refresh `http://127.0.0.1:8765`. Paste a `watch?v=&list=` URL, choose **Whole playlist**, confirm the named folder appears and files land one by one.
2. If a video fails, Browse into that playlist folder before **Retry failed** if files should stay there.
3. Leave cookies-from-browser off unless retry cannot clear a 403.
