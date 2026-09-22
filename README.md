# Cliphome

A small app that runs on **your computer**. You paste a video link, pick a folder, and the file lands there — the clip comes home. Nothing is uploaded to a website.

It is for personal use. Site terms often do not allow downloading everything, so only keep videos you are allowed to keep.

## What you can paste

- YouTube videos, Shorts, and playlists
- Facebook videos, Reels, and `fb.watch` links
- X (Twitter) video posts (`x.com/…/status/…` or `twitter.com/…/status/…`)
- Several links at once (new lines or commas)

A YouTube playlist URL (`youtube.com/playlist?list=…`) creates a folder named after the playlist; each video lands there when it finishes. A `watch?v=…&list=…` link is a **video inside a playlist** — choose this video only (default) or the whole playlist.

Facebook and X are one video per link. Some posts are login-only; those can fail without a browser login (the app does not read your cookies).

## What you can choose

- **Save to** — Browse to a folder on this Mac
- **Quality** — 1080p is the default; your last choice is remembered
- **Video or audio** — video is the default; audio saves as MP3

If a few links fail (the site sometimes returns 403, or wants a login), they show up in a list. You can copy them or hit **Retry failed**.

## First-time setup

You need:

- Python 3
- Node (for `npm start`, and yt-dlp uses it to talk to YouTube)
- ffmpeg (Homebrew: `brew install ffmpeg`)

Then, in this folder:

```bash
npm run setup
npm start
```

The app opens at [http://127.0.0.1:8765](http://127.0.0.1:8765). Later you can just run `npm start` (or `yarn start`). One Ctrl+C stops it. While changing the Python code, use `npm run dev` so it reloads itself.

## Tips

- Keep this running on your own machine. It is not meant to be a public site.
- If a site starts failing, update yt-dlp: `.venv/bin/pip install -U "yt-dlp[default]"`
