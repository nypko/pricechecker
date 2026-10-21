"""Shopify stores (e.g. Wonda Mobile, The Mobile Marvel): the public /products.json feed lists every product,
variant and price."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import http
from ..models import Offer
from ..normalize import edition_of, model_id, storage_of


_ACTIVE = re.compile(r'Shopify\.currency\s*=\s*\{"active":"([A-Z]{3})","rate":"([0-9.]+)"\}')
SITE_CURRENCIES = ["USD", "EUR", "GBP", "AUD"]


RATES_CACHE = Path("data/shop_rates.json")
REQUEST_SPACING_SEC = 75  # Shopify allows ~1 storefront request/min per IP, shared by all Shopify shops (grouped in http.py)


def _space_requests(base: str) -> None:
    host = base.split("//", 1)[1]
    http.HOST_DELAY[host] = REQUEST_SPACING_SEC
    http.HOST_GROUP[host] = "shopify"


def market_rates(base: str) -> tuple[str, dict]:
    """The shop's base currency (meta.json) and its OWN conversion rate for each site currency, read the same way
    a shopper's browser gets it (?currency=XXX). e.g. ('USD', {'USD': 1.0, 'EUR': 0.903254, 'GBP': 0.762941}).
    Cached for 7 days: shown prices come from the per-currency feeds; these rates only say which currencies the
    shop sells in (and convert a variant missing from a feed). Every saved request helps with the rate limit."""
    cache = json.loads(RATES_CACHE.read_text()) if RATES_CACHE.exists() else {}
    hit = cache.get(base)
    if hit and set(SITE_CURRENCIES) <= set(hit.get("checked", hit["rates"])) and \
            datetime.now(timezone.utc) - datetime.fromisoformat(hit["fetched"]) < timedelta(days=7):
        return hit["currency"], hit["rates"]
    shop_cur = http.get(f"{base}/meta.json").json()["currency"]
    rates = {shop_cur: 1.0}
    for cur in SITE_CURRENCIES:
        if cur in rates:
            continue
        m = _ACTIVE.search(http.get(f"{base}/policies/terms-of-service", params={"currency": cur}).text)
        if m and m.group(1) == cur:  # the shop really offers this currency (otherwise the site converts via ECB)
            rates[cur] = float(m.group(2))
    cache[base] = {"currency": shop_cur, "rates": rates, "checked": [shop_cur] + SITE_CURRENCIES,
                   "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    RATES_CACHE.write_text(json.dumps(cache, indent=1))
    return shop_cur, rates


def _feed(base: str, currency: str) -> list[dict]:
    """Every product in /products.json, priced in `currency`. Without ?currency= Shopify Markets answers in the
    currency of the visitor's country (e.g. EUR for an EU IP), so the currency is always asked for explicitly."""
    products = []
    for page in range(1, 21):
        batch = http.get(f"{base}/products.json", params={"limit": 250, "page": page, "currency": currency}).json()["products"]
        products += batch
        if len(batch) < 250:  # last page; Shopify rate-limits this endpoint, so don't ask for an empty one
            break
    return products


def fetch(store: str, cfg: dict) -> list[Offer]:
    base = cfg["base_url"].rstrip("/")
    _space_requests(base)
    shop_cur, rates = market_rates(base)
    if cfg.get("currency") and cfg["currency"] != shop_cur:
        print(f"  [{store}] NOTE: config says {cfg['currency']} but the shop's base currency is {shop_cur} - using {shop_cur}")
    # the shop's own price in every site currency it sells in (exact, incl. its .95-style rounding);
    # USD (or the shop currency) is the one recorded in history
    currencies = [c for c in SITE_CURRENCIES if c in rates] or [shop_cur]
    main_cur = "USD" if "USD" in currencies else currencies[0]
    currencies.sort(key=lambda c: c != main_cur)
    feeds = {c: _feed(base, c) for c in currencies}
    local = {c: {v["id"]: float(v["price"]) for p in prods for v in p["variants"]} for c, prods in feeds.items()}
    types = {t.lower() for t in cfg.get("product_types", [])}       # empty = don't filter by type
    exclude = re.compile(cfg["exclude_title"], re.I) if cfg.get("exclude_title") else None
    offers: list[Offer] = []
    for p in feeds[main_cur]:
        if types and p.get("product_type", "").lower() not in types:
            continue
        if exclude and exclude.search(p["title"]):
            continue
        mid, ed = model_id(p["title"]), edition_of(p["title"])
        # the storage option is "Size" at Wonda (1st), "Ram+Storage" at Mobile Marvel (2nd)
        names = [o["name"].lower() for o in p.get("options", [])]
        opt = next((i + 1 for i, n in enumerate(names) if re.search(r"size|storage|ram|capacity|memory", n)), 1)
        for v in p["variants"]:
            price = float(v["price"])
            # a variant can say more than the product: "(GLOBAL)" product, "16GB/1TB (China Version)" variant
            v_ed = edition_of(f'{p["title"]} - {v.get("title", "")}') if ed == "global" else ed
            offers.append(Offer(
                store=store, model_id=mid, edition=v_ed,
                storage=storage_of(v.get(f"option{opt}") or v.get("title", "")),
                title=f'{p["title"]} - {v.get("title", "")}',
                price=price, currency=main_cur,
                available=bool(v.get("available")),
                url=f'{base}/products/{p["handle"]}?variant={v["id"]}',
                prices={c: local[c].get(v["id"], round(price / rates[main_cur] * rates[c], 2)) for c in currencies},
            ))
    return cheapest_per_config(offers)


def cheapest_per_config(offers: list[Offer]) -> list[Offer]:
    """Colors share a price slot: keep the cheapest available variant per (model, edition, storage)."""
    best: dict[tuple, Offer] = {}
    for o in offers:
        cur = best.get(o.key)
        if cur is None or (o.available, -o.price) > (cur.available, -cur.price):
            best[o.key] = o
    return list(best.values())
