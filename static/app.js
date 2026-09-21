const KEYS = {
  quality: "ytdl.quality",
  mediaType: "ytdl.mediaType",
  directory: "ytdl.directory",
  playlistScope: "ytdl.playlistScope",
};

const COPY_ICON = `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" fill="none" stroke="currentColor" stroke-width="2"/></svg>`;

const urlsEl = document.querySelector("#urls");
const directoryEl = document.querySelector("#directory");
const qualityEl = document.querySelector("#quality");
const qualityHint = document.querySelector("#quality-hint");
const browseBtn = document.querySelector("#browse");
const downloadBtn = document.querySelector("#download");
const cancelBtn = document.querySelector("#cancel");
const retryBtn = document.querySelector("#retry");
const statusEl = document.querySelector("#status");
const barEl = document.querySelector("#bar");
const statusLine = document.querySelector("#status-line");
const tallyEl = document.querySelector("#tally");
const failedEl = document.querySelector("#failed");
const failedListEl = document.querySelector("#failed-list");
const logEl = document.querySelector("#log");
const urlKindEl = document.querySelector("#url-kind");
const playlistScopeEl = document.querySelector("#playlist-scope");
const playlistScopeButtons = [...document.querySelectorAll("[data-playlist-scope]")];
const mediaButtons = [...document.querySelectorAll("[data-media]")];

let mediaType = "video";
let playlistScope = "video";
let currentJobId = null;
let events = null;
let batchTotal = 0;
let succeeded = 0;
let failed = 0;
let failedUrls = [];

function loadPrefs() {
  const quality = localStorage.getItem(KEYS.quality);
  const savedMedia = localStorage.getItem(KEYS.mediaType);
  const directory = localStorage.getItem(KEYS.directory);
  if (quality && [...qualityEl.options].some((opt) => opt.value === quality)) {
    qualityEl.value = quality;
  }
  if (savedMedia === "audio" || savedMedia === "video") {
    setMedia(savedMedia, { persist: false });
  }
  if (directory) directoryEl.value = directory;
  const savedScope = localStorage.getItem(KEYS.playlistScope);
  if (savedScope === "video" || savedScope === "playlist") {
    setPlaylistScope(savedScope, { persist: false });
  }
  refreshUrlKind();
}

function setMedia(next, { persist = true } = {}) {
  mediaType = next;
  mediaButtons.forEach((btn) => {
    btn.classList.toggle("is-on", btn.dataset.media === next);
  });
  const audio = next === "audio";
  qualityEl.disabled = audio;
  qualityHint.textContent = audio
    ? "Audio saves as MP3. Video quality is kept for next time."
    : "Cached after you change it.";
  if (persist) localStorage.setItem(KEYS.mediaType, next);
}

function setPlaylistScope(next, { persist = true } = {}) {
  playlistScope = next;
  playlistScopeButtons.forEach((btn) => {
    btn.classList.toggle("is-on", btn.dataset.playlistScope === next);
  });
  if (persist) localStorage.setItem(KEYS.playlistScope, next);
  refreshUrlKind();
}

function splitUrls(raw) {
  return raw.replaceAll(",", " ").split(/\s+/).filter(Boolean);
}

function classifyUrl(raw) {
  try {
    const href = raw.includes("://") ? raw : `https://${raw}`;
    const parsed = new URL(href);
    const host = parsed.hostname.replace(/^www\./, "").toLowerCase();
    if (!host.endsWith("youtube.com") && host !== "youtu.be") return "other";
    const path = parsed.pathname.toLowerCase();
    const list = parsed.searchParams.get("list");
    if (path.includes("playlist") && list) return "playlist";
    if (list) return "video_in_playlist";
    return "video";
  } catch {
    return "other";
  }
}

function refreshUrlKind() {
  const parts = splitUrls(urlsEl.value);
  if (!parts.length) {
    urlKindEl.textContent = "Paste a YouTube link and I’ll say if it’s a video or a playlist.";
    playlistScopeEl.hidden = true;
    return;
  }
  const kinds = parts.map(classifyUrl);
  const playlists = kinds.filter((kind) => kind === "playlist").length;
  const inPlaylist = kinds.filter((kind) => kind === "video_in_playlist").length;
  const videos = kinds.filter((kind) => kind === "video").length;
  const other = kinds.filter((kind) => kind === "other").length;
  const bits = [];
  if (videos) bits.push(`${videos} video${videos === 1 ? "" : "s"}`);
  if (playlists) bits.push(`${playlists} playlist${playlists === 1 ? "" : "s"}`);
  if (inPlaylist) {
    bits.push(
      `${inPlaylist} video${inPlaylist === 1 ? "" : "s"} inside a playlist`
    );
  }
  if (other) bits.push(`${other} not recognized`);
  let extra = "";
  if (playlists && !inPlaylist) {
    extra = " Playlist links save into a folder named after the playlist.";
  } else if (inPlaylist && playlistScope === "playlist") {
    extra = " Whole playlist is on — I’ll use the list= id and save into a playlist folder.";
  } else if (inPlaylist) {
    extra = " That’s a watch link with a playlist. Default is this video only.";
  }
  urlKindEl.textContent = `Detected: ${bits.join(", ")}.${extra}`;
  playlistScopeEl.hidden = inPlaylist === 0;
}

function setBusy(busy) {
  downloadBtn.disabled = busy;
  cancelBtn.hidden = !busy;
  retryBtn.disabled = busy || !failedUrls.length;
  urlsEl.disabled = busy;
  directoryEl.disabled = busy;
  browseBtn.disabled = busy;
  qualityEl.disabled = busy || mediaType === "audio";
  mediaButtons.forEach((btn) => {
    btn.disabled = busy;
  });
  playlistScopeButtons.forEach((btn) => {
    btn.disabled = busy;
  });
}

function showStatus() {
  statusEl.hidden = false;
}

function setBar(percent) {
  barEl.style.width = `${Math.max(0, Math.min(percent, 100))}%`;
}

function setLine(text, kind) {
  statusLine.textContent = text;
  statusLine.classList.toggle("is-ok", kind === "ok");
  statusLine.classList.toggle("is-bad", kind === "bad");
}

function setTally(text, kind) {
  tallyEl.textContent = text;
  tallyEl.classList.toggle("is-ok", kind === "ok");
  tallyEl.classList.toggle("is-bad", kind === "bad");
}

function showCounts() {
  setTally(`Downloaded ${succeeded}/${batchTotal}`);
  const done = succeeded + failed;
  if (batchTotal) setBar((done / batchTotal) * 100);
}

function rememberFailed(url) {
  if (!url || failedUrls.includes(url)) return;
  failedUrls.push(url);
}

function renderFailed(urls) {
  failedUrls = [...new Set(urls.filter(Boolean))];
  failedListEl.replaceChildren();
  failedEl.hidden = failedUrls.length === 0;
  retryBtn.disabled = failedUrls.length === 0 || Boolean(currentJobId);
  failedUrls.forEach((url) => {
    const row = document.createElement("li");
    row.className = "failed-row";
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = url;
    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "copy-btn";
    copyBtn.innerHTML = `${COPY_ICON}<span>Copy</span>`;
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(url);
      } catch {
        const field = document.createElement("textarea");
        field.value = url;
        document.body.append(field);
        field.select();
        document.execCommand("copy");
        field.remove();
      }
      copyBtn.classList.add("is-copied");
      copyBtn.querySelector("span").textContent = "Copied";
      window.setTimeout(() => {
        copyBtn.classList.remove("is-copied");
        copyBtn.querySelector("span").textContent = "Copy";
      }, 1600);
    });
    row.append(link, copyBtn);
    failedListEl.append(row);
  });
}

function log(message) {
  if (!message) return;
  logEl.textContent += `${message}\n`;
  logEl.scrollTop = logEl.scrollHeight;
}

async function readError(res) {
  try {
    const data = await res.json();
    const detail = data.detail || data.message;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
    }
    return detail || res.statusText;
  } catch {
    return res.statusText;
  }
}

qualityEl.addEventListener("change", () => {
  localStorage.setItem(KEYS.quality, qualityEl.value);
});

directoryEl.addEventListener("change", () => {
  localStorage.setItem(KEYS.directory, directoryEl.value.trim());
});

mediaButtons.forEach((btn) => {
  btn.addEventListener("click", () => setMedia(btn.dataset.media));
});

playlistScopeButtons.forEach((btn) => {
  btn.addEventListener("click", () => setPlaylistScope(btn.dataset.playlistScope));
});

urlsEl.addEventListener("input", refreshUrlKind);

browseBtn.addEventListener("click", async () => {
  browseBtn.disabled = true;
  try {
    const res = await fetch("/api/folder/pick", { method: "POST" });
    if (res.status === 409) return;
    if (!res.ok) {
      showStatus();
      setLine(await readError(res), "bad");
      return;
    }
    const data = await res.json();
    directoryEl.value = data.path;
    localStorage.setItem(KEYS.directory, data.path);
  } catch (err) {
    showStatus();
    setLine(err.message || "Could not open the folder picker.", "bad");
  } finally {
    browseBtn.disabled = false;
  }
});

cancelBtn.addEventListener("click", async () => {
  if (!currentJobId) return;
  await fetch(`/api/downloads/${currentJobId}`, { method: "DELETE" });
});

retryBtn.addEventListener("click", () => {
  if (!failedUrls.length) return;
  urlsEl.value = failedUrls.join("\n");
  refreshUrlKind();
  startDownload();
});

downloadBtn.addEventListener("click", () => startDownload());

async function startDownload() {
  const urls = urlsEl.value.trim();
  const directory = directoryEl.value.trim();
  if (!urls) {
    showStatus();
    setLine("Paste at least one YouTube URL.", "bad");
    return;
  }
  if (!directory) {
    showStatus();
    setLine("Choose a download folder.", "bad");
    return;
  }

  localStorage.setItem(KEYS.quality, qualityEl.value);
  localStorage.setItem(KEYS.mediaType, mediaType);
  localStorage.setItem(KEYS.directory, directory);
  localStorage.setItem(KEYS.playlistScope, playlistScope);

  showStatus();
  logEl.textContent = "";
  batchTotal = 0;
  succeeded = 0;
  failed = 0;
  failedUrls = [];
  renderFailed([]);
  setBar(0);
  setTally("Downloaded 0/0");
  setLine("Starting…");
  setBusy(true);

  try {
    const res = await fetch("/api/downloads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        urls,
        directory,
        quality: qualityEl.value,
        media_type: mediaType,
        playlist_scope: playlistScope,
      }),
    });
    if (!res.ok) {
      setLine(await readError(res), "bad");
      setBusy(false);
      return;
    }
    const { id } = await res.json();
    currentJobId = id;
    listen(id);
  } catch (err) {
    setLine(err.message || "Could not start the download.", "bad");
    setBusy(false);
  }
}

function listen(id) {
  if (events) events.close();
  events = new EventSource(`/api/downloads/${id}/events`);
  events.onmessage = (message) => {
    const event = JSON.parse(message.data);
    if (event.type === "log") {
      log(event.message);
    } else if (event.type === "batch") {
      batchTotal = event.total || 0;
      succeeded = event.succeeded || 0;
      failed = event.failed || 0;
      showCounts();
      setLine(`Downloading 0 of ${batchTotal}`);
    } else if (event.type === "progress") {
      const done = succeeded + failed;
      if (batchTotal && typeof event.percent === "number") {
        setBar(((done + event.percent / 100) / batchTotal) * 100);
      }
      const bits = [
        batchTotal ? `Downloaded ${succeeded}/${batchTotal}` : null,
        event.filename,
        event.percent != null ? `${event.percent}%` : null,
        event.speed,
        event.eta && event.eta !== "NA" ? `ETA ${event.eta}` : null,
      ].filter(Boolean);
      setLine(bits.join(" · "));
    } else if (event.type === "item_ok" || event.type === "item_fail") {
      succeeded = event.succeeded || 0;
      failed = event.failed || 0;
      batchTotal = event.total || batchTotal;
      showCounts();
      if (event.type === "item_fail") rememberFailed(event.url);
      setLine(
        event.type === "item_ok"
          ? `Downloaded ${succeeded}/${batchTotal}`
          : `Downloaded ${succeeded}/${batchTotal} · ${failed} failed`
      );
    } else if (event.type === "done") {
      succeeded = event.succeeded ?? succeeded;
      failed = event.failed ?? failed;
      batchTotal = event.total || batchTotal;
      setBar(100);
      const kind = failed === 0 ? "ok" : succeeded === 0 ? "bad" : undefined;
      const summary = `Finished: ${succeeded} succeeded, ${failed} failed (of ${batchTotal})`;
      setTally(summary, kind);
      setLine(failed ? "Retry the failed links below, or copy them." : "All saved.", kind);
      renderFailed(event.failed_urls?.length ? event.failed_urls : failedUrls);
      finish();
    } else if (event.type === "error") {
      setTally(event.message || "Download failed.", "bad");
      setLine(event.message || "Download failed.", "bad");
      log(event.message);
      renderFailed(failedUrls);
      finish();
    }
  };
  events.onerror = () => {
    if (downloadBtn.disabled) {
      setLine("Lost connection to the downloader.", "bad");
      finish();
    }
  };
}

function finish() {
  if (events) {
    events.close();
    events = null;
  }
  currentJobId = null;
  setBusy(false);
}

loadPrefs();
