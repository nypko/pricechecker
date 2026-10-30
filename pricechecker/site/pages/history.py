"""Price history (spec §5.6): history/<slug>.html shows the last 90 days of changes for a phone, and every month the
phone has rows in gets its own small page, history/<slug>/<YYYY-MM>.html. The main page links the months older than its
window. Per version (China / Global): a line per store (derive.store_lines, drawn by the phone page's macro), lowest /
highest / now, and the change list grouped by day, newest first. static/js/history.js shows one version at a time."""
from collections import defaultdict
from datetime import datetime, timedelta

from jinja2 import Environment

from ... import derive
from ..blocks import mem_tiny, money
from ..common import ed_labels
from ..context import SiteData
from .phone import store_lines_svg

EDITION_ORDER = ("china", "global")   # the China version first, as on the phone page
WINDOW_DAYS = 90   # the main page lists changes of the last 90 days; earlier months have their own page


def _next_month(m: str) -> str:
    y, mo = int(m[:4]), int(m[5:])
    return f"{y + (mo == 12)}-{mo % 12 + 1:02d}"


def _month_label(m: str) -> str:
    return datetime.strptime(m + "-01", "%Y-%m-%d").strftime("%B %Y")


def _day_label(d: str) -> str:
    return datetime.strptime(d, "%Y-%m-%d").strftime("%-d %b %Y")


def change_lines(rows: list[dict], names: dict, labels: dict, rates: dict) -> list[dict]:
    """One line per recorded change of a phone's listings, newest first. `rows` hold only this phone's rows, oldest
    first, from the start of its history (a change is told against the listing's previous row). A row that moves the
    price by less than a euro on screen is no change and gets no line."""
    prev: dict[tuple, tuple[float, bool]] = {}
    out = []
    for r in rows:
        key = (r["store"], r["edition"], r["storage"])
        eur, avail = derive._eur(r["price"], r["currency"], rates), bool(r["available"])
        was = prev.get(key)
        prev[key] = (eur, avail)
        if was is None:
            tail, kind = (f"first seen at {money(eur, 'eur')}" if avail else "first seen out of stock"), ""
        elif not avail:
            if not was[1]:
                continue
            tail, kind = "out of stock", ""
        elif not was[1]:
            tail, kind = f"back in stock at {money(eur, 'eur')}", ""
        elif money(was[0], "eur") == money(eur, "eur"):
            continue
        else:
            tail, kind = f"{money(was[0], 'eur')} → {money(eur, 'eur')}", "down" if eur < was[0] else "up"
        out.append({"day": r["time"][:10], "hm": r["time"][11:16], "edition": r["edition"], "dir": kind,
                    "text": f"{names.get(r['store'], r['store'])} · {labels[r['edition']]} {mem_tiny(r['storage'])} · {tail}"})
    return out[::-1]


def _clip(lines: dict, first_day: str | None, start: str) -> dict:
    """Keep the points from `start` on. A store whose price held through `start` (its last earlier point, and it has a
    point on the window's first day) enters the window at `start` with that price instead of vanishing."""
    out = {}
    for s, pts in lines.items():
        inside = [(d, v) for d, v in pts if d >= start]
        before = [(d, v) for d, v in pts if d < start]
        if inside and before and inside[0][0] == first_day and first_day != start:
            inside = [(start, before[-1][1])] + inside
        if inside:
            out[s] = inside
    return out


def _stats(lines: dict, last_day: str | None) -> dict | None:
    vals = [v for pts in lines.values() for _, v in pts]
    if not vals:
        return None
    now = [pts[-1][1] for pts in lines.values() if pts[-1][0] == last_day]   # stores in stock on the window's last day
    return {"lowest": min(vals), "highest": max(vals), "now": min(now) if now else None}


def _sections(p: dict, rows: list[dict], names: dict, rates: dict, start: str, end: str | None) -> list[dict]:
    """Per version: chart, stats and the day-grouped changes of [start, end). rows: this phone's, oldest first."""
    labels = ed_labels(p["brand"])
    upto = [r for r in rows if end is None or r["time"][:10] < end]
    days = sorted({r["time"][:10] for r in upto})
    first_day = next((d for d in days if d >= start), None)
    last_day = days[-1] if first_day else None
    changes = [c for c in change_lines(upto, names, labels, rates) if c["day"] >= start]
    out = []
    for e in sorted(p["editions"], key=EDITION_ORDER.index):
        lines = _clip(derive.store_lines(upto, p["id"], e, rates), first_day, start)
        by_day: dict[str, list[dict]] = defaultdict(list)
        for c in changes:
            if c["edition"] == e:
                by_day[c["day"]].append(c)
        out.append({"e": e, "label": labels[e], "svg": store_lines_svg({names.get(s, s): pts for s, pts in lines.items()}),
                    "stats": _stats(lines, last_day),
                    "days": [{"day": d, "label": _day_label(d), "lines": by_day[d]} for d in sorted(by_day, reverse=True)]})
    return out


def _default_edition(p: dict, sections: list[dict]) -> str:
    """The version shown first when the switch runs: the one with the cheapest offer, if it has anything to show."""
    want = p["best"]["edition"] if p.get("best") else None
    withdata = [s["e"] for s in sections if s["days"] or s["svg"]]
    return want if want in withdata else (withdata or p["editions"])[0]


def _page(p: dict, rows: list[dict], months: list[str], names: dict, rates: dict, start: str, month: str | None) -> dict:
    end = _next_month(month) + "-01" if month else None
    sections = _sections(p, rows, names, rates, month + "-01" if month else start, end)
    v = {"month": month, "month_label": _month_label(month) if month else "", "sections": sections,
         "default": _default_edition(p, sections), "since": _day_label(rows[0]["time"][:10]) if rows else None,
         "window": WINDOW_DAYS}
    if month:
        i = months.index(month)
        v["prev"] = (months[i - 1], _month_label(months[i - 1])) if i else None
        v["next"] = (months[i + 1], _month_label(months[i + 1])) if i + 1 < len(months) else None
    else:
        older = {r["time"][:7] for r in rows if r["time"][:10] < start}
        v["earlier"] = [(m, _month_label(m)) for m in reversed(months) if m in older]
    return v


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for r in data.rows_all:
        by_model[r["model_id"]].append(r)
    names = {s: c.get("label", s) for s, c in data.stores_cfg.items()}
    latest = max((r["time"] for r in data.rows_all), default=None)
    now = data.updated_at or (datetime.strptime(latest, "%Y-%m-%dT%H:%M:%SZ") if latest else datetime.now())
    start = (now - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")
    t = env.get_template("history.html")
    out = {}
    for p in phones:
        slug = p["slug"]
        rows = sorted((r for r in by_model.get(p["id"], []) if r["edition"] in p["editions"]), key=lambda r: r["time"])
        months = sorted({r["time"][:7] for r in rows})
        out[f"history/{slug}.html"] = t.render(p=p, v=_page(p, rows, months, names, data.rates, start, None),
                                               root="../", path=f"history/{slug}", **ctx)
        for m in months:
            out[f"history/{slug}/{m}.html"] = t.render(p=p, v=_page(p, rows, months, names, data.rates, start, m),
                                                       root="../../", path=f"history/{slug}/{m}", **ctx)
    return out

