# YouTube Downloader

A small app that runs on **your computer**. You paste YouTube links, pick a folder, and the files land there. Nothing is uploaded to a website.

It is for personal use. YouTube’s terms do not allow downloading everything, so only use it for videos you are allowed to keep.

## What you can paste

- One video
- Several links (new lines or commas)
- A playlist URL (`youtube.com/playlist?list=…`) — that creates a folder named after the playlist and puts the videos inside it

A `watch?v=…&list=…` link is treated as **one video**, not the whole playlist.

## What you can choose

- **Save to** — Browse to a folder on this Mac
- **Quality** — 1080p is the default; your last choice is remembered
- **Video or audio** — video is the default; audio saves as MP3

If a few links fail (YouTube sometimes returns 403), they show up in a list. You can copy them or hit **Retry failed**.

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

The app opens at [http://127.0.0.1:8765](http://127.0.0.1:8765). Later you can just run `npm start` (or `yarn start`).

## Tips

- Keep this running on your own machine. It is not meant to be a public site.
- If YouTube changes something, update yt-dlp: `.venv/bin/pip install -U "yt-dlp[default]"`
