"""Generates the static website into build/ from data/latest.json, data/history.csv and config/."""
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import affiliate, fx, history, terms

OUT = Path("build")
CURRENCIES = ["USD", "EUR", "GBP", "AUD"]
EDITIONS = ["global", "china"]
EDITION_LABEL = {"global": "Global", "china": "China"}
STORE_COLORS = ["#2a78d6", "#e3742c", "#1fa37a", "#b0479c", "#c9a227", "#5c6bc0", "#d64545", "#3fa7b5"]


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


def _chart(series: dict[tuple, list[tuple[datetime, float]]], colors: dict[str, str]) -> str:
    """Inline SVG line chart (USD), one line per (store, edition) - China editions dashed; empty if no history yet."""
    pts = [(t, p) for s in series.values() for t, p in s]
    if len({t for t, _ in pts}) < 2:
        return ""
    W, H, L, R, T, B = 720, 260, 64, 12, 12, 28
    t0, t1 = min(t for t, _ in pts), max(t for t, _ in pts)
    lo, hi = min(p for _, p in pts), max(p for _, p in pts)
    pad = (hi - lo) * 0.1 or hi * 0.02
    lo, hi = lo - pad, hi + pad
    x = lambda t: L + (t - t0).total_seconds() / max((t1 - t0).total_seconds(), 1) * (W - L - R)
    y = lambda p: T + (hi - p) / (hi - lo) * (H - T - B)
    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Price history in USD">']
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="{L-8}" y="{y(v)+4:.1f}" class="axis" text-anchor="end">${v:,.0f}</text>')
    parts.append(f'<text x="{L}" y="{H-8}" class="axis">{t0:%b %d}</text>'
                 f'<text x="{W-R}" y="{H-8}" class="axis" text-anchor="end">{t1:%b %d %H:%M}</text>')
    for (store, edition), s in series.items():
        if not s:
            continue
        s = s + [(t1, s[-1][1])]  # extend the last known price to "now"
        d = f"M{x(s[0][0]):.1f} {y(s[0][1]):.1f}" + "".join(  # step line: price holds until the next change
            f" H{x(t):.1f} V{y(p):.1f}" for t, p in s[1:])
        dash = ' stroke-dasharray="6 4"' if edition == "china" else ""
        parts.append(f'<path d="{d}" fill="none" stroke="{colors[store]}" stroke-width="2"{dash}>'
                     f'<title>{store} ({EDITION_LABEL[edition]})</title></path>')
    parts.append("</svg>")
    return "".join(parts)


def _series(rows: list[dict], model: dict, rates: dict) -> dict:
    """Per (store, edition): that store's lowest in-stock price (any storage) for the phone, at every change, in USD."""
    state: dict[tuple, float | None] = {}
    out: dict[tuple, list] = defaultdict(list)
    for r in rows:
        if r["model_id"] != model["id"] or r["edition"] not in model["editions"]:
            continue
        line = (r["store"], r["edition"])
        state[(line, r["storage"])] = fx.convert(r["price"], r["currency"], "USD", rates) if r["available"] else None
        t = datetime.strptime(r["time"], "%Y-%m-%dT%H:%M:%SZ")
        best = min((p for (l, _), p in state.items() if l == line and p is not None), default=None)
        if best is not None and (not out[line] or out[line][-1][1] != best):
            out[line].append((t, best))
    return out


def _models(catalog: list[dict], offers: list[dict] = ()) -> list[dict]:
    """One entry per phone model; its Global and China editions are combined so the price difference between them
    is visible side by side. Editions come from catalog.yaml plus whatever the stores actually sell."""
    models: dict[str, dict] = {}
    for ph in catalog:
        m = models.setdefault(ph["id"], {"id": ph["id"], "name": ph["name"], "brand": ph["brand"], "editions": []})
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
                                   "notes": terms.notes(stores_cfg[store]),
                                   "duties": {r: terms.duties_included(stores_cfg[store], r) for r in terms.REGIONS},
                                   "terms_ok": terms_status.get(store, {}).get("ok", True)})
        offers.sort(key=lambda o: (not o["available"], o["usd"]))
        in_stock = [o for o in offers if o["available"]]
        js = lambda o: {k: o[k] for k in ("store_label", "edition", "storage", "link", "money", "pay", "pay_ok", "ship", "notes", "duties")}
        by_storage = defaultdict(list)
        for o in offers:
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
                       "n_stores": len({o["store"] for o in in_stock}), "offers": offers,
                       "by_storage": [(s, by_storage[s]) for s in storages], "compare": compare,
                       "chart": _chart(_series(rows, m, rates), colors)})
    phones.sort(key=lambda p: (p["best"] is None, p["brand"], -(p["best"]["usd"] if p["best"] else 0)))
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    env.filters["spec"] = spec
    ctx = {"updated": latest.get("updated", ""), "fx_date": rates_info.get("date"), "colors": colors,
           "stores": [{"name": s, "label": c.get("label", s), "ok": latest["stores"].get(s, {}).get("ok"),
                       "error": latest["stores"].get(s, {}).get("error", ""), "count": len(latest["stores"].get(s, {}).get("offers", [])),
                       "terms_ok": terms_status.get(s, {}).get("ok", True), "notes": terms.notes(c),
                       "pay": {m: terms.payment_pct(c, m) for m in terms.METHODS},
                       "pay_min": {m: terms.min_order_usd(c, m) for m in terms.METHODS},
                       "ship_notes": _ship_notes(terms.notes(c)["ship"])}
                      for s, c in stores_cfg.items() if c.get("enabled", True)],
           "brands": sorted({p["brand"] for p in phones}), "edition_label": EDITION_LABEL,
           "import_tax_json": json.dumps(yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"])}
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "phones").mkdir(parents=True)
    shutil.copytree("static", OUT / "static")
    (OUT / "index.html").write_text(env.get_template("index.html").render(phones=phones, root="", **ctx))
    for p in phones:
        (OUT / "phones" / f'{p["slug"]}.html').write_text(env.get_template("phone.html").render(p=p, root="../", **ctx))
    print(f"  site: {len(phones)} phone pages -> {OUT}/")
