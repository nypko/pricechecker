"""Each offer's price trend (a recent drop, a 30-day low) from the hourly history; the history pages draw their own charts."""
from datetime import datetime, timedelta


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
