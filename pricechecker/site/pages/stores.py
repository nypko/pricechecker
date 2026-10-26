"""/stores and one page per store with published terms: stores/<name>.html."""
from jinja2 import Environment

from ... import fx, terms
from ..common import SYMBOL
from ..context import SiteData

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


def _has_page(cfg: dict) -> bool:
    """A store gets its own page when it is enabled, not an EU-warehouse section of another, and publishes terms."""
    return bool(cfg.get("enabled", True) and not cfg.get("part_of") and (cfg.get("terms") or {}).get("shipping"))


def page_names(stores_cfg: dict) -> list[str]:
    """The stores with a page, in stores.yaml order (the names _store_pages makes pages for)."""
    return [name for name, cfg in stores_cfg.items() if _has_page(cfg)]


def _store_pages(phones: list[dict], stores_cfg: dict, rates: dict, buyers: dict) -> list[dict]:
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
        pages.append({"name": name, "label": cfg.get("label", name), "currency": cfg.get("currency"),
                      "trust": cfg.get("trust") or {}, "google_play": cfg.get("google_play"),
                      "ship": [_ship_cell(cfg, r, rates) for r in terms.REGIONS], "extra": extra,
                      "pay": [{"method": {"card": "Card", "paypal": "PayPal", "bank": "Bank transfer"}[m], "pct": terms.payment_pct(cfg, m),
                               "note": terms.notes(cfg)["pay"][m]} for m in terms.METHODS],
                      "buyers": buyers.get(name) or {}, "phones": listed,
                      "n_cheapest": sum(x["cheapest"] for x in listed)})
    return pages


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    store_pages = _store_pages(phones, data.stores_cfg, data.rates, data.buyers)
    out = {"stores.html": env.get_template("stores.html").render(root="", path="stores", store_pages=store_pages, **ctx)}
    for sp in store_pages:
        out[f'stores/{sp["name"]}.html'] = env.get_template("store.html").render(root="../", path=f'stores/{sp["name"]}', sp=sp, **ctx)
    return out
