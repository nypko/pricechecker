"""Magento 2 stores (e.g. Giztop): the phone category's first page (its newest products), plus every product page of a
tracked phone found in the store's sitemap; the per-variant prices (storage x color) come from each product page.
Giztop's robots.txt disallows the category's further pages (`Disallow: /*?p=`), so the sitemap stands in for them.
Product pages are cached and re-read when their sitemap date or listing price changes, or every few hours."""
import base64
import hashlib
import html
import json
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import requests

from .. import http
from ..models import Offer
from ..normalize import edition_of, model_id, storage_of
from .shopify import cheapest_per_config
from .sitemap import _URL
from .webpage import parse

_ITEM = re.compile(r'class="product-item-link"\s+href="([^"]+)">\s*([^<]+?)\s*</a>.*?data-price-amount="([0-9.]+)"', re.DOTALL)
_SP_CONFIG = re.compile(r'"spConfig":\s*(\{.*?\})\s*,\s*"gallerySwitchStrategy"', re.DOTALL)
# single-variant listings: "OPPO Find X9 Ultra-Black-12GB - 256GB"
# "Model-Colour-12GB - 256GB", optionally followed by a note: "(Brand New, Clearance, 30% off, )" on clearance units
_SIMPLE = re.compile(r"^(?P<base>.+?)-(?P<color>[^-]+)-(?P<storage>\d+\s*GB\s*-\s*\d+\s*(?:GB|TB))(?:\s*\([^()]*\))?$",
                     re.IGNORECASE)
REFRESH = timedelta(hours=6)
SITEMAP_TTL = timedelta(hours=20)   # the sitemap lists every product (Giztop: ~24,000 pages in four ~10 MB files): once a day
# sitemap addresses that are no phone for sale, whatever phone name they start with
_SLUG_SKIP = re.compile(r"\b(?:used|refurbished|almost new|open box|case|cover|protector|tempered|glass|film|charger|cable|"
                        r"strap|holder|stand|skin|adapter|stylus|keyboard|lens|kit|accessories)\b")
SITE_CURRENCIES = ["EUR", "GBP", "AUD"]
RATES_CACHE = Path("data/shop_rates.json")   # shared with the Shopify stores


def _final_prices(page: str) -> list[float]:
    """Every price on the page (variant data, else the price boxes): the store converts all of them at one rate."""
    return [float(x) for x in re.findall(r'"finalPrice":\{"amount":([0-9.]+)', page)
            or re.findall(r'data-price-amount="([0-9.]+)"', page)]


def market_rates(base: str, sample_url: str, base_cur: str = "USD") -> dict:
    """The store's OWN conversion rate per site currency, e.g. {'USD': 1.0, 'EUR': 0.8755, 'GBP': 0.7725}: the same
    currency switch a shopper makes in the header (POST /directory/currency/switch/), in a separate session so the
    main price check stays in USD. Prices on the site then match what the store shows in EUR/GBP. Cached for 20h."""
    cache = json.loads(RATES_CACHE.read_text()) if RATES_CACHE.exists() else {}
    hit = cache.get(base)
    if hit and datetime.now(UTC) - datetime.fromisoformat(hit["fetched"]) < timedelta(hours=20):
        return hit["rates"]
    sess = requests.Session()
    sess.headers.update({"User-Agent": http.USER_AGENT, "Accept-Language": "en"})
    page = sess.get(sample_url, timeout=30).text
    key = re.search(r'name="form_key"[^>]*value="([^"]+)"', page)
    usd = max(_final_prices(page), default=0)
    rates = {base_cur: 1.0}
    if key and usd:
        sess.cookies.set("form_key", key.group(1), domain=base.split("//")[1], path="/")  # set by the store's JS in a browser
        uenc = base64.urlsafe_b64encode(sample_url.encode()).decode().replace("=", ",")
        for cur in SITE_CURRENCIES:
            time.sleep(http.MIN_DELAY_SEC)
            sess.post(f"{base}/directory/currency/switch/", data={"currency": cur, "uenc": uenc, "form_key": key.group(1)},
                      timeout=30, allow_redirects=False)
            time.sleep(http.MIN_DELAY_SEC)
            local = sess.get(sample_url, timeout=30).text
            if '"currencyFormat":"' in local and max(_final_prices(local), default=0):
                rate = round(max(_final_prices(local)) / usd, 6)
                if rate != 1.0:   # a currency the store doesn't offer leaves the page in USD -> site uses ECB instead
                    rates[cur] = rate
    cache[base] = {"currency": base_cur, "rates": rates, "fetched": datetime.now(UTC).isoformat(timespec="seconds")}
    RATES_CACHE.write_text(json.dumps(cache, indent=1))
    return rates


def listing(base: str, path: str) -> list[tuple[str, str, float]]:
    """(url, name, 'as low as' price) on the category's first page: its newest products. Its further pages (?p=2 ...)
    are disallowed by Giztop's robots.txt; sitemap_pages() finds the rest."""
    return [(u, html.unescape(n), float(p)) for u, n, p in _ITEM.findall(http.get(f"{base}{path}").text)]


def slug_key(url: str) -> str:
    """A product address read like a title: '.../motorola-moto-razr-70-ultra-black-16gb-512gb.html' ->
    'motorola-razr-70-ultra-black' (storage dropped, brand spellings unified), so it can be matched to phone ids."""
    return model_id(url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".html").replace("-", " "))


def candidates(entries: list[tuple[str, str]], prefixes: set[str]) -> dict[str, str]:
    """{url: lastmod} of the product pages whose address starts with a tracked phone's id or other name and names no
    accessory or used unit: the pages worth reading. Which phone a page sells is then read from its title."""
    out = {}
    for url, lastmod in entries:
        key = slug_key(url) if url.endswith(".html") else ""
        if key and not _SLUG_SKIP.search(key.replace("-", " ")) and any(key == p or key.startswith(p + "-") for p in prefixes):
            out[url] = lastmod or ""
    return out


def sitemap_pages(store: str, cfg: dict, prefixes: set[str]) -> dict[str, str]:
    """candidates() from the store's sitemap (an index of sitemaps or one), read once a day and when the tracked phones
    change, kept in data/<store>_sitemap.json. If it can't be read, the last list is used."""
    f = Path(f"data/{store}_sitemap.json")
    saved = json.loads(f.read_text()) if f.exists() else {}
    key = hashlib.sha1("\n".join(sorted(prefixes)).encode()).hexdigest()[:12]
    if saved.get("key") == key and datetime.now(UTC) - datetime.fromisoformat(saved["fetched"]) < SITEMAP_TTL:
        return saved["urls"]
    try:
        top = http.get(cfg["sitemap_url"]).text
        subs = [html.unescape(u) for u in re.findall(r"<sitemap>\s*<loc>([^<]+)</loc>", top)]
        entries = [e for u in subs for e in _URL.findall(http.get(u).text)] if subs else _URL.findall(top)
    except Exception as e:  # noqa: BLE001 - a failed sitemap shouldn't drop the store: the last list still works
        print(f"  [{store}] warning: sitemap not read ({type(e).__name__}: {e}); using the list from {saved.get('fetched', 'no earlier run')}")
        return saved.get("urls", {})
    urls = candidates(entries, prefixes)
    f.write_text(json.dumps({"fetched": datetime.now(UTC).isoformat(timespec="seconds"), "key": key, "urls": urls},
                            indent=0, sort_keys=True))
    return urls


def split_title(name: str) -> tuple[str, str | None]:
    """'OPPO Find X9 Ultra-Black-12GB - 256GB' -> ('OPPO Find X9 Ultra', '12/256'); other titles unchanged."""
    m = _SIMPLE.match(name)
    return (m.group("base"), storage_of(m.group("storage"))) if m else (name, None)


def variants(page: str) -> list[tuple[str, float]] | None:
    """[(storage, price)] for every variant in the product page's configurable-product data, or None."""
    m = _SP_CONFIG.search(page)
    if not m:
        return None
    cfg = json.loads(m.group(1))
    attrs = list(cfg["attributes"].values())
    store_attr = next((a for a in attrs if re.search(r"storage|memory|capacity|rom", a["code"] + a["label"], re.IGNORECASE)), None)
    storage_by_product = {}
    if store_attr:
        for o in store_attr["options"]:
            for pid in o["products"]:
                storage_by_product[pid] = storage_of(o["label"])
    return [(storage_by_product.get(pid, "base"), float(p["finalPrice"]["amount"]))
            for pid, p in cfg["optionPrices"].items()]


def fetch(store: str, cfg: dict, catalog: list[dict]) -> list[Offer]:
    base = cfg["base_url"].rstrip("/")
    tracked = {p["id"] for p in catalog}
    aliases = {**{n: c["id"] for c in catalog for n in c.get("also") or []}, **(cfg.get("aliases") or {})}   # catalog `also` + store aliases
    exclude = re.compile(cfg["exclude_title"], re.IGNORECASE) if cfg.get("exclude_title") else None
    cache_file = Path(f"data/{store}_pages.json")
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    now = datetime.now(UTC)

    def phone(name: str) -> tuple[str | None, str | None]:
        """(tracked model id or None, storage the title fixes) for a listing or page title."""
        title, fixed = split_title(name)
        mid = model_id(title)
        mid = aliases.get(mid, mid)
        return (mid if mid in tracked and not (exclude and exclude.search(name)) else None), fixed

    # 1. the newest listings: their names and "as low as" prices; untracked ones go to data/untracked.txt
    todo: dict[str, tuple[str | None, float | None, str | None]] = {}   # url -> (listing name, listing price, sitemap date)
    untracked = []
    for path in cfg.get("categories", ["/phones.html"]):
        for url, name, low in listing(base, path):
            if url in todo or (exclude and exclude.search(name)):
                continue
            if phone(name)[0]:
                todo[url] = (name, low, None)
            else:
                mid = aliases.get(model_id(split_title(name)[0]), model_id(split_title(name)[0]))
                untracked.append(Offer(store=store, model_id=mid, edition=edition_of(name), storage=split_title(name)[1] or "base",
                                       title=name, price=low, currency=cfg.get("currency", "USD"), available=True, url=url))
    # 2. every other page of a tracked phone, from the sitemap; without any list yet, the pages read before
    pages = sitemap_pages(store, cfg, tracked | {a for a, t in aliases.items() if t in tracked}) if cfg.get("sitemap_url") else {}
    for url, lastmod in pages.items():
        name, low, _ = todo.get(url, (None, None, None))
        todo[url] = (name, low, lastmod)
    if not pages:
        for url in cache:
            todo.setdefault(url, (None, None, None))
    offers, keep, rates = [], set(), None
    for url, (lname, low, lastmod) in todo.items():
        hit = cache.get(url)
        stale = (not hit or "name" not in hit or (lastmod and hit.get("lastmod") != lastmod)
                 or (low is not None and hit.get("low") != low))
        if not stale and phone(hit["name"])[0]:   # a tracked phone's prices: at least every REFRESH
            stale = "variants" not in hit or now - datetime.fromisoformat(hit["fetched"]) > REFRESH
        if stale:
            try:
                page = http.get(url).text
            except http.Blocked:
                raise
            except Exception as e:  # noqa: BLE001 - one broken page shouldn't drop the whole store
                print(f"  [{store}] warning: {url}: {type(e).__name__}: {e}")
                if not hit or "name" not in hit:
                    continue
            else:
                info = parse(page) or {}
                name = html.unescape(info.get("name") or lname or "")
                hit = cache[url] = {"name": name, "lastmod": lastmod, "low": low if low is not None else info.get("price"),
                                    "fetched": now.isoformat(timespec="seconds")}
                mid, fixed = phone(name)
                if mid:   # only tracked phones' variants are kept; other pages are just remembered by title
                    hit["variants"] = variants(page) or [(fixed or storage_of(split_title(name)[0]), info.get("price", low))]
                    hit["available"] = 'class="stock unavailable"' not in page and info.get("available", True)
        keep.add(url)
        mid, fixed = phone(hit["name"])
        if not mid or "variants" not in hit:
            continue
        if rates is None:
            rates = market_rates(base, url, cfg.get("currency", "USD"))
        for storage, price in hit["variants"]:
            offers.append(Offer(store=store, model_id=mid, edition=edition_of(hit["name"]),
                                storage=fixed or storage, title=hit["name"], price=price,
                                currency=cfg.get("currency", "USD"), available=hit["available"], url=url,
                                prices={c: round(price * r, 2) for c, r in rates.items()}))
    cache_file.write_text(json.dumps({u: v for u, v in cache.items() if u in keep}, indent=0))
    # untracked models go back too, so run.py can list them in data/untracked.txt
    return cheapest_per_config(offers) + untracked
