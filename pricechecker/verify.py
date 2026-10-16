"""Spot-check what we pulled against the live store, per currency.
Usage: python -m pricechecker.verify wonda [--n 3]

For a random sample of saved offers (data/latest.json) it opens the product page the way a shopper in each
currency would (?currency=USD/EUR/GBP) and compares the page's price and active currency with ours."""
import argparse
import json
import os
import random
import re
from pathlib import Path

from . import http
from .stores.webpage import parse

_ACTIVE = re.compile(r'Shopify\.currency\s*=\s*\{"active":"([A-Z]{3})"')
_OG_AMOUNT = re.compile(r'og:price:amount"\s+content="([^"]+)"')


def _num(s: str) -> float:
    s = s.strip()
    if re.search(r",\d{2}$", s):          # European format 1.019,77
        s = s.replace(".", "").replace(",", ".")
    return float(s.replace(",", ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("store")
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args(argv)
    os.chdir(Path(__file__).resolve().parent.parent)
    st = json.loads(Path("data/latest.json").read_text())["stores"].get(args.store)
    if not st or not st["offers"]:
        print(f"no saved offers for {args.store}")
        return 1
    import yaml
    cfg = yaml.safe_load(Path("config/stores.yaml").read_text())["stores"].get(args.store, {})
    if cfg.get("type") == "shopify":   # ~1 request/min, or the store answers 429
        from .stores.shopify import _space_requests
        _space_requests(cfg["base_url"].rstrip("/"))
    sample = random.sample([o for o in st["offers"] if o["available"]] or st["offers"], min(args.n, len(st["offers"])))
    bad = 0
    for o in sample:
        print(f"\n{o['title']}\n  {o['url']}")
        ours = o.get("prices") or {o["currency"]: o["price"]}
        for cur, our_price in ours.items():
            sep = "&" if "?" in o["url"] else "?"
            html = http.get(f"{o['url']}{sep}currency={cur}").text
            active = _ACTIVE.search(html)
            m = _OG_AMOUNT.search(html)
            live = _num(m.group(1)) if m else (parse(html) or {}).get("price")
            live_cur = active.group(1) if active else (parse(html) or {}).get("currency")
            ok = live is not None and abs(live - our_price) < 0.015 and (live_cur in (None, cur))
            bad += not ok
            print(f"  {cur}: ours {our_price:>10,.2f} | store page {live if live is not None else '?':>10} {live_cur or '?':3s}  {'OK' if ok else 'MISMATCH'}")
    print(f"\n{'All prices match the live store.' if not bad else f'{bad} mismatch(es) - check the lines above.'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
