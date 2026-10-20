"""Generates the static website into build/ from data/latest.json, data/history.csv and config/."""
import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import affiliate, buyer_reports, fx, history, promos, terms

OUT = Path("build")
CURRENCIES = ["USD", "EUR", "GBP", "AUD"]
EDITIONS = ["global", "china"]
EDITION_LABEL = {"global": "Global", "china": "China"}
_GOOGLE: dict = {}


def _google() -> dict:
    """config/google.yaml: Google Play on each brand's China version, and what we call that version."""
    if not _GOOGLE:
        _GOOGLE.update(yaml.safe_load(Path("config/google.yaml").read_text()))
    return _GOOGLE


def ed_labels(brand: str) -> dict:
    """{"global": "Global", "china": "China"} - or "Asia" for brands whose model numbers cover China, Hong Kong and Taiwan."""
    b = _google()["brands"].get(brand.lower(), {})
    return {**EDITION_LABEL, "china": b.get("china_label", EDITION_LABEL["china"])}
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


def _feeds(site_cfg: dict, phones: list[dict], rows: list[dict], stores_cfg: dict, updated_at: datetime | None) -> None:
    """Atom feeds of price changes, so people can follow a phone without an account: feeds/<slug>.xml per phone and
    feeds/all.xml for every phone. Each entry is one store price change, in the store's own currency, with the price before."""
    from xml.sax.saxutils import escape
    base = (site_cfg.get("base_url") or "https://doorprice.app").rstrip("/")
    names = {p["id"]: p["name"] for p in phones}
    labels = {p["id"]: p["ed_label"] for p in phones}
    sym = {"USD": "$", "EUR": "€", "GBP": "£", "AUD": "A$", "HKD": "HK$"}
    money = lambda v, c: f"{sym.get(c, c + ' ')}{v:,.0f}"
    last: dict[tuple, dict] = {}
    entries = []
    for r in rows:   # oldest first: each change knows the price before it
        if r["model_id"] not in names:
            continue
        key = (r["store"], r["model_id"], r["edition"], r["storage"])
        prev = last.get(key)
        if prev is None or (r["available"] == prev["available"] and abs(r["price"] - prev["price"]) < prev["price"] * 0.005):
            last.setdefault(key, r)   # currency-rounding moves (a store re-converting its prices) aren't news
            continue
        last[key] = r
        label = stores_cfg.get(r["store"], {}).get("label", r["store"])
        what = f"{names[r['model_id']]} {labels[r['model_id']][r['edition']]}" + (f" {spec(r['storage'])}" if "/" in r["storage"] else "")
        if r["available"] and not prev["available"]:
            change = f"back in stock at {money(r['price'], r['currency'])}"
        elif not r["available"]:
            change = "out of stock"
        elif r["price"] < prev["price"]:
            change = f"down to {money(r['price'], r['currency'])} (was {money(prev['price'], prev['currency'])})"
        else:
            change = f"up to {money(r['price'], r['currency'])} (was {money(prev['price'], prev['currency'])})"
        entries.append({"model": r["model_id"], "time": r["time"], "title": f"{what} at {label}: {change}",
                        "id": f"{base}/history/{r['model_id']}#{r['time']}-{r['store']}-{r['edition']}-{r['storage']}"})
    entries.reverse()   # newest first

    def write(path: Path, title: str, link: str, items: list[dict]) -> None:
        stamp = items[0]["time"] if items else (f"{updated_at:%Y-%m-%dT%H:%M:%SZ}" if updated_at else "2026-01-01T00:00:00Z")
        body = "".join(f"<entry><title>{escape(e['title'])}</title><id>{escape(e['id'])}</id><updated>{e['time']}</updated>"
                       f'<link href="{escape(base)}/history/{e["model"]}"/></entry>' for e in items[:50])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">'
                        f"<title>{escape(title)}</title><id>{escape(link)}</id><updated>{stamp}</updated>"
                        f'<link href="{escape(link)}"/><author><name>DoorPrice</name></author>{body}</feed>\n')
    for ph in phones:
        write(OUT / "feeds" / f"{ph['slug']}.xml", f"{ph['name']} price changes – DoorPrice", f"{base}/phones/{ph['slug']}",
              [e for e in entries if e["model"] == ph["id"]])
    write(OUT / "feeds" / "all.xml", "Phone price changes – DoorPrice", f"{base}/", entries)


def _seo_files(site_cfg: dict, phones: list[dict], store_names: list[str] = ()) -> None:
    """robots.txt and sitemap.xml for search engines; the sitemap lists absolute URLs, so only once the domain is live."""
    base = (site_cfg.get("base_url") or "").rstrip("/")
    live = bool(site_cfg.get("domain_live") and base)
    robots = "User-agent: *\nAllow: /\n" + (f"Sitemap: {base}/sitemap.xml\n" if live else "")
    (OUT / "robots.txt").write_text(robots)
    if not live:
        return
    paths = ["", "compare", "stores", "methodology", "about", "privacy"] + [f"stores/{n}" for n in store_names] + [f"phones/{p['slug']}" for p in phones] + [f"history/{p['slug']}" for p in phones]
    urls = "".join(f"<url><loc>{base}/{p}</loc></url>" for p in paths)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')


def _usd_money(usd: float | None, rates: dict) -> dict | None:
    return _money({"price": usd, "currency": "USD"}, rates) if usd else None


SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "AUD": "A$"}
LABELS: dict[str, str] = {}   # store key -> name shown in chart readouts; set by build()


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
    parts = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Price history in {cur}, shown in the table below" '
             f'data-t0="{t0:%Y-%m-%dT%H:%M}" data-t1="{t1:%Y-%m-%dT%H:%M}" data-l="{L}" data-r="{W-R}">']
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
        if out[line] or best is not None:   # a line starts at its first in-stock price
            if not out[line] or out[line][-1][1] != best:
                out[line].append((t, best))
    return out


def _charts(rows: list[dict], model: dict, rates: dict, colors: dict, now: datetime | None, storage: str | None = None) -> dict:
    """The chart once per site currency ({"usd": svg, ...}; {} if no history yet), so it follows the visitor's currency.
    History records each store's own price; other currencies are converted at the current ECB rate."""
    out = {c.lower(): _chart(_series(rows, model, rates, storage, c), colors, now, c, ed_labels(model["brand"])) for c in CURRENCIES}
    return out if all(out.values()) else {}


def _all_stats(rows: list[dict], model: dict, rates: dict, now: datetime | None, storage: str | None = None) -> dict:
    """_stats once per site currency, like the charts: {"usd": {...}, ...}; {} if no history."""
    out = {c.lower(): _stats(_series(rows, model, rates, storage, c), now, c) for c in CURRENCIES}
    return out if all(out.values()) else {}


def _tier_chart(rows: list[dict], model: dict, storage: str, rates: dict, colors: dict, now: datetime | None) -> dict:
    """Price history for one RAM/storage option (the toggle under each table on the phone page)."""
    series = _series(rows, model, rates, storage)
    eds = defaultdict(list)   # store -> versions it has lines for, so the legend can follow the version filter
    for s, e in series:
        eds[s].append(e)
    return {"svg": _charts(rows, model, rates, colors, now, storage), "stats": _all_stats(rows, model, rates, now, storage), "stores": {s: " ".join(sorted(eds[s])) for s in sorted(eds)},
            "china": any(e == "china" for _, e in series)}


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


def _product_ld(model: dict, in_stock: list[dict], site_cfg: dict) -> str:
    """schema.org Product + AggregateOffer for search results ("from €X · N offers"): the stores' own prices in EUR
    (what the store charges, as search engines expect), not our delivered totals. Empty when nothing is in stock."""
    if not in_stock:
        return ""
    eur = [o["money"]["eur"] for o in in_stock]
    ld = {"@context": "https://schema.org", "@type": "Product", "name": model["name"], "brand": {"@type": "Brand", "name": model["brand"]},
          "offers": {"@type": "AggregateOffer", "priceCurrency": "EUR", "lowPrice": f"{min(eur):.2f}", "highPrice": f"{max(eur):.2f}",
                     "offerCount": len(in_stock)}}
    base = (site_cfg.get("base_url") or "").rstrip("/")
    if site_cfg.get("domain_live") and base:
        ld["url"] = f"{base}/phones/{model['id']}"
        ld["image"] = f"{base}/static/icons/icon-512.png"
    return json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _specs(sp: dict | None) -> list[tuple[str, str]]:
    """specs.yaml entry -> [("Chip", "Dimensity 9500"), ("Screen", "6.78″"), ...] in a fixed order, skipping blanks."""
    if not sp:
        return []
    screen = sp.get("screen")
    if screen is not None:
        size, _, rest = str(screen).partition(" ")
        screen = f"{size}″" + (f" {rest}" if rest else "")
    rows = [("Chip", sp.get("chip")), ("Screen", screen), ("Battery", sp.get("battery")), ("Charging", sp.get("charging"))]
    return [(k, str(v)) for k, v in rows if v]


def _spec_parts(v: str) -> list[tuple[str, str]]:
    """One spec value -> [(value, tag)] for display on separate lines: "7,200 mAh (China) / 7,100 mAh (Global)" ->
    [("7,200 mAh", "China"), ("7,100 mAh", "Global")]; "7.95″ inside" -> [("7.95″", "inner screen")]; else [(v, "")]."""
    out = []
    for part in v.split(" / "):
        m = re.match(r"^(.*?)\s*\((China|Global|US|EU)\)$", part)
        if m:
            out.append((m[1], m[2]))
        elif part.endswith(" inside"):
            out.append((part[:-7], "inner screen"))
        else:
            out.append((part, ""))
    return out


def _trust(t: dict | None) -> dict | None:
    """stores.yaml trust block, JSON-ready (YAML reads the checked date as a date)."""
    return {**t, "checked": str(t["checked"])} if t and t.get("checked") else t


REGION_CUR = {"EU": "EUR", "UK": "GBP", "US": "USD", "AU": "AUD", "Global": "USD"}   # shipping shown in each region's currency
REGION_LABEL = {"EU": "EU", "UK": "UK", "US": "US", "AU": "Australia", "Global": "Rest of world"}


def _ship_cell(cfg: dict, region: str, rates: dict) -> dict:
    """One store's shipping terms for a region, for the store pages: cost in the region's currency, days, who pays tax."""
    t = ((cfg.get("terms") or {}).get("shipping", {}).get(region)) or {}
    cur, to = t.get("currency", cfg.get("currency", "USD")), REGION_CUR[region]
    amount = t["cost"] if t.get("cost") is not None else t.get("cost_min")
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
            "duties": t.get("duties_included"), "note": t.get("note", "")}


def _store_pages(phones: list[dict], stores_cfg: dict, rates: dict, buyers: dict) -> list[dict]:
    """One page per store with published terms (an EU warehouse is shown on its store's page): trust, terms per Ship-to
    region, payment fees, and every phone it lists with its lowest price against the cheapest store's."""
    pages = []
    for name, cfg in stores_cfg.items():
        if not cfg.get("enabled", True) or cfg.get("part_of") or not (cfg.get("terms") or {}).get("shipping"):
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


def _tax_config(rates: dict) -> dict:
    """config/import_tax.yaml regions, with each courier fee's minimum (EUR) also in the other display currencies,
    since the browser works out the fee in whatever currency the visitor picked."""
    regions = yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"]
    for c in (regions.get("EU") or {}).get("countries", {}).values():
        if c.get("fee"):
            c["fee"]["min_m"] = {cur.lower(): round(fx.convert(c["fee"]["min"], "EUR", cur, rates), 2) for cur in CURRENCIES}
    return regions


def _title_price(offers: list[dict], tax_eu_pct: float | None) -> tuple[float, bool] | None:
    """Cheapest total for the page title and search snippet (a complete total first, as on the page): shipping to the EU, paying by card, in EUR - the same sum
    the browser does (store price, automatic store discount, card fee, shipping, estimated import VAT when the store's
    price excludes it). Returns (total, complete); complete = shipping known and import tax settled either way.
    Ranked like the page (app.js better()): fewer unknowns first - unlisted shipping counts 2, import tax that may be
    due 1 (a "from €10" shipping floor is a known, approximate cost) - then the lower total."""
    best = None
    for o in offers:
        if not o["available"] or o.get("old") or not (o.get("pay_ok") or {}).get("card", True):
            continue
        base = o["money"]["eur"]
        if o.get("promo"):
            base -= base * o["promo"]["pct"] / 100
        adj = (o["pay"].get("card") or 0) * base / 100
        ship = (o["ship"] or {}).get("EU")
        ship_amt = ship["eur"] if ship else 0
        duties = (o.get("duties") or {}).get("EU")
        tax = (base + adj + ship_amt) * tax_eu_pct / 100 if duties is False and tax_eu_pct is not None else 0
        total = base + adj + ship_amt + tax
        unknown = (2 if ship is None else 0) + (0 if duties is True or tax else 1)
        if best is None or (unknown, total) < best[2:]:
            best = (total, ship is not None and (duties is True or bool(tax)), unknown, total)
    return best[:2] if best else None


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


OLD_AFTER = timedelta(hours=48)


def _too_old(checked: str | None, updated_at: datetime | None) -> bool:
    """True when a store's last successful check is more than OLD_AFTER before this run: its prices are then shown
    as "last checked …" and never lead a ranking, the page title or search data."""
    if not checked or not updated_at:
        return False
    try:
        return updated_at - datetime.strptime(checked, "%Y-%m-%dT%H:%M:%SZ") > OLD_AFTER
    except ValueError:
        return False


def build(catalog: list[dict], stores_cfg: dict, rates_info: dict, terms_status: dict | None = None) -> None:
    rates = rates_info["rates"]
    terms_status = terms_status or {}
    latest = history.load_latest()
    rows = history.load_history()
    LABELS.update({k: v.get("label", k) for k, v in stores_cfg.items()})
    store_names = list(stores_cfg)
    colors = {s: STORE_COLORS[i % len(STORE_COLORS)] for i, s in enumerate(store_names)}
    try:
        updated_at = datetime.strptime(latest.get("updated", ""), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        updated_at = None
    tax_cfg = _tax_config(rates)
    tax_eu = (tax_cfg.get("EU") or {}).get("rate_pct")
    variants = yaml.safe_load(Path("config/variants.yaml").read_text()) or {}   # RAM/storage options each brand makes
    site_cfg = yaml.safe_load(Path("config/site.yaml").read_text()) if Path("config/site.yaml").exists() else {}
    specs = (yaml.safe_load(Path("config/specs.yaml").read_text()) or {}).get("phones") or {}   # key specs, hand-entered
    google = _google()   # Google Play on each brand's China version
    buyers = buyer_reports.summary(updated_at.replace(tzinfo=timezone.utc) if updated_at else None)   # approved buyer reports per store, region
    # only stores still enabled in stores.yaml: a switched-off or removed store's last prices must not show as current
    live_stores = {s: st for s, st in latest["stores"].items() if s in stores_cfg and stores_cfg[s].get("enabled", True)}
    old = {s: _too_old(st.get("checked"), updated_at) for s, st in live_stores.items()}
    by_model = defaultdict(list)   # history rows per phone, so each phone's charts and trends scan only its own rows
    for r in rows:
        by_model[r["model_id"]].append(r)
    phones = []
    for m in _models(catalog, [o for st in live_stores.values() for o in st["offers"]]):
        mrows = by_model[m["id"]]
        offers = []
        for store, st in live_stores.items():
            # an EU-warehouse section (part_of) shares its store's promotions, coupons and their watch state
            shop = stores_cfg[store]["part_of"] if stores_cfg[store].get("part_of") in stores_cfg else store
            for o in st["offers"]:
                if o["model_id"] == m["id"] and o["edition"] in m["editions"]:
                    usd = (o.get("prices") or {}).get("USD") or fx.convert(o["price"], o["currency"], "USD", rates)
                    offers.append({**o, "store_label": stores_cfg[store].get("label", store), "stale": not st.get("ok", True), "old": old[store],
                                   "link": affiliate.link(o["url"], stores_cfg[store]), "money": _money(o, rates), "usd": usd,
                                   "pay": {k: terms.payment_pct(stores_cfg[store], k) for k in terms.METHODS},
                                   "pay_ok": {k: terms.payment_available(stores_cfg[store], k, usd) for k in terms.METHODS},
                                   "ship": {r: terms.shipping(stores_cfg[store], r, o, rates) for r in terms.REGIONS},
                                   "notes": terms.notes(stores_cfg[store]), "promo": terms.promo(stores_cfg[shop]) if promos.active(shop, stores_cfg[shop]) else None,
                                   "coupons": promos.coupons(shop, stores_cfg[shop]),
                                   "duties": {r: terms.duties_included(stores_cfg[store], r) for r in terms.REGIONS},
                                   "days": {r: terms.delivery(stores_cfg[store], r) for r in terms.REGIONS},
                                   "buyers": buyers.get(store),
                                   "gplay": stores_cfg[store].get("google_play") or stores_cfg.get(stores_cfg[store].get("part_of"), {}).get("google_play")
                                            if o["edition"] == "china" else None,
                                   "trust": _trust(stores_cfg[store].get("trust") or stores_cfg.get(stores_cfg[store].get("part_of"), {}).get("trust")),
                                   "trend": _trend(mrows, m["id"], {**o, "store": store}, updated_at),
                                   "terms_ok": terms_status.get(store, {}).get("ok", True)})
        offers.sort(key=lambda o: (not o["available"], o["usd"]))
        offers.sort(key=lambda o: o["old"])   # stable: current prices first, a store that hasn't answered for days last
        in_stock = [o for o in offers if o["available"] and not o["old"]]   # what the index, compare, title and search data rank
        js = lambda o: {k: o[k] for k in ("store_label", "edition", "storage", "link", "money", "pay", "pay_ok", "ship", "notes", "duties", "promo", "coupons", "days", "trend", "store", "trust", "buyers", "gplay", "old")}
        # index rows: only what the ranking needs (store notes, links and coupons are for the phone page), so the page stays light
        lean = lambda o: {**{k: o[k] for k in ("store_label", "edition", "storage", "money", "pay", "pay_ok", "ship", "duties", "trend")},
                          "promo": {k: o["promo"][k] for k in ("pct", "stacks_with_bank") if k in o["promo"]} if o.get("promo") else None}
        # phone page: every offer (out of stock too) - the browser builds the price grid, answer and store list from it
        full = lambda o: {**js(o), "available": o["available"], "stale": o["stale"], "store": o["store"]}
        by_storage = defaultdict(list)
        for o in offers:
            o["js"] = js(o)   # per storage tier: the browser shows each version's cheapest total in the tier header
            by_storage[o["storage"]].append(o)
        storages = sorted(by_storage, key=_storage_key)
        eds = [{"edition": e, "label": ed_labels(m["brand"])[e],
                "best": next((o for o in in_stock if o["edition"] == e), None),
                "listed": any(o["edition"] == e for o in offers)} for e in m["editions"]]
        # Global vs China at the same configuration: the browser picks the cheapest total in each cell
        compare = [{"storage": s, "cells": [json.dumps([js(o) for o in in_stock if o["storage"] == s and o["edition"] == e],
                                                       separators=(",", ":")) for e in m["editions"]]}
                   for s in storages if len(m["editions"]) > 1]
        phones.append({**m, "slug": m["id"], "best": in_stock[0] if in_stock else None, "eds": eds,
                       "offers_json": json.dumps([lean(o) for o in in_stock], separators=(",", ":")),  # re-ranked in the browser
                       "all_json": json.dumps([full(o) for o in offers], separators=(",", ":")),
                       "n_stores": len({o["store"] for o in in_stock}), "offers": offers,
                       "by_storage": [(s, by_storage[s]) for s in storages], "compare": compare,
                       "made": {e: [str(x) for x in v["made"]] for e, v in (variants.get(m["id"]) or {}).items()},
                       "title_price": _title_price(offers, tax_eu),
                       "ld": _product_ld(m, in_stock, site_cfg),
                       "specs": _specs(specs.get(m["id"])),
                       "ed_label": ed_labels(m["brand"]),
                       "google": {**google["brands"].get(m["brand"].lower(), google["brands"]["default"]),
                                  "caveat": google["caveat"] if m["brand"].lower() != "huawei" else ""},
                       "chart": _charts(mrows, m, rates, colors, updated_at),
                       "chart_stats": _all_stats(mrows, m, rates, updated_at),
                       "tier_charts": {s: _tier_chart(mrows, m, s, rates, colors, updated_at) for s in storages}, "changes": _changes(mrows, m, stores_cfg, rates),
                       "series_stores": sorted({s for s, _ in _series(mrows, m, rates)})})
    phones.sort(key=lambda p: p["name"])
    phones.sort(key=lambda p: p["announced"], reverse=True)   # newest first; the index can re-sort by price or saving
    # end of each phone page: the same brand's other phones (newest first) and the nearest in price from other brands
    card = lambda q: {"name": q["name"], "slug": q["slug"], "announced": q["announced"], "editions": q["editions"], "ed_label": q["ed_label"],
                      "money": q["best"]["money"] if q["best"] else None}
    for ph in phones:
        same = [q for q in phones if q["brand"] == ph["brand"] and q is not ph][:4]
        others = [q for q in phones if q["brand"] != ph["brand"] and q["best"]]
        near = sorted(others, key=lambda q: abs(q["best"]["usd"] - ph["best"]["usd"]))[:3] if ph["best"] else []
        ph["related"] = {"brand": [card(q) for q in same], "near": [card(q) for q in near]}
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    env.filters["spec"] = spec
    env.filters["spec_parts"] = _spec_parts
    env.filters["month"] = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%b %Y") if d else ""
    upd = latest.get("updated", "")
    try:
        upd_label = datetime.strptime(upd, "%Y-%m-%dT%H:%M:%SZ").strftime("%-d %b, %H:%M UTC")
    except ValueError:
        upd_label = upd
    # ?v=<content hash> on the script and stylesheet: browsers cache them for hours (Cloudflare's default), and an old
    # app.js on a new page breaks it (Chrome on Android kept a pre-Phase-2 app.js and the brand filters stopped working)
    ver = {f: hashlib.sha256(Path("static", f).read_bytes()).hexdigest()[:10] for f in ("app.js", "style.css")}
    ctx = {"asset_v": ver, "updated": upd, "updated_label": upd_label, "fx_date": rates_info.get("date"), "colors": colors,
           "stores": [{"name": s, "label": c.get("label", s), "ok": latest["stores"].get(s, {}).get("ok"), "part_of": c.get("part_of"),
                       "error": latest["stores"].get(s, {}).get("error", ""), "count": len(latest["stores"].get(s, {}).get("offers", [])),
                       "terms_ok": terms_status.get(s, {}).get("ok", True), "notes": terms.notes(c),
                       "pay": {m: terms.payment_pct(c, m) for m in terms.METHODS},
                       "pay_min": {m: _usd_money(terms.min_order_usd(c, m), rates) for m in terms.METHODS},
                       "ship_notes": _ship_notes(terms.notes(c)["ship"])}
                      for s, c in stores_cfg.items() if c.get("enabled", True)],
           "month": updated_at.strftime("%B %Y") if updated_at else "",   # "October 2026" in page titles
           "site": site_cfg,
           "brands": sorted({p["brand"] for p in phones}), "edition_label": EDITION_LABEL,
           "report_stores": [{"name": s, "label": c.get("label", s)} for s, c in stores_cfg.items() if c.get("enabled", True)],
           "report_countries": sorted(buyer_reports.COUNTRIES.items(), key=lambda kv: (kv[0] == "XX", kv[1])),
           "nav_phones": [{"name": p["name"], "slug": p["slug"]} for p in phones],   # header search suggestions on every page
           "eu_countries": sorted(tax_cfg["EU"]["countries"].items(), key=lambda kv: kv[1]["name"]), "eu_avg_vat": tax_cfg["EU"]["rate_pct"],
           "store_page_map": json.dumps({n: c.get("part_of") or n for n, c in stores_cfg.items() if c.get("enabled", True)
                                         and (c.get("terms") or {}).get("shipping")}),
           "tax_regions": tax_cfg, "import_tax_json": json.dumps(tax_cfg)}
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "phones").mkdir(parents=True)
    (OUT / "history").mkdir()
    shutil.copytree("static", OUT / "static")
    shutil.copy("static/favicon.ico", OUT / "favicon.ico")   # browsers ask for /favicon.ico at the root
    # Cloudflare Pages caching: app.js and style.css are linked with ?v=<content hash>, so a year is safe; fonts and
    # icons keep their names when they change, so a month. Pages themselves keep the default (revalidate every visit).
    (OUT / "_headers").write_text("/static/app.js\n  Cache-Control: public, max-age=31536000, immutable\n"
                                  "/static/style.css\n  Cache-Control: public, max-age=31536000, immutable\n"
                                  "/static/fonts/*\n  Cache-Control: public, max-age=2592000\n"
                                  "/static/icons/*\n  Cache-Control: public, max-age=2592000\n")
    if site_cfg.get("indexnow_key"):   # IndexNow ownership file (pricechecker/indexnow.py)
        (OUT / f'{site_cfg["indexnow_key"]}.txt').write_text(site_cfg["indexnow_key"])
    (OUT / "index.html").write_text(env.get_template("index.html").render(phones=phones, root="", path="", **ctx))
    for p in phones:
        (OUT / "phones" / f'{p["slug"]}.html').write_text(env.get_template("phone.html").render(p=p, root="../", path=f'phones/{p["slug"]}', **ctx))
        (OUT / "history" / f'{p["slug"]}.html').write_text(env.get_template("history.html").render(p=p, root="../", path=f'history/{p["slug"]}', **ctx))
    # /compare: every phone's specs and in-stock offers in one JSON block; the browser shows up to three side by side
    # (picked in the page, kept in the URL hash so a comparison can be shared) and prices them for the chosen Ship-to
    cmp = [{"s": p["slug"], "n": p["name"], "b": p["brand"], "d": p["announced"], "e": p["editions"], "cl": p["ed_label"]["china"],
            "sp": [[k, _spec_parts(v)] for k, v in p["specs"]], "g": p["google"]["short"] if "china" in p["editions"] else "",
            "st": [st for st, _ in p["by_storage"]], "o": json.loads(p["offers_json"])}
           for p in sorted(phones, key=lambda q: q["name"])]
    (OUT / "compare.html").write_text(env.get_template("compare.html").render(
        root="", path="compare", cmp_phones=cmp, cmp_json=json.dumps(cmp, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"), **ctx))
    store_pages = _store_pages(phones, stores_cfg, rates, buyers)
    (OUT / "stores").mkdir()
    (OUT / "stores.html").write_text(env.get_template("stores.html").render(root="", path="stores", store_pages=store_pages, **ctx))
    for sp in store_pages:
        (OUT / "stores" / f'{sp["name"]}.html').write_text(env.get_template("store.html").render(
            root="../", path=f'stores/{sp["name"]}', sp=sp, **ctx))
    for page in ("about", "methodology", "privacy"):   # /about and /privacy (affiliate networks look for both)
        (OUT / f"{page}.html").write_text(env.get_template(f"{page}.html").render(phones=phones, root="", path=page, **ctx))
    _seo_files(ctx["site"], phones, [sp["name"] for sp in store_pages])
    _feeds(ctx["site"], phones, rows, stores_cfg, updated_at)
    print(f"  site: {len(phones)} phone pages + price history pages -> {OUT}/")
