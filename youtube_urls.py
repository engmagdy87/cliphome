from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

FACEBOOK_HOSTS = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "mbasic.facebook.com",
    "web.facebook.com",
    "fb.com",
    "www.fb.com",
    "fb.watch",
    "www.fb.watch",
}

TWITTER_HOSTS = {
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
    "x.com",
    "www.x.com",
}

ALLOWED_HOSTS = YOUTUBE_HOSTS | FACEBOOK_HOSTS | TWITTER_HOSTS


def parse_urls(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [chunk.strip() for chunk in raw.replace(",", " ").split() if chunk.strip()]


def normalize(url: str) -> str:
    return url if "://" in url else f"https://{url}"


def _host(url: str) -> str:
    try:
        return (urlparse(normalize(url)).hostname or "").lower()
    except ValueError:
        return ""


def is_youtube_url(url: str) -> bool:
    host = _host(url)
    if host in YOUTUBE_HOSTS:
        return True
    return host.endswith(".youtube.com")


def is_facebook_url(url: str) -> bool:
    host = _host(url)
    if host in FACEBOOK_HOSTS:
        return True
    return host.endswith(".facebook.com") or host.endswith(".fb.watch")


def is_twitter_url(url: str) -> bool:
    host = _host(url)
    if host in TWITTER_HOSTS:
        return True
    return host.endswith(".twitter.com") or host.endswith(".x.com")


def is_supported_url(url: str) -> bool:
    return is_youtube_url(url) or is_facebook_url(url) or is_twitter_url(url)


def list_id(url: str) -> str | None:
    query = parse_qs(urlparse(normalize(url)).query)
    values = query.get("list") or []
    return values[0] if values else None


def is_playlist_url(url: str) -> bool:
    if not is_youtube_url(url):
        return False
    parsed = urlparse(normalize(url))
    path = (parsed.path or "").lower()
    return "playlist" in path and bool(list_id(url))


def url_kind(url: str) -> str:
    if is_playlist_url(url):
        return "playlist"
    if is_youtube_url(url) and list_id(url):
        return "video_in_playlist"
    return "video"


def to_playlist_url(url: str) -> str:
    lid = list_id(url)
    if not lid:
        return normalize(url)
    return f"https://www.youtube.com/playlist?list={lid}"


def canonical_key(url: str) -> str:
    parsed = urlparse(normalize(url))
    host = (parsed.hostname or "").lower()
    parts = [p for p in (parsed.path or "").split("/") if p]
    query = parse_qs(parsed.query)
    if is_playlist_url(url):
        return f"playlist:{query['list'][0]}"
    if is_youtube_url(url):
        if query.get("v"):
            return f"video:{query['v'][0]}"
        if host in {"youtu.be", "www.youtu.be"} and parts:
            return f"video:{parts[0]}"
        if parts and parts[0] in {"shorts", "embed", "live"} and len(parts) > 1:
            return f"video:{parts[1]}"
    if is_twitter_url(url) and "status" in parts:
        idx = parts.index("status")
        if idx + 1 < len(parts):
            return f"tweet:{parts[idx + 1]}"
    if is_facebook_url(url):
        if query.get("v"):
            return f"fb:{query['v'][0]}"
        if parts and parts[0] in {"reel", "share", "watch", "videos"} and len(parts) > 1:
            return f"fb:{parts[-1]}"
        if host.endswith("fb.watch") and parts:
            return f"fb:{parts[0]}"
    return normalize(url)


def validate_urls(raw: str, watch_playlists: bool = False) -> tuple[list[str], list[str]]:
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for part in parse_urls(raw):
        url = normalize(part)
        if not is_supported_url(url):
            invalid.append(part)
            continue
        if watch_playlists and url_kind(url) == "video_in_playlist":
            url = to_playlist_url(url)
        key = canonical_key(url)
        if key in seen:
            continue
        seen.add(key)
        valid.append(url)
    return valid, invalid
