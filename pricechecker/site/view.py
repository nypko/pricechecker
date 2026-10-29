"""The one view model every page renders from: offer inputs + the visitor's settings -> display rows.
static/js/view.js is its line-for-line mirror; rows are plain dicts with the same camelCase keys on both sides so the
server templates and the browser blocks show identical numbers. No I/O."""
from .. import pricing
from ..pricing import Settings

DEFAULT = Settings("EU", "", "card", "eur")


def _tail(c: pricing.Cost, unknown: int) -> str:
    if c.ship is None:
        return "+ shipping, tax?" if c.duties is None else "+ shipping"
    return "+ tax?" if unknown else ""


def _row(o: dict, c: pricing.Cost, s: Settings, state: str, tax_name: str) -> dict:
    unknown = pricing.unknowns(c)
    days = (o.get("days") or {}).get(s.region)
    return {
        "store": o.get("store_label"), "edition": o.get("edition"), "storage": o.get("storage"), "link": o.get("link"),
        "days": list(days) if days else None, "trust": o.get("trust"),
        "promoLabel": (o.get("promo") or {}).get("label"),
        "list": c.list, "promoAmt": c.promo_amt, "promoPct": c.promo_pct, "base": c.base, "adj": c.adj,
        "adjAmt": c.adj_amt, "ship": c.ship, "shipMin": c.ship_min, "taxEst": c.tax_est, "taxAdded": c.tax_added,
        "duties": c.duties, "total": c.total, "approx": c.approx, "unknown": unknown,
        "left": pricing.left_out(c), "tail": _tail(c, unknown), "settled": unknown == 0,
        "payOk": c.pay_ok, "old": c.old, "available": bool(o.get("available")),
        "delivers": (o.get("ship") or {}).get(s.region) is not False, "state": state,
        "checked": o.get("checked"), "taxName": tax_name,   # when the store's prices were read (ISO, UTC); the tax's name
    }


def _state(o: dict, c: pricing.Cost, s: Settings) -> str:
    if not o.get("available"):
        return "soldout"
    if (o.get("ship") or {}).get(s.region) is False:
        return "nodelivery"
    if c.old:
        return "stale"
    return "ok" if c.pay_ok else "nopay"


def rows(inputs: list[dict], tax_cfg: dict, s: Settings) -> list[dict]:
    """Every offer as a row, in the one order every store list shows: priced rows in pricing.better order (offers whose
    RAM/storage the store doesn't list included, as the page title does) except that stale rows come after all the
    others, then stores that don't deliver, then sold out."""
    rule = pricing.tax_rule(tax_cfg, s)
    ranked = pricing.rank(inputs, s, rule, with_base=True)
    ids = {id(o) for o, _ in ranked}
    priced = [_row(o, c, s, _state(o, c, s), rule.name) for o, c in ranked]
    out = [r for r in priced if r["state"] != "stale"] + [r for r in priced if r["state"] == "stale"]
    rest = [(o, pricing.cost(o, s, rule)) for o in inputs if id(o) not in ids]
    for want in ("nodelivery", "soldout"):
        out += [_row(o, c, s, want, rule.name) for o, c in rest if _state(o, c, s) == want]
    return out


def best_of(rows: list[dict], edition: str, storage: str | None = None) -> dict | None:
    """The first (best) current, payable row of the edition; with storage, only that storage (exact match)."""
    return next((r for r in rows if r["state"] == "ok" and r["edition"] == edition
                 and (storage is None or r["storage"] == storage)), None)


def gap(rows: list[dict]) -> dict | None:
    """China vs Global at the same RAM/storage: settled totals of ok rows only; the storage where China is cheapest
    among those both editions have. Same rule as derive.gap, over rows."""
    best: dict[tuple, float] = {}
    for r in rows:
        if r["state"] != "ok" or r["storage"] == "base" or not r["settled"]:
            continue
        k = (r["storage"], r["edition"])
        best[k] = min(r["total"], best.get(k, r["total"]))
    tiers = [st for (st, e) in best if e == "china" and (st, "global") in best]
    if not tiers:
        return None
    st = min(tiers, key=lambda t: best[(t, "china")])
    return {"storage": st, "china": best[(st, "china")], "global": best[(st, "global")],
            "diff": round(best[(st, "global")] - best[(st, "china")], 2)}
