"""Numbers derived from stored data for the data files and pages: per-store price lines, real listing drops, the
China/Global gap and the sale split. Pure functions: rows and offers come in as the dicts history and site.build make."""
from datetime import UTC, datetime, timedelta

from .pricing import Settings, cost, unknowns

MIN_PCT, MIN_EUR = 3, 20      # a "real" drop; the same rule as telegram.MIN_PCT / MIN_EUR
OLDER_DAYS = 30               # how far back the Drops page looks for earlier drops in a week with none
_EU = Settings("EU", "", "card", "eur")


def _eur(price: float, cur: str, rates: dict) -> float:
    return price if cur == "EUR" else price / rates[cur]


def _when(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def _parent(store: str) -> str:
    """An EU-warehouse sub-store (x_eu) draws on its parent store's line. By id suffix: no stores config needed."""
    return store[:-3] if store.endswith("_eu") else store


def store_lines(rows: list[dict], model_id: str, edition: str, rates: dict) -> dict[str, list[tuple[str, float]]]:
    """{store: [(day, lowest EUR price that day)]}. Rows exist only on change, so a listing's state carries forward
    day to day; sold-out listings drop out; sub-stores fold into their parent. A day is any day with a row."""
    days = sorted({r["time"][:10] for r in rows})
    by_day: dict[str, list[dict]] = {}
    for r in rows:
        by_day.setdefault(r["time"][:10], []).append(r)
    state: dict[tuple, float | None] = {}
    out: dict[str, list[tuple[str, float]]] = {}
    for day in days:
        for r in by_day[day]:
            if r["model_id"] == model_id and r["edition"] == edition:
                state[(r["store"], r["storage"])] = _eur(r["price"], r["currency"], rates) if r["available"] else None
        low: dict[str, float] = {}
        for (store, _), p in state.items():
            if p is not None:
                s = _parent(store)
                low[s] = min(p, low.get(s, p))
        for s, p in low.items():
            out.setdefault(s, []).append((day, round(p, 2)))
    return out


def listing_days(rows: list[dict], model_id: str) -> dict[tuple[str, str, str], list[tuple[str, float | None]]]:
    """{(store, edition, storage): [(day, native price or None)]}: a listing's end-of-day state (the last row of the UTC
    day wins), as change points over all of `rows`: the first day it has a price, then each day the end-of-day price
    differs from the last point's, None when it goes out of stock. A listing that starts sold out has no point until
    it is in stock. Sub-stores are not folded: each listing is its own offer."""
    days = sorted({r["time"][:10] for r in rows})
    by_day: dict[str, list[dict]] = {}
    for r in rows:
        by_day.setdefault(r["time"][:10], []).append(r)
    state: dict[tuple, float | None] = {}
    out: dict[tuple[str, str, str], list[tuple[str, float | None]]] = {}
    for day in days:
        touched = set()
        for r in by_day[day]:
            if r["model_id"] == model_id:
                k = (r["store"], r["edition"], r["storage"])
                state[k] = r["price"] if r["available"] else None
                touched.add(k)
        for k in touched:
            pts = out.setdefault(k, [])
            if state[k] != (pts[-1][1] if pts else None):
                pts.append((day, state[k]))
    return {k: v for k, v in out.items() if v}


def listing_drops(rows: list[dict], rates: dict, now: datetime, window_days: int = 7) -> list[dict]:
    """The same store listing, its price `window_days` ago vs now. A listing with no price from then (a store
    joining the site) is not a drop. real: at least 3% and EUR 20 below."""
    hist: dict[tuple, list[dict]] = {}
    for r in rows:
        hist.setdefault((r["store"], r["model_id"], r["edition"], r["storage"]), []).append(r)
    cutoff = now - timedelta(days=window_days)
    out = []
    for (store, model, edition, storage), h in hist.items():
        last = h[-1]
        if not last["available"]:
            continue
        before = [r for r in h if r["available"] and _when(r["time"]) <= cutoff]
        if not before:
            continue
        then, cur = _eur(before[-1]["price"], before[-1]["currency"], rates), _eur(last["price"], last["currency"], rates)
        if cur >= then - 1:
            continue
        pct, saving = round((cur / then - 1) * 100, 1), round(then - cur, 2)
        out.append({"slug": model, "store": store, "edition": edition, "storage": storage, "then": round(then, 2),
                    "now": round(cur, 2), "pct": pct, "eur": saving, "when": last["time"][:10],
                    "real": (cur / then - 1) * 100 <= -MIN_PCT and saving >= MIN_EUR})
    return out


def mark_headline(drops: list[dict], telegram_state: dict, now: datetime, window_days: int = 7) -> list[dict]:
    """Adds headline: True to drops of a phone the Telegram channel posted within the window. Takes the "posted" list
    from the saved state (or from the whole telegram.json); a state without it marks nothing."""
    st = telegram_state or {}
    posted = st.get("posted") or (st.get("phones") or {}).get("posted") or []
    cutoff = now - timedelta(days=window_days)
    slugs = {p["slug"] for p in posted if _when(p["at"]) >= cutoff}
    return [{**d, "headline": True} if d["slug"] in slugs else d for d in drops]


def _key(d: dict) -> tuple:
    return (d["slug"], d["store"], d["edition"], d["storage"])


def week_drops(rows: list[dict], rates: dict, now: datetime, telegram_state: dict | None = None, window_days: int = 7) -> list[dict]:
    """The drops of the last `window_days` that count (real: MIN_PCT and MIN_EUR), those of a phone the Telegram channel
    posted marked headline. The one list behind the home page's count and the Drops page and its feed."""
    return mark_headline([d for d in listing_drops(rows, rates, now, window_days) if d["real"]], telegram_state or {}, now, window_days)


def older_drops(rows: list[dict], rates: dict, now: datetime, window_days: int = OLDER_DAYS) -> list[dict]:
    """Real drops against the price `window_days` ago that are not in this week's list, the latest change first: what
    the Drops page shows in a week with none. Not cut to a number here (the page drops listings it can't show first)."""
    week = {_key(d) for d in week_drops(rows, rates, now)}
    out = [d for d in listing_drops(rows, rates, now, window_days) if d["real"] and _key(d) not in week]
    return sorted(out, key=lambda d: (d["when"], d["eur"]), reverse=True)


def gap(offers: list[dict], rule) -> dict | None:
    """China vs Global at the same RAM/storage ("China ~EUR 527 less at 12 + 512 GB"), EU / card / EUR: settled totals
    of current, in-stock offers only. The storage where China is cheapest among those both editions have."""
    best: dict[tuple, float] = {}
    for o in offers:
        if not o.get("available") or o.get("storage") == "base" or (o.get("ship") or {}).get("EU") is False:
            continue
        c = cost(o, _EU, rule)
        if c.old or not c.pay_ok or unknowns(c):
            continue
        k = (o["storage"], o["edition"])
        best[k] = min(c.total, best.get(k, c.total))
    tiers = [st for (st, e) in best if e == "china" and (st, "global") in best]
    if not tiers:
        return None
    st = min(tiers, key=lambda t: best[(t, "china")])
    return {"storage": st, "china": best[(st, "china")], "global": best[(st, "global")],
            "diff": round(best[(st, "global")] - best[(st, "china")], 2)}


def promo_split(offer: dict, cur: str) -> tuple[float, float, float]:
    """(list price, sale amount, price paid) in the display currency."""
    lst = offer["money"][cur]
    amt = lst * ((offer.get("promo") or {}).get("pct") or 0) / 100
    return lst, round(amt, 2), round(lst - amt, 2)
