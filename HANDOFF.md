# Handoff

## Goal

Polish Cliphome’s local web UI and docs: light theme, real brand logo, logo-blue Download button, Inter type, clean static assets, fancy README with logo.

## Done

- Light theme live at `http://127.0.0.1:8765` (browser-checked this session). Soft blue-grey page, white panel, dark text.
- Header uses `static/logo.png` (user-replaced good transparent RGBA wordmark; 1736×494).
- Download / accent color `#3878f0` (sampled from logo blues); hover `#2f68d8`.
- UI font: Inter via Google Fonts + system fallbacks; `styles.css?v=light6`.
- Lede copy kept at `max-width: 54ch` (not full-width) — readability choice confirmed with user.
- Removed unused `static/favicon.svg`; keep `favicon.ico` + `favicon.png` (C + play mark).
- Fancy `README.md` with centered logo, badges, tables, quick start (uncommitted).
- Committed on `main` / `origin/main`: `9823722` — light styles, `logo.png`, favicon ico/png, Inter, blue accent, logo in HTML.

## In progress

Branch: `main` (tracks `origin/main`, up to date for committed work).

Uncommitted (`git diff --stat`):

| Path | Change |
| :--- | :--- |
| `README.md` | Fancy rewrite + logo |
| `static/favicon.svg` | deleted |
| `static/index.html` | drop `favicon.svg` `<link>` only |

Seam: working tree not committed after asset cleanup + README. UI CSS/logo already on origin at `9823722`.

## Files

- `static/styles.css` — light tokens, Inter, `#3878f0` accent
- `static/index.html` — logo wordmark, Inter links, favicons (svg link pending remove)
- `static/logo.png` — brand wordmark (user’s good version)
- `static/favicon.ico` / `static/favicon.png` — tab / Apple touch (C mark)
- `README.md` — docs with logo (dirty)
- `app.py` — serves UI at `:8765` (unchanged this session)
- Transcript: `c6d7a49a-3b25-4c16-9728-43165bf72a4c`

## Decisions

- Light theme required (user rejected dark / gold-on-black).
- Prefer real `logo.png` over hand-made SVG mark + text (SVG looked “weird”).
- Do not stretch lede full-width; keep ~54ch.
- Accent = logo blue, not teal/purple CTA.
- Inter = industry UI font for eye comfort (explicit user ask).
- Drop `favicon.svg` as redundant; keep ico + png.

## Constraints

- Personal local tool only; not a public downloader.
- Only keep videos the user is allowed to keep.
- User wants brand assets (`logo.png`) used, not substitutes.
- Do not commit unless asked (uncommitted README/favicon cleanup still pending).

## Blocked / open

None.

## Next

1. Commit uncommitted trio: `README.md`, delete `static/favicon.svg`, `static/index.html` favicon link cleanup.
2. Hard-refresh `http://127.0.0.1:8765` and confirm logo, Inter, blue Download.
3. Optional: replace C-mark favicons with a crop of the play mark from `logo.png` if brand consistency is wanted.
