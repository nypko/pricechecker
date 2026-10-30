"""Price-history charts (inline SVG), the series behind them, their Now/Low/High/Average stats, and each offer's trend."""
from collections import defaultdict
from datetime import datetime, timedelta

from .. import fx
from .common import EDITION_LABEL, SYMBOL

LABELS: dict[str, str] = {}   # store key -> name shown in chart readouts; set by build()


def _ticks(lo: float, hi: float, n: int = 4) -> list[float]:
    """Round axis values covering lo..hi, e.g. 1075..1249 -> [1050, 1100, 1150, 1200, 1250]."""
    raw = max((hi - lo) / n, 1)
    mag = 10 ** (len(str(int(raw))) - 1)
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    v, out = (lo // step) * step, []
    while v < hi + step:
        out.append(v)
        v += step
    return out


def _chart(series: dict[tuple, list[tuple[datetime, float]]], colors: dict[str, str], now: datetime | None = None,
           cur: str = "USD", labels: dict = EDITION_LABEL) -> str:
    """Inline SVG line chart in `cur`, one line per (store, edition) - China editions dashed; empty if no history yet.
    Drawn at phone width (400 units) so the axis text stays readable when the page shrinks it."""
    pts = [(t, p) for s in series.values() for t, p in s if p is not None]
    if not pts:
        return ""
    W, H, L, R, T, B = 400, 240, 52, 8, 10, 26
    # lines run up to the last check, so a price that never changed is still a line from when it was first seen
    t0, t1 = min(t for t, _ in pts), max([t for t, _ in pts] + ([now] if now else []))
    if t1 <= t0:
        return ""
    p0, p1 = min(p for _, p in pts), max(p for _, p in pts)
    if p1 == p0:   # one flat price: give the axis some room around it
        p0, p1 = p0 - p1 * 0.05, p1 + p1 * 0.05
    ticks = _ticks(p0, p1)
    lo, hi = ticks[0], ticks[-1]
    x = lambda t: L + (t - t0).total_seconds() / max((t1 - t0).total_seconds(), 1) * (W - L - R)
    y = lambda p: T + (hi - p) / (hi - lo) * (H - T - B)
    # data-* let app.js read a value off the chart where it is tapped: the time span, plot edges, and each line's steps
    parts = [(f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Price history in {cur}, shown in the table below" '
              f'data-t0="{t0:%Y-%m-%dT%H:%M}" data-t1="{t1:%Y-%m-%dT%H:%M}" data-l="{L}" data-r="{W-R}">')]
    for v in ticks:
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="{L-6}" y="{y(v)+4:.1f}" class="axis" text-anchor="end">{SYMBOL[cur]}{v:,.0f}</text>')
    parts.append(f'<text x="{L}" y="{H-6}" class="axis">{t0:%d %b}</text>'
                 f'<text x="{W-R}" y="{H-6}" class="axis" text-anchor="end">{t1:%d %b %H:%M}</text>')
    for (store, edition), s in series.items():
        if not s:
            continue
        s = s + [(t1, s[-1][1])]  # extend the last price to "now" (a sold-out line stays cut off)
        d, prev = "", None   # step line: price holds until the next change; None (sold out) ends it until it's back
        for t, p in s:
            if prev is not None:
                d += f" H{x(t):.1f}"
            if p is not None:
                d += f" V{y(p):.1f}" if prev is not None else f" M{x(t):.1f} {y(p):.1f}"
            prev = p
        d = d.strip()
        dash = ' stroke-dasharray="6 4"' if edition == "china" else ""
        name = f"{LABELS.get(store, store)} ({labels[edition]})"
        steps = ";".join(f"{x(t):.1f}:" + (f"{SYMBOL[cur]}{p:,.0f}" if p is not None else "") for t, p in s[:-1])
        parts.append(f'<path d="{d}" fill="none" stroke="{colors[store]}" stroke-width="2"{dash} data-ed="{edition}" '
                     f'data-name="{name}" data-steps="{steps}"><title>{name}</title></path>')
    parts.append("</svg>")
    return "".join(parts)


def _series(rows: list[dict], model: dict, rates: dict, storage: str | None = None, cur: str = "USD") -> dict:
    """Per (store, edition): that store's lowest in-stock price for the phone at every change, in `cur` -
    across all RAM/storage options, or for one (storage="12/512"). A point with price None = sold out from then on."""
    state: dict[tuple, float | None] = {}
    out: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r["model_id"] != model["id"] or r["edition"] not in model["editions"] or (storage and r["storage"] != storage):
            continue
        if r["store"] not in LABELS:   # a store since removed from stores.yaml
            continue
        line = (r["store"], r["edition"])
        state[(line, r["storage"])] = fx.convert(r["price"], r["currency"], cur, rates) if r["available"] else None
        t = datetime.strptime(r["time"], "%Y-%m-%dT%H:%M:%SZ")
        best = min((p for (l, _), p in state.items() if l == line and p is not None), default=None)
        # a line starts at its first in-stock price
        if (out[line] or best is not None) and (not out[line] or out[line][-1][1] != best):
            out[line].append((t, best))
    return out


def _trend(rows: list[dict], model_id: str, o: dict, now: datetime | None) -> dict | None:
    """How one offer's store price moved, from the hourly history, as ratios so the browser can show it in any currency:
    {"drop": 0.05, "since": "2026-10-16"} when it is below its highest in-stock price of the last 7 days (or since we
    first saw it, if that's sooner), and "low30": 1 when it's the lowest in 30 days of history. None = no movement to show."""
    if not now or not o.get("available"):
        return None
    hist = [(datetime.strptime(r["time"], "%Y-%m-%dT%H:%M:%SZ"), r["price"], r["available"]) for r in rows
            if r["store"] == o["store"] and r["model_id"] == model_id and r["edition"] == o["edition"] and r["storage"] == o["storage"]]
    if not hist:
        return None
    price, start = float(o["price"]), now - timedelta(days=7)
    held = [p for t, p, ok in hist if t <= start and ok][-1:]               # the price the week started with
    recent = [p for t, p, ok in hist if t > start and ok]
    prev = max(held + recent) if held + recent else None
    out = {}
    if prev and prev > price * 1.005:                                       # ignore rounding-size moves
        first = hist[0][0]
        out = {"drop": round((prev - price) / price, 4), "since": "" if first <= start else first.strftime("%Y-%m-%d")}
    if now - hist[0][0] >= timedelta(days=30):
        month = [p for t, p, ok in hist if ok and t >= now - timedelta(days=30)] + [p for t, p, ok in hist if ok and t < now - timedelta(days=30)][-1:]
        if month and price <= min(month) and max(month) > price * 1.005:
            out["low30"] = 1
    return out or None


def _stats(series: dict, now: datetime | None, cur: str) -> dict | None:
    """Now / lowest / highest / average of the cheapest in-stock price at any store, over the recorded history (one variant,
    one currency). The average is weighted by time, so a price that held for days counts for more than a one-hour blip."""
    events = sorted({t for s in series.values() for t, _ in s})
    if not events or not now:
        return None
    level, steps = {}, []
    for t in events:
        for line, s in series.items():
            for tt, p in s:
                if tt == t:
                    level[line] = p
        live = [p for p in level.values() if p is not None]   # stores that sold out don't count
        steps.append((t, min(live) if live else None))
    if steps[-1][1] is None:   # nothing in stock now: no "Now" price to show
        return None
    span = [(t, p, ((steps[i + 1][0] if i + 1 < len(steps) else now) - t).total_seconds()) for i, (t, p) in enumerate(steps) if p is not None]
    steps = [st for st in steps if st[1] is not None]
    total = sum(w for _, _, w in span)
    lo = min(steps, key=lambda x: x[1])
    hi = max(steps, key=lambda x: x[1])
    fmt = lambda v: f"{SYMBOL[cur]}{v:,.0f}"
    return {"now": fmt(steps[-1][1]), "low": fmt(lo[1]), "low_at": f"{lo[0]:%-d %b}", "high": fmt(hi[1]), "high_at": f"{hi[0]:%-d %b}",
            "avg": fmt(sum(p * w for _, p, w in span) / total) if total else fmt(steps[-1][1]), "since": f"{steps[0][0]:%-d %b}"}
