"""Payment and shipping terms per store (config/stores.yaml `terms:`), plus a daily check that the pages they
came from still say the same thing."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import fx, http

STATUS = Path("data/terms_status.json")
METHODS = {"card": "card", "paypal": "paypal", "bank": "bank_transfer"}
REGIONS = ["EU", "UK", "US", "AU", "Global"]   # Global = any other country
CURRENCIES = ["USD", "EUR", "GBP", "AUD"]


def payment_pct(cfg: dict, method: str) -> float | None:
    """Price adjustment in % for a payment method: +fee or -discount. None = unknown."""
    t = (cfg.get("terms") or {}).get("payment", {}).get(METHODS[method]) or {}
    if "discount_pct" in t:
        return None if t["discount_pct"] is None else -float(t["discount_pct"])
    return None if t.get("fee_pct") is None else float(t["fee_pct"])


def promo(cfg: dict) -> dict | None:
    """Store-wide automatic discount, e.g. {'pct': 2, 'label': 'Summer sale', 'stacks_with_bank': False, 'note': ...}."""
    p = (cfg.get("terms") or {}).get("promo")
    return {"pct": float(p["pct"]), "label": p.get("label", "Store discount"), "stacks_with_bank": bool(p.get("stacks_with_bank")),
            "note": p.get("note", "")} if p and p.get("pct") else None


def min_order_usd(cfg: dict, method: str) -> float | None:
    """Smallest order (USD) for which the store accepts this payment method, e.g. Giztop wires only over $1,500."""
    t = (cfg.get("terms") or {}).get("payment", {}).get(METHODS[method]) or {}
    return t.get("min_order_usd")


def payment_available(cfg: dict, method: str, usd: float) -> bool:
    mn = min_order_usd(cfg, method)
    return mn is None or usd >= mn


def shipping(cfg: dict, region: str, offer: dict, rates: dict) -> dict | None:
    """Shipping cost in each site currency, or None when the store doesn't list it. Uses the store's own
    exchange rate (from its prices) when the cost is in the offer's currency, else ECB."""
    t = (cfg.get("terms") or {}).get("shipping", {}).get(region) or {}
    minimum = t.get("cost") is None and t.get("cost_min") is not None   # "from EUR 10": used as a floor, marked as such
    if t.get("cost") is None and not minimum:
        return None
    cost, cur = float(t["cost_min" if minimum else "cost"]), t.get("currency", offer["currency"])
    out = {"min": 1} if minimum else {}
    for c in CURRENCIES:
        own = (offer.get("prices") or {}).get(c)
        if cur == offer["currency"] and own is not None and offer["price"]:
            out[c.lower()] = round(cost * own / offer["price"], 2)
        else:
            out[c.lower()] = round(fx.convert(cost, cur, c, rates), 2)
    return out


def delivery(cfg: dict, region: str) -> list | None:
    """Delivery time in working days from the store's shipping terms, [min, max] (min may be None: "up to 8"), or None."""
    d = ((cfg.get("terms") or {}).get("shipping", {}).get(region) or {}).get("days")
    return list(d) if d else None


def duties_included(cfg: dict, region: str) -> bool | None:
    """Does the price already include the destination's import duties and VAT/GST? None = the store doesn't say."""
    return ((cfg.get("terms") or {}).get("shipping", {}).get(region) or {}).get("duties_included")


def notes(cfg: dict) -> dict:
    t = cfg.get("terms") or {}
    return {"pay": {m: (t.get("payment", {}).get(k) or {}).get("note", "") for m, k in METHODS.items()},
            "ship": {r: (t.get("shipping", {}).get(r) or {}).get("note", "") for r in REGIONS}}


def check_pages(stores_cfg: dict, force: bool = False) -> dict:
    """Once a day: fetch each `watch` URL and confirm the expected text is still there."""
    status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    now = datetime.now(timezone.utc)
    last = status.get("_checked")
    if not force and last and now - datetime.fromisoformat(last) < timedelta(hours=20):
        return status
    for name, cfg in stores_cfg.items():
        watch = (cfg.get("terms") or {}).get("watch") or []
        if not cfg.get("enabled", True) or not watch:
            continue
        problems = []
        if cfg.get("type") == "shopify":
            from .stores.shopify import _space_requests
            _space_requests(cfg["base_url"].rstrip("/"))
        for w in watch:
            try:
                text = re.sub(r"<[^>]+>", " ", http.get(w["url"]).text)
                if not re.search(w["expect"], text, re.I):
                    problems.append(f"'{w['expect']}' no longer on {w['url']}")
            except Exception as e:
                problems.append(f"could not read {w['url']}: {type(e).__name__}")
        status[name] = {"ok": not problems, "problems": problems, "checked": now.isoformat(timespec="seconds")}
        print(f"  [terms] {name}: {'unchanged' if not problems else 'NEEDS REVIEW - ' + '; '.join(problems)}")
    status["_checked"] = now.isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(status, indent=1))
    return status
