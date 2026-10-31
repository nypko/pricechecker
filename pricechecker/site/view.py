"""The one view model every page renders from: offer inputs + the visitor's settings -> display rows.
static/js/view.js is its line-for-line mirror; rows are plain dicts with the same camelCase keys on both sides so the
server templates and the browser blocks show identical numbers. No I/O."""
import math
from datetime import date, timedelta

from .. import pricing
from ..pricing import Settings

DEFAULT = Settings("EU", "", "card", "eur")


_CUR = ("eur", "usd", "gbp", "cad", "aud")


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


def daily_best(inputs: list[dict], trend: dict, edition: str, storage: str, tax_cfg: dict, s: Settings) -> list[dict]:
    """The best delivered price of the edition/storage on each day with a point: a point's store re-priced as its current
    offer with the point's ratio applied, ranked by rows/best_of so delivery, payment and staleness rules are today's."""
    series = ((trend.get(edition) or {}).get(storage)) or {}
    days: dict[str, list[dict]] = {}
    for label, points in series.items():
        cur = next((o for o in inputs if o.get("store_label") == label and o.get("edition") == edition
                    and o.get("storage") == storage), None)
        if cur is None:
            continue
        for day, ratio in points:
            # approximation: history has only the native price, so every currency is scaled by the same ratio
            money = {k: (v * ratio if k in _CUR else v) for k, v in (cur.get("money") or {}).items()}
            days.setdefault(day, []).append({**cur, "money": money, "available": True})
    out = []
    for day in sorted(days):
        best = best_of(rows(days[day], tax_cfg, s), edition, storage)
        if best is not None:
            out.append({"day": day, "total": best["total"], "store": best["store"], "approx": best["approx"]})
    return out


def _shift(day: str, n: int) -> str:
    return (date.fromisoformat(day) - timedelta(days=n)).isoformat()


def _pct(now: float, base: float) -> float:
    return math.floor((now - base) / base * 1000 + 0.5) / 10      # half up, as the JS mirror does


def price_trend(days: list[dict], now_row: dict | None, today: str) -> dict | None:
    """The numbers behind the 30-day trend block: today's point is now_row (it replaces any list entry for today),
    the window is today-29..today, the low is the most recent day at the window minimum. Whole days, UTC."""
    if now_row is None:
        return None
    pts = [d for d in days if d["day"] < today] + [{"day": today, "total": now_row["total"], "store": now_row["store"],
                                                    "approx": now_row["approx"]}]
    start = _shift(today, 29)
    win = [d for d in pts if d["day"] >= start]
    first_day = pts[0]["day"]
    low = min(d["total"] for d in win)
    low_pt = [d for d in win if d["total"] == low][-1]
    base = win[0]
    back = [d for d in pts if d["day"] <= _shift(today, 7)]
    return {"short": len(pts) < 7, "first_day": first_day, "window_start": start, "full_window": first_day <= start,
            "now": now_row["total"], "low": low, "low_day": low_pt["day"], "low_store": low_pt["store"],
            "high": max(d["total"] for d in win), "is_low": now_row["total"] <= low,
            "change_pct": _pct(now_row["total"], base["total"]) if base["day"] != today else None,
            "since_first": base["day"] == first_day,
            "change_7d": _pct(now_row["total"], back[-1]["total"]) if back else None,
            "approx": bool(now_row["approx"] or low_pt["approx"])}


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


def _size(s: str | None) -> tuple[int, int] | None:
    p = (s or "").split("/")
    return (int(p[0]), int(p[1])) if len(p) == 2 and p[0].isdigit() and p[1].isdigit() else None


def distance(a: str, b: str) -> float:
    """How far two RAM/storage options are apart: a storage step counts double, RAM counts per 4 GB."""
    x, y = _size(a), _size(b)
    if not x or not y:
        return 99
    return abs(math.log2(x[1] / y[1])) * 2 + abs(x[0] - y[0]) / 4


def closest(storages: list[str], want: str) -> str:
    """The option in `storages` nearest to `want` (the first listed on a tie); "" when there are none."""
    best, bd = "", math.inf
    for s in storages:
        d = 0 if s == want else distance(s, want)
        if d < bd:
            best, bd = s, d
    return best


def nearest_memory(rows: list[dict], edition: str, storage: str) -> str | None:
    """The memory nearest `storage` among those the edition has a current, payable row for (never "base")."""
    have = [r["storage"] for r in rows if r["state"] == "ok" and r["edition"] == edition and r["storage"] != "base"]
    return closest(have, storage) or None


def default_pick(rows: list[dict]) -> dict | None:
    """The first (best) current, payable row's edition and storage."""
    r = next((r for r in rows if r["state"] == "ok"), None)
    return {"ed": r["edition"], "mem": r["storage"]} if r else None


def pick_for_memory(rows: list[dict], storage: str, preferred: str) -> dict:
    """The version to show once a memory is picked: the preferred one if it has a current price there, else the other
    version, else the default pick; with nothing current at all, the preferred version at that memory."""
    other = "global" if preferred == "china" else "china"
    for ed in (preferred, other):
        if best_of(rows, ed, storage):
            return {"ed": ed, "mem": storage}
    return default_pick(rows) or {"ed": preferred, "mem": storage}
