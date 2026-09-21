from urllib.parse import parse_qs, urlparse

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def parse_urls(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [chunk.strip() for chunk in raw.replace(",", " ").split() if chunk.strip()]


def normalize(url: str) -> str:
    return url if "://" in url else f"https://{url}"


def is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(normalize(url))
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if host in ALLOWED_HOSTS:
        return True
    return host.endswith(".youtube.com")


def is_playlist_url(url: str) -> bool:
    parsed = urlparse(normalize(url))
    path = (parsed.path or "").lower()
    query = parse_qs(parsed.query)
    return "playlist" in path and bool(query.get("list"))


def canonical_key(url: str) -> str:
    parsed = urlparse(normalize(url))
    host = (parsed.hostname or "").lower()
    parts = [p for p in (parsed.path or "").split("/") if p]
    query = parse_qs(parsed.query)
    if is_playlist_url(url):
        return f"playlist:{query['list'][0]}"
    if query.get("v"):
        return f"video:{query['v'][0]}"
    if host in {"youtu.be", "www.youtu.be"} and parts:
        return f"video:{parts[0]}"
    if parts and parts[0] in {"shorts", "embed", "live"} and len(parts) > 1:
        return f"video:{parts[1]}"
    return normalize(url)


def validate_urls(raw: str) -> tuple[list[str], list[str]]:
    valid: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for part in parse_urls(raw):
        url = normalize(part)
        if not is_youtube_url(url):
            invalid.append(part)
            continue
        key = canonical_key(url)
        if key in seen:
            continue
        seen.add(key)
        valid.append(url)
    return valid, invalid
