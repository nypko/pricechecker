"""Generic product-page reader for stores without a feed: reads schema.org JSON-LD, then price meta tags.
Which pages to read comes from config/catalog.yaml (one URL per phone per store)."""
import json
import re

from .. import http
from ..models import Offer, StoreNotConfigured
from ..normalize import storage_of

_LD = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_META_PRICE = [
    re.compile(r'<meta[^>]+property="product:price:amount"[^>]+content="([0-9.,]+)"', re.I),
    re.compile(r'itemprop="price"[^>]+content="([0-9.,]+)"', re.I),
]
_META_CUR = re.compile(r'<meta[^>]+property="product:price:currency"[^>]+content="([A-Z]{3})"', re.I)


def parse(html: str) -> dict | None:
    """Returns {'name', 'price', 'currency', 'available'} from a product page, or None."""
    for m in _LD.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        for item in (data if isinstance(data, list) else data.get("@graph", [data])):
            if isinstance(item, dict) and "Product" in str(item.get("@type")):
                o = item.get("offers") or {}
                o = o[0] if isinstance(o, list) else o
                price = o.get("price") or o.get("lowPrice")
                if price:
                    return {"name": item.get("name", ""), "price": float(str(price).replace(",", "")),
                            "currency": o.get("priceCurrency"), "available": "InStock" in str(o.get("availability", "InStock"))}
    for pat in _META_PRICE:
        m = pat.search(html)
        if m:
            cur = _META_CUR.search(html)
            name = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
            return {"name": name.group(1) if name else "", "price": float(m.group(1).replace(",", "")),
                    "currency": cur.group(1) if cur else None, "available": "out of stock" not in html.lower()[:200000]}
    return None


def fetch(store: str, cfg: dict, catalog: list[dict]) -> list[Offer]:
    targets = [(phone, phone["offers"][store]) for phone in catalog if store in phone.get("offers", {})]
    if not targets:
        raise StoreNotConfigured(f"no product URLs for '{store}' in config/catalog.yaml")
    offers, errors = [], []
    for phone, entry in targets:
        url, storage = (entry, None) if isinstance(entry, str) else (entry["url"], entry.get("storage"))
        try:
            info = parse(http.get(url).text)
        except http.Blocked:
            raise
        except Exception as e:  # one broken page shouldn't drop the whole store
            errors.append(f"{url}: {e}")
            continue
        if not info:
            errors.append(f"{url}: no price found on page")
            continue
        offers.append(Offer(store=store, model_id=phone["id"], edition=phone.get("edition", "china"),
                            storage=storage or storage_of(info["name"]), title=info["name"] or phone["name"],
                            price=info["price"], currency=info["currency"] or cfg.get("currency", "USD"),
                            available=info["available"], url=url))
    if errors and not offers:
        raise RuntimeError("; ".join(errors))
    for e in errors:
        print(f"  [{store}] warning: {e}")
    return offers
