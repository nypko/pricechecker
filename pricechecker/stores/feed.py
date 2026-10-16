"""Affiliate product feeds (CSV or Google-Merchant-style XML) - the preferred source for stores that block
scripts (e.g. Trading Shenzhen). Ask your affiliate manager / network for the feed URL and set it in config/stores.yaml."""
import csv
import io
import os
import xml.etree.ElementTree as ET

from .. import http
from ..models import Offer, StoreNotConfigured
from ..normalize import edition_of, model_id, storage_of

DEFAULT_FIELDS = {"title": "title", "link": "link", "price": "price", "availability": "availability"}


def _rows(text: str, fmt: str):
    if fmt == "csv":
        sample = text[:5000]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        yield from csv.DictReader(io.StringIO(text), dialect=dialect)
    else:
        root = ET.fromstring(text.encode())
        for item in root.iter():
            if item.tag.split("}")[-1] in ("item", "entry", "product"):
                yield {child.tag.split("}")[-1]: (child.text or "").strip() for child in item}


def _price(raw: str, default_cur: str) -> tuple[float, str]:
    parts = raw.replace(",", "").split()
    nums = [p for p in parts if p.replace(".", "", 1).isdigit()]
    curs = [p for p in parts if len(p) == 3 and p.isalpha()]
    return float(nums[0]), (curs[0].upper() if curs else default_cur)


def fetch(store: str, cfg: dict) -> list[Offer]:
    url = os.environ.get(cfg.get("feed_url_env", ""), "") or cfg.get("feed_url", "")
    if not url:
        raise StoreNotConfigured(f"set feed_url (or env {cfg.get('feed_url_env')}) for '{store}' - get it from your affiliate account")
    f = {**DEFAULT_FIELDS, **cfg.get("feed_fields", {})}
    text = http.get(url, respect_robots=False).text   # a feed given to us by the merchant, not a crawl
    offers = []
    for row in _rows(text, cfg.get("feed_format", "xml")):
        title = row.get(f["title"], "")
        if not title or not any(k in title.lower() for k in cfg.get("title_must_contain", [""])):
            continue
        price, cur = _price(row.get(f["price"], "0"), cfg.get("currency", "USD"))
        offers.append(Offer(store=store, model_id=model_id(title), edition=edition_of(title), storage=storage_of(title),
                            title=title, price=price, currency=cur,
                            available="in" in row.get(f["availability"], "in stock").lower(), url=row.get(f["link"], "")))
    return offers
