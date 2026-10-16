"""Magento 2 stores (e.g. Giztop): walk the phone category pages (allowed by robots.txt via ?p=), then read the
per-variant prices (storage x color) from each tracked phone's product page.
Product pages are cached and only re-read when the category's "as low as" price changes, or every few hours."""
import base64
import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from .. import http
from ..models import Offer
from ..normalize import edition_of, model_id, storage_of
from .shopify import cheapest_per_config
from .webpage import parse

_ITEM = re.compile(r'class="product-item-link"\s+href="([^"]+)">\s*([^<]+?)\s*</a>.*?data-price-amount="([0-9.]+)"', re.S)
_COUNT = re.compile(r'toolbar-number">(\d+)</span>')
_SP_CONFIG = re.compile(r'"spConfig":\s*(\{.*?\})\s*,\s*"gallerySwitchStrategy"', re.S)
# single-variant listings: "OPPO Find X9 Ultra-Black-12GB - 256GB"
_SIMPLE = re.compile(r"^(?P<base>.+?)-(?P<color>[^-]+)-(?P<storage>\d+\s*GB\s*-\s*\d+\s*(?:GB|TB))$", re.I)
PER_PAGE = 24
REFRESH = timedelta(hours=6)
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
    if hit and datetime.now(timezone.utc) - datetime.fromisoformat(hit["fetched"]) < timedelta(hours=20):
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
            if f'"currencyFormat":"' in local and max(_final_prices(local), default=0):
                rate = round(max(_final_prices(local)) / usd, 6)
                if rate != 1.0:   # a currency the store doesn't offer leaves the page in USD -> site uses ECB instead
                    rates[cur] = rate
    cache[base] = {"currency": base_cur, "rates": rates, "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    RATES_CACHE.write_text(json.dumps(cache, indent=1))
    return rates


def listing(base: str, path: str) -> list[tuple[str, str, float]]:
    """(url, name, 'as low as' price) for every product in a category, across all its pages."""
    items, page, total = [], 1, None
    while True:
        s = http.get(f"{base}{path}" + (f"?p={page}" if page > 1 else "")).text
        found = [(u, html.unescape(n), float(p)) for u, n, p in _ITEM.findall(s)]
        items += found
        if total is None:
            counts = _COUNT.findall(s)
            total = int(counts[2]) if len(counts) > 2 else len(found)
        if not found or len(items) >= total or page >= 50:
            return items
        page += 1


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
    store_attr = next((a for a in attrs if re.search(r"storage|memory|capacity|rom", a["code"] + a["label"], re.I)), None)
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
    aliases = cfg.get("aliases") or {}
    exclude = re.compile(cfg["exclude_title"], re.I) if cfg.get("exclude_title") else None
    cache_file = Path(f"data/{store}_pages.json")
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    now = datetime.now(timezone.utc)
    seen, offers, untracked = set(), [], []
    rates = None
    for path in cfg.get("categories", ["/phones.html"]):
        for url, name, low in listing(base, path):
            if url in seen or (exclude and exclude.search(name)):
                continue
            seen.add(url)
            title, fixed_storage = split_title(name)
            mid = model_id(title)
            mid = aliases.get(mid, mid)
            if mid not in tracked:
                untracked.append(Offer(store=store, model_id=mid, edition=edition_of(name), storage=fixed_storage or "base",
                                       title=name, price=low, currency=cfg.get("currency", "USD"), available=True, url=url))
                continue
            hit = cache.get(url)
            if not hit or hit["low"] != low or now - datetime.fromisoformat(hit["fetched"]) > REFRESH:
                page = http.get(url).text
                info = parse(page) or {}
                vs = variants(page) or [(fixed_storage or storage_of(title), info.get("price", low))]
                in_stock = 'class="stock unavailable"' not in page and info.get("available", True)
                hit = cache[url] = {"low": low, "fetched": now.isoformat(timespec="seconds"),
                                    "variants": vs, "available": in_stock}
            if rates is None:
                rates = market_rates(base, url, cfg.get("currency", "USD"))
            for storage, price in hit["variants"]:
                offers.append(Offer(store=store, model_id=mid, edition=edition_of(name),
                                    storage=fixed_storage or storage, title=name, price=price,
                                    currency=cfg.get("currency", "USD"), available=hit["available"], url=url,
                                    prices={c: round(price * r, 2) for c, r in rates.items()}))
    cache_file.write_text(json.dumps({u: v for u, v in cache.items() if u in seen}, indent=0))
    # untracked models go back too, so run.py can list them in data/untracked.txt
    return cheapest_per_config(offers) + untracked
