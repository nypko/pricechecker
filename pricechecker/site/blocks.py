"""Text helpers for the D blocks (templates/_d/blocks.html), registered in the Jinja environment. static/js/blocks.js
has the same functions with the same rules, so a block reads the same rendered on the server or in the browser
(tests/test_blocks.py compares them). Rounding is half up on both sides, written out (not Python's round())."""
import math
from datetime import datetime

from . import view

SYMBOL = {"eur": "€", "gbp": "£", "usd": "$", "cad": "C$", "aud": "A$"}
PLACE = {"EU": "the EU", "UK": "the UK", "US": "the US", "CA": "Canada", "AU": "Australia", "Global": "your country"}
PAY_BY = {"card": "card", "paypal": "PayPal", "bank": "bank transfer"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _half_up(v: float, dec: int) -> int:
    """|v| scaled by 10^dec and rounded half up, as an integer (the same float steps as Math.floor(x * f + 0.5))."""
    return math.floor(abs(v) * 10 ** dec + 0.5)


def fixed(v: float, dec: int = 1) -> str:
    """4.65 -> "4.7": a plain number with dec decimals, half up."""
    n = _half_up(v, dec)
    s = str(n // 10 ** dec) + (f".{n % 10 ** dec:0{dec}d}" if dec else "")
    return ("-" if v < 0 and n else "") + s


def pct(v: float) -> str:
    """2 -> "2", 2.5 -> "2.5"."""
    s = fixed(v, 1)
    return s.removesuffix(".0")


def group(n: int) -> str:
    """12345 -> "12,345"."""
    return f"{n:,}"


def money(v: float | None, cur: str, dec: bool = False) -> str:
    """Symbol + en-GB grouping: €1,049 (headline) or €1,049.00 (dec, receipt lines); "−" for a negative; "–" for none."""
    if v is None:
        return "–"
    d = 2 if dec else 0
    n = _half_up(v, d)
    s = group(n // 10 ** d) + (f".{n % 10 ** d:02d}" if dec else "")
    return ("−" if v < 0 and n else "") + SYMBOL[cur] + s


def _rom(gb: str) -> str:
    return f"{int(gb) // 1024} TB" if int(gb) >= 1024 and int(gb) % 1024 == 0 else f"{gb} GB"


def mem_parts(storage: str | None) -> tuple[str, str] | None:
    """'12/256' -> ('12 GB', '256 GB'); None for "base" (the store doesn't list RAM/storage)."""
    p = (storage or "").split("/")
    return (f"{p[0]} GB", _rom(p[1])) if len(p) == 2 else None


def mem_label(storage: str | None) -> str:
    """'12/256' -> '12 GB · 256 GB' (chips, store rows)."""
    p = mem_parts(storage)
    return f"{p[0]} · {p[1]}" if p else "RAM/storage not listed"


def mem_text(storage: str | None) -> str:
    """'12/256' -> '12 GB RAM · 256 GB storage'."""
    p = mem_parts(storage)
    return f"{p[0]} RAM · {p[1]} storage" if p else "RAM/storage not listed"


def mem_short(storage: str | None) -> str:
    """'12/256' -> '12 GB + 256 GB' (buy bar)."""
    p = mem_parts(storage)
    return f"{p[0]} + {p[1]}" if p else "RAM/storage not listed"


def mem_tiny(storage: str | None) -> str:
    """'12/256' -> '12 + 256', '16/1024' -> '16 + 1 TB' (home gap line)."""
    p = (storage or "").split("/")
    if len(p) != 2:
        return "RAM/storage not listed"
    return f"{p[0]} + " + (_rom(p[1]) if int(p[1]) >= 1024 else p[1])


def mem_key(storage: str) -> tuple[int, int]:
    p = storage.split("/")
    return int(p[1]), int(p[0])


def _ts(iso: str) -> datetime:
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")


def stamp(iso: str | None) -> str:
    """'2026-10-30T14:05:00Z' -> '30 Oct, 14:05 UTC'."""
    if not iso:
        return ""
    d = _ts(iso)
    return f"{d.day} {MON[d.month - 1]}, {d.hour:02d}:{d.minute:02d} UTC"


def days_ago(iso: str | None, now: str | None) -> int | None:
    """Whole days between the store's last check and now (both ISO, UTC)."""
    if not iso or not now:
        return None
    return math.floor((_ts(now) - _ts(iso)).total_seconds() / 86400)


def month(iso: str | None) -> str:
    """'2026-10-02' -> 'Oct 2026'."""
    if not iso:
        return ""
    y, m = iso[:7].split("-")
    return f"{MON[int(m) - 1]} {y}"


def days(d: list | None) -> str:
    """[5, 9] -> '5–9 days'."""
    if not d:
        return "delivery time not stated"
    return f"{d[0]} days" if d[0] == d[1] else f"{d[0]}–{d[1]} days"


def cap(t: str) -> str:
    return t[:1].upper() + t[1:]


def caveat(r: dict, s) -> str:
    """What a store row's total leaves out or includes, in words."""
    x = []
    if r["ship"] is None:
        x.append("shipping not listed")
    elif r["shipMin"]:
        x.append("shipping from " + money(r["ship"], s.cur))
    if r["adj"] is None:
        x.append(PAY_BY[s.pay] + " fee unknown")
    if r["duties"] is True:
        x.append(r["taxName"] + " paid by store")
    elif r["taxEst"] is None:
        x.append(r["taxName"] + " not estimated")
    elif r["duties"] is False:
        x.append("incl. ≈" + money(r["taxAdded"], s.cur) + " " + r["taxName"])
    else:
        x.append(r["taxName"] + " not stated, may add ≈" + money(r["taxEst"], s.cur))
    return " · ".join(x)


def why(best: dict, pick: list[dict], s) -> tuple[str, str]:
    """The verdict's "why this one": (bold lead, rest)."""
    ok = [r for r in pick if r["state"] == "ok"]
    cheaper = sorted((r for r in ok if r["total"] < best["total"]), key=lambda r: r["total"])
    if cheaper:
        c = cheaper[0]
        gaps = " or ".join(g for g, open_ in (("shipping", c["ship"] is None), ("import tax", c["unknown"] % 2 == 1)) if open_)
        rest = (f"the lowest total where shipping and import tax are settled. {c['store']} lists "
                f"{money(c['total'], s.cur)} but doesn't say what {gaps} will add.")
        return "Why this one:", rest
    if len(ok) > 1:
        return "Why this one:", f"the lowest total of {len(ok)} stores for this version and memory."
    return "Only one store", "we check sells this version and memory."


def mem_options(rows: list[dict], edition: str) -> list[tuple[str, dict | None]]:
    """The edition's memories (no "base"), smallest first, each with its best current payable row (or None)."""
    sts = sorted({r["storage"] for r in rows if r["edition"] == edition and r["storage"] != "base"
                  and r["state"] in ("ok", "nopay", "stale")}, key=mem_key)
    return [(st, view.best_of(rows, edition, st)) for st in sts]


def list_order(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Store list order: (current payable, not payable, stale, doesn't deliver), and the sold-out ones apart."""
    order = ["ok", "nopay", "stale", "nodelivery"]
    main = sorted((r for r in rows if r["state"] in order), key=lambda r: order.index(r["state"]))
    return main, [r for r in rows if r["state"] == "soldout"]


def stores_n(rows: list[dict]) -> int:
    return len({r["store"] for r in rows if r["state"] == "ok"})


def register(env) -> None:
    """Make the helpers and the view functions the blocks call available to every template."""
    env.globals.update(money=money, fixed=fixed, pct=pct, group=group, mem_parts=mem_parts, mem_label=mem_label, mem_text=mem_text, mem_short=mem_short,
                       mem_tiny=mem_tiny, stamp=stamp, days_ago=days_ago, month_of=month, days_text=days, cap=cap,
                       caveat=caveat, why=why, mem_options=mem_options, list_order=list_order, stores_n=stores_n,
                       best_of=view.best_of, gap_of=view.gap, PLACE=PLACE, PAY_BY=PAY_BY)
