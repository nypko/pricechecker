"""Polite HTTP: honest user agent, robots.txt check, per-host delay, retries."""
import json
import time
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

USER_AGENT = "PriceCheckerBot/0.1 (hourly price comparison; affiliate partner)"
_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}
_last_hit: dict[str, float] = {}
MIN_DELAY_SEC = 3.0
HOST_DELAY: dict[str, float] = {}   # stricter per-host spacing, e.g. Shopify allows ~1 request/min per IP
HOST_GROUP: dict[str, str] = {}     # hosts that share one rate limit (all Shopify shops) are spaced as one
ROBOTS_CACHE = Path("data/robots_cache.json")
ROBOTS_TTL = timedelta(hours=24)


class Blocked(Exception):
    """robots.txt disallows the URL, or the site refuses automated access (401/403/429)."""


def _robots_text(host: str) -> str:
    """robots.txt, cached on disk for a day: on rate-limited stores every saved request counts."""
    cache = json.loads(ROBOTS_CACHE.read_text()) if ROBOTS_CACHE.exists() else {}
    hit = cache.get(host)
    if hit and datetime.now(timezone.utc) - datetime.fromisoformat(hit["fetched"]) < ROBOTS_TTL:
        return hit["text"]
    try:
        _wait(urlparse(host).netloc)
        r = _session.get(host + "/robots.txt", timeout=20)
        text = r.text if r.ok else ""
        if r.status_code == 429:
            return ""   # rate limited: don't cache, try again next run
    except requests.RequestException:
        return ""
    cache[host] = {"text": text, "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    ROBOTS_CACHE.parent.mkdir(exist_ok=True)
    ROBOTS_CACHE.write_text(json.dumps(cache, indent=1))
    return text


def allowed(url: str) -> bool:
    host = urlparse(url).scheme + "://" + urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(_robots_text(host).splitlines())
        _robots[host] = rp
    return _robots[host].can_fetch(USER_AGENT, url)


def _wait(host: str) -> None:
    key = HOST_GROUP.get(host, host)
    wait = HOST_DELAY.get(host, MIN_DELAY_SEC) - (time.monotonic() - _last_hit.get(key, 0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[key] = time.monotonic()


def get(url: str, *, retries: int = 2, respect_robots: bool = True, **kw) -> requests.Response:
    if respect_robots and not allowed(url):
        raise Blocked(f"robots.txt disallows {url}")
    host = urlparse(url).netloc
    for attempt in range(retries + 1):
        _wait(host)
        try:
            r = _session.get(url, timeout=30, **kw)
        except requests.RequestException:
            if attempt == retries:
                raise
            continue
        # rate limited: back off and try again - except on hosts with strict spacing (Shopify), where every retry
        # inside the penalty window seems to extend it; those wait for the next hourly run instead
        if r.status_code == 429 and attempt < retries and host not in HOST_DELAY:
            retry_after = r.headers.get("Retry-After", "")
            time.sleep(min(int(retry_after) if retry_after.isdigit() else 20 * (attempt + 1), 90))
            continue
        if r.status_code in (401, 403, 429):
            raise Blocked(f"{r.status_code} from {host} - the site refuses or rate-limits automated access; use its affiliate feed/API")
        if r.status_code >= 500 and attempt < retries:
            continue
        r.raise_for_status()
        return r
    raise RuntimeError("unreachable")
