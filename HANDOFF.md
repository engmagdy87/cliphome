# Handoff

## Goal

Show playlist summary in the Cliphome UI when a YouTube playlist is listed: name, video count, and total duration — clearly labeled as playlist (not “list”).

## Done

- Light theme, logo, Inter, logo-blue Download (`#3878f0`), fancy README + `docs/demo.gif` already on `origin/main` at `ce7c185` (and earlier `aeacde9` / `9823722`).
- Playlist summary feature implemented and **user-verified in UI** (screenshot: “Complete Postman Course In Arabic”, **29** videos, **3h 0m**).
- Backend emits `playlist_info` after flat yt-dlp list in `_expand_jobs` (`download_service.py`): `title`, `video_count`, `duration_seconds`, `duration_complete`, `folder`.
- UI `#playlists` / `#playlist-list` shows rows with **Playlist Name**, **Videos** (large), **Total Playlist Time**.
- Labels renamed from “List …” → “Playlist …” per user (Playlist correct for YouTube).
- Duration sum from flat `entries[].duration`; missing durations → `~` prefix via `duration_complete`.

## In progress

Branch: `main` (tracks `origin/main`, committed work up to date).

Uncommitted (`git diff --stat` — **186 insertions**):

| Path | Role |
| :--- | :--- |
| `download_service.py` | `_playlist_title`, `_playlist_duration_seconds`, `playlist_info` event |
| `static/app.js` | `addPlaylistInfo`, `formatDuration`, SSE handler, clear on start |
| `static/index.html` | Playlists section markup; CSS cache `?v=playlists2` |
| `static/styles.css` | Three-column playlist card styles |

Seam: feature works locally; **not committed / not pushed**.

## Files

- `download_service.py` — `_list_playlist`, `_expand_jobs`, playlist_info emit
- `static/app.js` — SSE `playlist_info` → playlist list UI
- `static/index.html` — `#playlists` block above progress meter
- `static/styles.css` — `.playlist-fields` / `.playlist-stat`
- `README.md` / `docs/demo.gif` — LinkedIn funnel assets (already committed)
- Transcript: `c6d7a49a-3b25-4c16-9728-43165bf72a4c`

## Decisions

- Prefer **Playlist** wording over List (YouTube term; matches section title).
- Video count gets equal visual weight to time (own labeled field, large `.playlist-stat`).
- Emit playlist metadata during download expand (no separate preview API).
- Sum flat-entry durations; do not re-fetch full metadata for totals (speed).
- LinkedIn advice (external ChatGPT share): same story as README; GitHub URL in first comment; optional — not coded.

## Constraints

- Local personal tool only; not a public downloader.
- Do not commit unless user asks.
- Use real `static/logo.png`; keep light theme.
- Personal-use honesty in README (keep what you’re allowed to keep).

## Blocked / open

None.

## Next

1. Commit the four uncommitted playlist-UI files when user asks.
2. Hard-refresh / smoke one playlist download after commit to confirm cache-bust.
3. Optional: push to `origin/main` and post LinkedIn (repo `https://github.com/engmagdy87/cliphome`).
