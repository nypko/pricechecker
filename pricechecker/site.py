"""Generates the static website into build/ from data/latest.json, data/history.csv and config/."""
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import affiliate, fx, history, promos, terms

OUT = Path("build")
CURRENCIES = ["USD", "EUR", "GBP", "AUD"]
EDITIONS = ["global", "china"]
EDITION_LABEL = {"global": "Global", "china": "China"}
STORE_COLORS = ["#2a78d6", "#e3742c", "#1fa37a", "#b0479c", "#c9a227", "#6d4c41", "#d64545", "#3fa7b5"]


def _money(offer: dict, rates: dict) -> dict:
    """Per site currency: the store's own price if it sets one, else an ECB conversion (flagged approximate)."""
    own = offer.get("prices") or {offer["currency"]: offer["price"]}
    m = {}
    for c in CURRENCIES:
        if c in own:
            m[c.lower()], m[c.lower() + "_approx"] = own[c], 0
        else:
            m[c.lower()], m[c.lower() + "_approx"] = round(fx.convert(offer["price"], offer["currency"], c, rates), 2), 1
    return m


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


def _usd_money(usd: float | None, rates: dict) -> dict | None:
    return _money({"price": usd, "currency": "USD"}, rates) if usd else None


def _chart(series: dict[tuple, list[tuple[datetime, float]]], colors: dict[str, str], now: datetime | None = None) -> str:
    """Inline SVG line chart (USD), one line per (store, edition) - China editions dashed; empty if no history yet.
    Drawn at phone width (400 units) so the axis text stays readable when the page shrinks it."""
    pts = [(t, p) for s in series.values() for t, p in s]
    if len({t for t, _ in pts}) < 2:
        return ""
    W, H, L, R, T, B = 400, 240, 52, 8, 10, 26
    t0, t1 = min(t for t, _ in pts), max([t for t, _ in pts] + ([now] if now else []))   # lines run up to the last check
    ticks = _ticks(min(p for _, p in pts), max(p for _, p in pts))
    lo, hi = ticks[0], ticks[-1]
    x = lambda t: L + (t - t0).total_seconds() / max((t1 - t0).total_seconds(), 1) * (W - L - R)
    y = lambda p: T + (hi - p) / (hi - lo) * (H - T - B)
    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Price history in USD, shown in the table below">']
    for v in ticks:
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="{L-6}" y="{y(v)+4:.1f}" class="axis" text-anchor="end">${v:,.0f}</text>')
    parts.append(f'<text x="{L}" y="{H-6}" class="axis">{t0:%d %b}</text>'
                 f'<text x="{W-R}" y="{H-6}" class="axis" text-anchor="end">{t1:%d %b %H:%M}</text>')
    for (store, edition), s in series.items():
        if not s:
            continue
        s = s + [(t1, s[-1][1])]  # extend the last known price to "now"
        d = f"M{x(s[0][0]):.1f} {y(s[0][1]):.1f}" + "".join(  # step line: price holds until the next change
            f" H{x(t):.1f} V{y(p):.1f}" for t, p in s[1:])
        dash = ' stroke-dasharray="6 4"' if edition == "china" else ""
        parts.append(f'<path d="{d}" fill="none" stroke="{colors[store]}" stroke-width="2"{dash} data-ed="{edition}">'
                     f'<title>{store} ({EDITION_LABEL[edition]})</title></path>')
    parts.append("</svg>")
    return "".join(parts)


def _series(rows: list[dict], model: dict, rates: dict, storage: str | None = None) -> dict:
    """Per (store, edition): that store's lowest in-stock price for the phone at every change, in USD -
    across all RAM/storage options, or for one (storage="12/512")."""
    state: dict[tuple, float | None] = {}
    out: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r["model_id"] != model["id"] or r["edition"] not in model["editions"] or (storage and r["storage"] != storage):
            continue
        line = (r["store"], r["edition"])
        state[(line, r["storage"])] = fx.convert(r["price"], r["currency"], "USD", rates) if r["available"] else None
        t = datetime.strptime(r["time"], "%Y-%m-%dT%H:%M:%SZ")
        best = min((p for (l, _), p in state.items() if l == line and p is not None), default=None)
        if best is not None and (not out[line] or out[line][-1][1] != best):
            out[line].append((t, best))
    return out


def _tier_chart(rows: list[dict], model: dict, storage: str, rates: dict, colors: dict, now: datetime | None) -> dict:
    """Price history for one RAM/storage option (the toggle under each table on the phone page)."""
    series = _series(rows, model, rates, storage)
    eds = defaultdict(list)   # store -> versions it has lines for, so the legend can follow the version filter
    for s, e in series:
        eds[s].append(e)
    return {"svg": _chart(series, colors, now), "stores": {s: " ".join(sorted(eds[s])) for s in sorted(eds)},
            "china": any(e == "china" for _, e in series)}


def _title_price(offers: list[dict], tax_eu_pct: float | None) -> tuple[float, bool] | None:
    """Cheapest total for the page title and search snippet: shipping to the EU, paying by card, in EUR - the same sum
    the browser does (store price, automatic store discount, card fee, shipping, estimated import VAT when the store's
    price excludes it). Returns (total, complete); complete = shipping known and import tax settled either way."""
    best = None
    for o in offers:
        if not o["available"] or not (o.get("pay_ok") or {}).get("card", True):
            continue
        base = o["money"]["eur"]
        if o.get("promo"):
            base -= base * o["promo"]["pct"] / 100
        adj = (o["pay"].get("card") or 0) * base / 100
        ship = (o["ship"] or {}).get("EU")
        ship_amt = ship["eur"] if ship else 0
        duties = (o.get("duties") or {}).get("EU")
        tax = (base + adj + ship_amt) * tax_eu_pct / 100 if duties is False and tax_eu_pct is not None else 0
        total, complete = base + adj + ship_amt + tax, ship is not None and duties is not None
        if best is None or total < best[0]:
            best = (total, complete)
    return best


def _changes(rows: list[dict], model: dict, stores_cfg: dict, rates: dict) -> list[dict]:
    """Every recorded price/stock change for the phone, newest first, for the table on its history page."""
    out = []
    for r in rows:
        if r["model_id"] != model["id"] or r["edition"] not in model["editions"]:
            continue
        cfg = stores_cfg.get(r["store"], {})
        out.append({"time": datetime.strptime(r["time"], "%Y-%m-%dT%H:%M:%SZ"), "store_label": cfg.get("label", r["store"]),
                    "edition": r["edition"], "storage": r["storage"], "available": bool(int(r["available"])),
                    "money": _money({"price": float(r["price"]), "currency": r["currency"]}, rates)})
    return out[::-1]


def _models(catalog: list[dict], offers: list[dict] = ()) -> list[dict]:
    """One entry per phone model; its Global and China editions are combined so the price difference between them
    is visible side by side. Editions come from catalog.yaml plus whatever the stores actually sell."""
    models: dict[str, dict] = {}
    for ph in catalog:
        m = models.setdefault(ph["id"], {"id": ph["id"], "name": ph["name"], "brand": ph["brand"], "editions": [],
                                         "announced": str(ph.get("announced") or "")})   # first official launch, YYYY-MM-DD
        if ph["edition"] not in m["editions"]:
            m["editions"].append(ph["edition"])
    for o in offers:
        m = models.get(o["model_id"])
        if m and o["edition"] not in m["editions"]:
            m["editions"].append(o["edition"])
    for m in models.values():
        m["editions"].sort(key=EDITIONS.index)
    return list(models.values())


def spec(storage: str) -> str:
    """'12/256' -> '12 GB RAM · 256 GB storage', '16/1024' -> '16 GB RAM · 1 TB storage'; '' when unknown."""
    if "/" not in storage:
        return ""
    ram, rom = (int(x) for x in storage.split("/"))
    return f"{ram} GB RAM · " + (f"{rom // 1024} TB" if rom >= 1024 and rom % 1024 == 0 else f"{rom} GB") + " storage"


def _ship_notes(by_region: dict) -> list[tuple[str, list[str]]]:
    """{'EU': a, 'UK': b, 'US': b} -> [(a, ['EU']), (b, ['UK', 'US'])]: identical terms listed once."""
    grouped: dict[str, list[str]] = {}
    for region, note in by_region.items():
        if note:
            grouped.setdefault(note, []).append(region)
    return list(grouped.items())


def _storage_key(s: str) -> tuple:
    return tuple(int(x) for x in s.split("/")) if "/" in s else (0, 0)


def build(catalog: list[dict], stores_cfg: dict, rates_info: dict, terms_status: dict | None = None) -> None:
    rates = rates_info["rates"]
    terms_status = terms_status or {}
    latest = history.load_latest()
    rows = history.load_history()
    store_names = list(stores_cfg)
    colors = {s: STORE_COLORS[i % len(STORE_COLORS)] for i, s in enumerate(store_names)}
    try:
        updated_at = datetime.strptime(latest.get("updated", ""), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        updated_at = None
    tax_eu = (yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"].get("EU") or {}).get("rate_pct")
    phones = []
    for m in _models(catalog, [o for st in latest["stores"].values() for o in st["offers"]]):
        offers = []
        for store, st in latest["stores"].items():
            for o in st["offers"]:
                if o["model_id"] == m["id"] and o["edition"] in m["editions"]:
                    usd = (o.get("prices") or {}).get("USD") or fx.convert(o["price"], o["currency"], "USD", rates)
                    offers.append({**o, "store_label": stores_cfg[store].get("label", store), "stale": not st.get("ok", True),
                                   "link": affiliate.link(o["url"], stores_cfg[store]), "money": _money(o, rates), "usd": usd,
                                   "pay": {k: terms.payment_pct(stores_cfg[store], k) for k in terms.METHODS},
                                   "pay_ok": {k: terms.payment_available(stores_cfg[store], k, usd) for k in terms.METHODS},
                                   "ship": {r: terms.shipping(stores_cfg[store], r, o, rates) for r in terms.REGIONS},
                                   "notes": terms.notes(stores_cfg[store]), "promo": terms.promo(stores_cfg[store]) if promos.active(store, stores_cfg[store]) else None,
                                   "coupons": promos.coupons(store, stores_cfg.get(stores_cfg[store].get("part_of"), stores_cfg[store])
                                                             if stores_cfg[store].get("part_of") else stores_cfg[store]),
                                   "duties": {r: terms.duties_included(stores_cfg[store], r) for r in terms.REGIONS},
                                   "terms_ok": terms_status.get(store, {}).get("ok", True)})
        offers.sort(key=lambda o: (not o["available"], o["usd"]))
        in_stock = [o for o in offers if o["available"]]
        js = lambda o: {k: o[k] for k in ("store_label", "edition", "storage", "link", "money", "pay", "pay_ok", "ship", "notes", "duties", "promo", "coupons")}
        # phone page: every offer (out of stock too) - the browser builds the price grid, answer and store list from it
        full = lambda o: {**js(o), "available": o["available"], "stale": o["stale"], "store": o["store"]}
        by_storage = defaultdict(list)
        for o in offers:
            o["js"] = js(o)   # per storage tier: the browser shows each version's cheapest total in the tier header
            by_storage[o["storage"]].append(o)
        storages = sorted(by_storage, key=_storage_key)
        eds = [{"edition": e, "label": EDITION_LABEL[e],
                "best": next((o for o in in_stock if o["edition"] == e), None),
                "listed": any(o["edition"] == e for o in offers)} for e in m["editions"]]
        # Global vs China at the same configuration: the browser picks the cheapest total in each cell
        compare = [{"storage": s, "cells": [json.dumps([js(o) for o in in_stock if o["storage"] == s and o["edition"] == e],
                                                       separators=(",", ":")) for e in m["editions"]]}
                   for s in storages if len(m["editions"]) > 1]
        phones.append({**m, "slug": m["id"], "best": in_stock[0] if in_stock else None, "eds": eds,
                       "offers_json": json.dumps([js(o) for o in in_stock], separators=(",", ":")),  # re-ranked in the browser
                       "all_json": json.dumps([full(o) for o in offers], separators=(",", ":")),
                       "n_stores": len({o["store"] for o in in_stock}), "offers": offers,
                       "by_storage": [(s, by_storage[s]) for s in storages], "compare": compare,
                       "title_price": _title_price(offers, tax_eu),
                       "chart": _chart(_series(rows, m, rates), colors, updated_at),
                       "tier_charts": {s: _tier_chart(rows, m, s, rates, colors, updated_at) for s in storages}, "changes": _changes(rows, m, stores_cfg, rates),
                       "series_stores": sorted({s for s, _ in _series(rows, m, rates)})})
    phones.sort(key=lambda p: p["name"])
    phones.sort(key=lambda p: p["announced"], reverse=True)   # newest first; the index can re-sort by price or saving
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    env.filters["spec"] = spec
    env.filters["month"] = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%b %Y") if d else ""
    upd = latest.get("updated", "")
    try:
        upd_label = datetime.strptime(upd, "%Y-%m-%dT%H:%M:%SZ").strftime("%-d %b, %H:%M UTC")
    except ValueError:
        upd_label = upd
    ctx = {"updated": upd, "updated_label": upd_label, "fx_date": rates_info.get("date"), "colors": colors,
           "stores": [{"name": s, "label": c.get("label", s), "ok": latest["stores"].get(s, {}).get("ok"),
                       "error": latest["stores"].get(s, {}).get("error", ""), "count": len(latest["stores"].get(s, {}).get("offers", [])),
                       "terms_ok": terms_status.get(s, {}).get("ok", True), "notes": terms.notes(c),
                       "pay": {m: terms.payment_pct(c, m) for m in terms.METHODS},
                       "pay_min": {m: _usd_money(terms.min_order_usd(c, m), rates) for m in terms.METHODS},
                       "ship_notes": _ship_notes(terms.notes(c)["ship"])}
                      for s, c in stores_cfg.items() if c.get("enabled", True)],
           "month": updated_at.strftime("%B %Y") if updated_at else "",   # "October 2026" in page titles
           "brands": sorted({p["brand"] for p in phones}), "edition_label": EDITION_LABEL,
           "import_tax_json": json.dumps(yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"])}
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "phones").mkdir(parents=True)
    (OUT / "history").mkdir()
    shutil.copytree("static", OUT / "static")
    shutil.copy("static/favicon.ico", OUT / "favicon.ico")   # browsers ask for /favicon.ico at the root
    (OUT / "index.html").write_text(env.get_template("index.html").render(phones=phones, root="", **ctx))
    for p in phones:
        (OUT / "phones" / f'{p["slug"]}.html').write_text(env.get_template("phone.html").render(p=p, root="../", **ctx))
        (OUT / "history" / f'{p["slug"]}.html').write_text(env.get_template("history.html").render(p=p, root="../", **ctx))
    print(f"  site: {len(phones)} phone pages + price history pages -> {OUT}/")
