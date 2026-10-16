"""Stores with a product sitemap and one product page per configuration (e.g. Trading Shenzhen, PrestaShop):
read the sitemap, pick the tracked phones by their URL, and read price/stock from each page's schema.org data.
Pages are cached and only re-read when the sitemap's <lastmod> changes, or every few hours."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import http
from ..models import Offer
from ..normalize import edition_of, model_id, storage_of
from .webpage import parse

_URL = re.compile(r"<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?", re.S)
# ".../xiaomi-17-pro-max-16gb512gb", ".../oneplus-15-16gb512gb-eu-warehouse", ".../oppo-find-n6-12gb256gb-foldable"
_SLUG_STORAGE = re.compile(r"-(\d{1,2})gb-?(\d{2,4}gb|\dtb)\b")
_SLUG_EXTRA = re.compile(r"-(eu-warehouse|eu-lager|foldable)\b")
REFRESH = timedelta(hours=6)
_STORAGE_PART = re.compile(r"\s+-\s+\d{1,2}\s*GB\s*/\s*\d+\s*(?:GB|TB)\b.*$", re.I)


def title_model(name: str) -> str:
    """'Oppo Find N5 - 16GB/512GB - Foldable' -> 'Oppo Find N5': titles read model - storage - extras."""
    return _STORAGE_PART.sub("", name)


def slug_model(url: str) -> str:
    """Best guess of the model id from the URL alone, to decide which pages are worth reading."""
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return model_id(_SLUG_EXTRA.sub("", _SLUG_STORAGE.sub("", slug)).replace("-", " "))


def fetch(store: str, cfg: dict, catalog: list[dict]) -> list[Offer]:
    tracked = {p["id"] for p in catalog}
    aliases = cfg.get("aliases") or {}
    skip_url = re.compile(cfg["exclude_url"], re.I) if cfg.get("exclude_url") else None
    skip_title = re.compile(cfg["exclude_title"], re.I) if cfg.get("exclude_title") else None
    if cfg.get("request_spacing_sec"):
        http.HOST_DELAY[cfg["sitemap_url"].split("/")[2]] = cfg["request_spacing_sec"]
    cache_file = Path(f"data/{store}_pages.json")
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    now = datetime.now(timezone.utc)
    entries = _URL.findall(http.get(cfg["sitemap_url"]).text)
    offers, seen = [], set()
    for url, lastmod in entries:
        if (skip_url and skip_url.search(url)) or aliases.get(slug_model(url), slug_model(url)) not in tracked:
            continue
        seen.add(url)
        hit = cache.get(url)
        if not hit or hit["lastmod"] != lastmod or now - datetime.fromisoformat(hit["fetched"]) > REFRESH:
            try:
                info = parse(http.get(url).text)
            except http.Blocked:
                raise
            except Exception as e:   # one broken page shouldn't drop the whole store
                print(f"  [{store}] warning: {url}: {type(e).__name__}: {e}")
                continue
            hit = cache[url] = {"lastmod": lastmod, "fetched": now.isoformat(timespec="seconds"), "info": info}
        info = hit["info"]
        if not info or not info.get("price") or (skip_title and skip_title.search(info["name"])):
            continue
        mid = model_id(title_model(info["name"]))
        mid = aliases.get(mid, mid)
        if mid not in tracked:   # the page title disagrees with the URL guess: trust the title
            continue
        # e.g. "... - EU Warehouse": same phone, shipped from inside the EU with other terms -> its own store entry
        sub = next((name for name, pattern in (cfg.get("sub_stores") or {}).items() if re.search(pattern, info["name"], re.I)), store)
        offers.append(Offer(store=sub, model_id=mid, edition=edition_of(info["name"]),
                            storage=storage_of(info["name"]) if storage_of(info["name"]) != "base" else storage_of(url.replace("gb", "GB ")),
                            title=info["name"], price=info["price"], currency=info["currency"] or cfg.get("currency", "EUR"),
                            available=info["available"], url=url,
                            prices={info["currency"] or cfg.get("currency", "EUR"): info["price"]}))
    cache_file.write_text(json.dumps({u: v for u, v in cache.items() if u in seen}, indent=0))
    return offers
