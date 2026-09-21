# Learning log

- 2026-09-21 — Detect video vs playlist vs watch+list; optional “whole playlist” from a watch URL.
- 2026-09-21 — Playlist: create the folder first, then move each finished video in (not wait for the whole list).
- 2026-09-21 — Night amber theme (gold accent on near-black).
- 2026-09-21 — Failed URL list with copy + retry (same folder/quality, new POST).
- 2026-09-21 — Playlist URLs save into a folder named after the playlist.
- 2026-09-21 — Stage video+audio merge in a temp dir; only the final file appears in the user’s folder.
- 2026-09-21 — Scale small YouTube streams to the chosen canvas (1080/720) so playback fills the player.
- 2026-09-21 — Batch tally (x/total + success/fail summary), title-only filenames, favicon.
- 2026-09-21 — YouTube downloads need Node/Deno + `yt-dlp[default]` (EJS). Wired `js_runtimes` on the downloader service.
- 2026-09-21 — `npm start` opens http://127.0.0.1:8765 after the port is up (parent process only, not on reload).
- 2026-09-21 — `npm start` / `yarn start` runs `.venv/bin/python app.py` (launcher only).
- 2026-09-21 — Local FastAPI app wrapping yt-dlp. Job + SSE for progress. Native OS folder picker. Quality/media/folder cached in localStorage. No database.
