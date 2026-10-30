"""Payment and shipping terms per store (config/stores.yaml `terms:`), plus a daily check of the pages they came from:
  - `watch`: a phrase each page must still contain (else the store shows "terms changed" until reviewed)
  - every watched page and the extra `pages` (customs, shipping, payment, returns) is kept as text in
    data/terms_pages.json; when a page's wording changes, the change is written to .terms_report.md, which the workflow
    files as a GitHub issue. Nothing is applied automatically: store wording needs a person to turn it into terms."""
import difflib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import fx, http
from .issue_text import fence

STATUS = Path("data/terms_status.json")
PAGES = Path("data/terms_pages.json")
REPORT = Path(".terms_report.md")   # filed as a GitHub issue by the workflow; not committed
METHODS = {"card": "card", "paypal": "paypal", "bank": "bank_transfer"}
REGIONS = ["EU", "UK", "US", "CA", "AU", "Global"]   # Global = any other country
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]


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


def shipping(cfg: dict, region: str, offer: dict, rates: dict) -> dict | None | bool:
    """Shipping cost in each site currency, None when the store doesn't list it, False when it doesn't deliver there
    (`ships: false`: the page leaves its offers out for that region). Uses the store's own
    exchange rate (from its prices) when the cost is in the offer's currency, else ECB."""
    t = (cfg.get("terms") or {}).get("shipping", {}).get(region) or {}
    if t.get("ships") is False:
        return False
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


def policy_lines(html: str) -> list[str]:
    """The wording of a terms page: the <main> part where there is one (no menus, footers or carts), as lines of
    four or more words, so a changed price in a product carousel or a cart counter isn't reported as a new policy."""
    from .promos import text_of
    m = re.search(r"(?is)<main\b.*?</main>", html)
    return [ln for ln in text_of(m.group(0) if m else html) if len(ln.split()) >= 4]


def page_diff(old: list[str], new: list[str], limit: int = 40) -> list[str]:
    """Removed (-) and added (+) lines, at most `limit`."""
    out = [ln for ln in difflib.unified_diff(old, new, lineterm="", n=0) if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
    return out[:limit] + ([f"... {len(out) - limit} more changed lines"] if len(out) > limit else [])


def snapshot(old: dict | None, lines: list[str], now: datetime) -> dict:
    """A terms page's saved record after a read: its lines, when it was read, and (store pages show it as "Terms last
    changed") when its wording last differed from the read before. First sight is not a change."""
    out = {"lines": lines, "checked": now.isoformat(timespec="seconds")}
    changed = now.isoformat(timespec="seconds") if old is not None and old["lines"] != lines else (old or {}).get("changed")
    if changed:
        out["changed"] = changed
    return out


def saved_status() -> dict:
    """The last daily terms check as saved, without reading any store page (offline builds)."""
    return json.loads(STATUS.read_text()) if STATUS.exists() else {}


def check_pages(stores_cfg: dict, force: bool = False) -> dict:
    """Once a day: fetch each store's terms pages, confirm each `watch` phrase is still there, and report any
    change in a page's wording since the last check (first sight: recorded only)."""
    status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    snaps = json.loads(PAGES.read_text()) if PAGES.exists() else {}
    now = datetime.now(UTC)
    last = status.get("_checked")
    if not force and last and now - datetime.fromisoformat(last) < timedelta(hours=20):
        return status
    report = []
    for name, cfg in stores_cfg.items():
        t = cfg.get("terms") or {}
        watch = t.get("watch") or []
        urls = list(dict.fromkeys([w["url"] for w in watch] + list(t.get("pages") or [])))
        if not cfg.get("enabled", True) or not urls:
            continue
        problems, texts = [], {}
        if cfg.get("type") == "shopify":
            from .stores.shopify import _space_requests
            _space_requests(cfg["base_url"].rstrip("/"))
        for u in urls:   # each page once, even when several phrases are watched on it
            try:
                texts[u] = http.get(u).text
            except Exception as e:  # noqa: BLE001
                problems.append(f"could not read {u}: {type(e).__name__}")
        for w in watch:
            if w["url"] in texts and not re.search(w["expect"], re.sub(r"<[^>]+>", " ", texts[w["url"]]), re.IGNORECASE):
                problems.append(f"'{w['expect']}' no longer on {w['url']}")
        for u, html in texts.items():
            lines, old = policy_lines(html), snaps.get(u)
            if old is not None and old["lines"] != lines:
                diff = page_diff(old["lines"], lines)
                if diff:
                    report += [f"**{cfg.get('label', name)}**: {u} (last read {old['checked'][:10]})", "", *fence(diff, "diff"), ""]
            snaps[u] = snapshot(old, lines, now)
        status[name] = {"ok": not problems, "problems": problems, "checked": now.isoformat(timespec="seconds")}
        print(f"  [terms] {name}: {'unchanged' if not problems else 'NEEDS REVIEW - ' + '; '.join(problems)}")
    status["_checked"] = now.isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(status, indent=1))
    PAGES.write_text(json.dumps(snaps, indent=0, ensure_ascii=False))
    if report:
        REPORT.write_text("A store changed the wording of a terms page (customs, shipping, payment or returns). Check whether "
                          "`config/stores.yaml` still matches, then close this issue.\n\n" + "\n".join(report) + "\n")
        print(f"  [terms] wording changed on {sum(1 for x in report if x.startswith('**'))} page(s): see the GitHub issue")
    return status
