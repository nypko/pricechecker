"""/stores and one page per store with published terms: stores/<name>.html."""
import json
from pathlib import Path

from jinja2 import Environment

from ... import fx, promos, terms
from ..common import SYMBOL
from ..context import SiteData
from ..data_files import offer_inputs
from ..view import DEFAULT, best_of
from ..view import rows as view_rows

REGION_CUR = {"EU": "EUR", "UK": "GBP", "US": "USD", "CA": "CAD", "AU": "AUD", "Global": "USD"}   # shipping shown in each region's currency
REGION_LABEL = {"EU": "EU", "UK": "UK", "US": "US", "CA": "Canada", "AU": "Australia", "Global": "Rest of world"}


def _ship_cell(cfg: dict, region: str, rates: dict) -> dict:
    """One store's shipping terms for a region, for the store pages: cost in the region's currency, days, who pays tax."""
    t = ((cfg.get("terms") or {}).get("shipping", {}).get(region)) or {}
    cur, to = t.get("currency", cfg.get("currency", "USD")), REGION_CUR[region]
    amount = t["cost"] if t.get("cost") is not None else t.get("cost_min")
    if t.get("ships") is False:
        return {"region": region, "label": REGION_LABEL[region], "cost": "doesn't deliver", "days": None,
                "duties": None, "ships": False, "note": t.get("note", "")}
    if amount is None:
        cost = "not listed"
    elif float(amount) == 0:
        cost = "free"
    else:
        v = fx.convert(float(amount), cur, to, rates)
        cost = ("from " if t.get("cost") is None else "") + ("" if cur == to else "≈") + f"{SYMBOL[to]}{v:,.2f}".replace(".00", "")
    d = t.get("days")
    days = None if not d else (f"up to {d[1]}" if d[0] is None else f"{d[0]}–{d[1]}") + " working days"
    return {"region": region, "label": REGION_LABEL[region], "cost": cost, "days": days,
            "duties": t.get("duties_included"), "ships": True, "note": t.get("note", "")}


FAST_DAYS = 10   # the "Within 10 days" chip: delivery to the EU takes at most this many working days
CHIPS = (("tax", "Import tax paid"), ("free", "Free shipping"), ("fast", f"Within {FAST_DAYS} days"), ("paypal", "Takes PayPal"))


def _parts(stores_cfg: dict, name: str) -> list[dict]:
    """A store's config plus its enabled EU-warehouse sections: a store qualifies for a chip if any of them does."""
    return [stores_cfg[name]] + [c for n, c in stores_cfg.items() if c.get("part_of") == name and c.get("enabled", True)]


def delivery_flags(stores_cfg: dict, name: str) -> dict:
    """What the list page's chips count for one store, from its stores.yaml terms for delivery to the EU: import tax
    already paid, free shipping, delivered within FAST_DAYS working days, takes PayPal."""
    ship = [((c.get("terms") or {}).get("shipping") or {}).get("EU") or {} for c in _parts(stores_cfg, name)]
    return {"tax": any(t.get("duties_included") is True for t in ship),
            "free": any(t.get("cost") == 0 for t in ship),
            "fast": any(t.get("days") and t["days"][1] <= FAST_DAYS for t in ship),
            "paypal": any(terms.payment_pct(c, "paypal") is not None for c in _parts(stores_cfg, name))}


def delivery_counts(stores_cfg: dict, names: list[str]) -> dict:
    """How many of the stores each chip keeps (the number printed on the chip)."""
    flags = [delivery_flags(stores_cfg, n) for n in names]
    return {k: sum(f[k] for f in flags) for k, _ in CHIPS}


def _pay_text(pct: float | None) -> str:
    if pct is None:
        return "fee not published"
    return f"{-pct:g}% discount" if pct < 0 else f"{pct:g}% fee" if pct > 0 else "no fee"


def _tax_line(ship: list[dict]) -> str:
    """Who pays import tax, by region: 'included in the EU, UK; you pay on delivery in the US'."""
    groups = {"included": [], "you pay on delivery": [], "not stated": []}
    for c in ship:
        if c["ships"]:
            groups["included" if c["duties"] else "you pay on delivery" if c["duties"] is False else "not stated"].append(c["label"])
    return "; ".join(f"{k} in {', '.join(v)}" for k, v in groups.items() if v)


def _clean_promo(line: str) -> str:
    """The banner text the daily scan kept, minus stray markup left from the page (a leading '> ' or a trailing '\">')."""
    return line.strip().lstrip("> ").rstrip('"> ').strip()


def _promos(name: str, cfg: dict, state: dict) -> list[str]:
    """What the store advertises now: its configured store-wide discount while it runs, coupon hints, and the banner
    lines from the last daily scan (repeats merged)."""
    out = []
    p = terms.promo(cfg) if promos.active(name, cfg, state) else None
    if p:
        out.append(f"{p['label']}: {p['pct']:g}% off" + (f" ({p['note']})" if p["note"] else ""))
    out += [f"Coupon {c['code']}" + (f": {c['text']}" if c["text"] else "") + (f" (until {c['until']})" if c["until"] else "")
            for c in promos.coupons(name, cfg, state)]
    seen = {x.lower() for x in out}
    for line in (state.get(name) or {}).get("current") or []:
        t = _clean_promo(line)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def _sources(cfg: dict, snaps: dict) -> dict:
    """The store pages its terms came from (stores.yaml watch + pages) with when each was last read, and the date its
    wording last changed (the latest change among them; none recorded yet is shown as such)."""
    t = cfg.get("terms") or {}
    urls = list(dict.fromkeys([w["url"] for w in t.get("watch") or []] + list(t.get("pages") or [])))
    rows = [{"url": u, "checked": (snaps.get(u) or {}).get("checked", "")[:10], "changed": (snaps.get(u) or {}).get("changed", "")[:10]} for u in urls]
    return {"pages": rows, "read": max((r["checked"] for r in rows), default=""), "changed": max((r["changed"] for r in rows), default="")}


def _has_page(cfg: dict) -> bool:
    """A store gets its own page when it is enabled, not an EU-warehouse section of another, and publishes terms."""
    return bool(cfg.get("enabled", True) and not cfg.get("part_of") and (cfg.get("terms") or {}).get("shipping"))


def page_names(stores_cfg: dict) -> list[str]:
    """The stores with a page, in stores.yaml order (the names _store_pages makes pages for)."""
    return [name for name, cfg in stores_cfg.items() if _has_page(cfg)]


def _cheapest_for(phones: list[dict], labels: set[str], tax_cfg: dict) -> list[dict]:
    """The phone versions this store (or its EU-warehouse section) has the best current, payable delivered total on
    for the default settings (the EU, card, euro): the one view-model rule the phone pages use."""
    out = []
    for p in phones:
        rows = view_rows([offer_inputs(o) for o in p["offers"]], tax_cfg, DEFAULT)
        for e in p["editions"]:
            b = best_of(rows, e)
            if b and b["store"] in labels:
                out.append({"name": p["name"], "slug": p["slug"], "edition": e, "ed_label": p["ed_label"], "storage": b["storage"],
                            "total": b["total"], "store": b["store"]})
    return sorted(out, key=lambda x: (x["name"], x["edition"]))


def _store_pages(phones: list[dict], stores_cfg: dict, rates: dict, buyers: dict, tax_cfg: dict | None = None,
                 promo_state: dict | None = None, term_snaps: dict | None = None) -> list[dict]:
    """One page per store with published terms (an EU warehouse is shown on its store's page): trust, terms per Ship-to
    region, payment fees, and every phone it lists with its lowest price against the cheapest store's."""
    pages = []
    for name, cfg in stores_cfg.items():
        if not _has_page(cfg):
            continue
        parts = [name] + [n for n, c in stores_cfg.items() if c.get("part_of") == name and c.get("enabled", True)]
        listed = []
        for p in phones:
            mine = [o for o in p["offers"] if o["store"] in parts and o["available"] and not o["old"]]
            if not mine:
                continue
            best = min(mine, key=lambda o: o["usd"])
            low = min(o["usd"] for o in p["offers"] if o["available"] and not o["old"])
            listed.append({"name": p["name"], "slug": p["slug"], "money": best["money"], "storage": best["storage"],
                           "edition": best["edition"], "ed_label": p["ed_label"], "cheapest": best["usd"] <= low + 0.5,
                           "gap_pct": round((best["usd"] / low - 1) * 100) if low else 0, "n": len(mine)})
        listed.sort(key=lambda x: x["name"])
        extra = [{"label": stores_cfg[n].get("label", n), "ship": [_ship_cell(stores_cfg[n], r, rates) for r in terms.REGIONS]}
                 for n in parts[1:]]
        ship = [_ship_cell(cfg, r, rates) for r in terms.REGIONS]
        labels = {stores_cfg[n].get("label", n) for n in parts}
        pages.append({"name": name, "label": cfg.get("label", name), "currency": cfg.get("currency"),
                      "flags": delivery_flags(stores_cfg, name), "tax_line": _tax_line(ship),
                      "served": [c["label"] for c in ship if c["ships"]],
                      "not_served": [c["label"] for c in ship if not c["ships"]],
                      "promos": _promos(name, cfg, promo_state or {}), "sources": _sources(cfg, term_snaps or {}),
                      "cheapest_for": _cheapest_for(phones, labels, tax_cfg) if tax_cfg else [],
                      "trust": cfg.get("trust") or {}, "google_play": cfg.get("google_play"),
                      "ship": ship, "extra": extra,
                      "pay": [{"method": {"card": "Card", "paypal": "PayPal", "bank": "Bank transfer"}[m], "pct": terms.payment_pct(cfg, m),
                               "text": _pay_text(terms.payment_pct(cfg, m)),
                               "note": terms.notes(cfg)["pay"][m]} for m in terms.METHODS],
                      "buyers": buyers.get(name) or {}, "phones": listed,
                      "n_cheapest": sum(x["cheapest"] for x in listed)})
    return pages


def _saved(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    store_pages = _store_pages(phones, data.stores_cfg, data.rates, data.buyers, data.tax_cfg, _saved(promos.STATE), _saved(terms.PAGES))
    counts = delivery_counts(data.stores_cfg, [sp["name"] for sp in store_pages])
    out = {"stores.html": env.get_template("stores.html").render(root="", path="stores", store_pages=store_pages, chips=CHIPS, counts=counts, **ctx)}
    for sp in store_pages:
        out[f'stores/{sp["name"]}.html'] = env.get_template("store.html").render(root="../", path=f'stores/{sp["name"]}', sp=sp, **ctx)
    return out
