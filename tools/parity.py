"""One-off parity check: pricechecker/pricing.py against the pricing in today's static/app.js, on the real offers of an
offline build (run `python -m pricechecker.run --build-only --offline` first).

Every offer embedded in build/phones/*.html (id="offers") and in the index rows (data-offers, the lean form), under
every settings combination the tax config allows, goes through pricing.cost and through app.js (tools/parity_appjs.mjs,
one node process for all of it). Also compares, per phone, the page title's price (site._title_price as it was before it
moved onto pricing.py, kept below) with plain pricing.rank, with what app.js puts first on the phone page, and with
today's site._title_price, for EU / card / EUR / EU average. Prints a summary and writes the details as JSON
(default: build/parity.json, next to the build it checked). Exit status 1 when any total or flag differs.

    .venv/bin/python tools/parity.py [out.json]
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pricechecker import pricing, site  # noqa: E402

CURS = ("eur", "usd", "gbp", "cad", "aud")
PAYS = ("card", "paypal", "bank")
TITLE = ("EU", "", "card", "eur")
OFFERS_RE = re.compile(r'<script type="application/json" id="offers">(.*?)</script>', re.S)
TAX_RE = re.compile(r'<script type="application/json" id="import-tax">(.*?)</script>', re.S)
ROW_RE = re.compile(r'data-slug="([^"]+)"[^>]*?data-offers="([^"]*)"', re.S)


def old_title_price(offers, tax_eu_pct, with_offer=False):
    """site._title_price as of commit 72f6969 (before it became a wrapper over pricing.rank), verbatim."""
    best = None
    for o in offers:
        if not o["available"] or o.get("old") or not (o.get("pay_ok") or {}).get("card", True):
            continue
        base = o["money"]["eur"]
        if o.get("promo"):
            base -= base * o["promo"]["pct"] / 100
        adj = (o["pay"].get("card") or 0) * base / 100
        ship = (o["ship"] or {}).get("EU")
        if ship is False:
            continue
        ship_amt = ship["eur"] if ship else 0
        duties = (o.get("duties") or {}).get("EU")
        tax = (base + adj + ship_amt) * tax_eu_pct / 100 if duties is False and tax_eu_pct is not None else 0
        total = base + adj + ship_amt + tax
        unknown = (2 if ship is None else 0) + (0 if duties is True or tax else 1)
        if best is None or (unknown, total) < best[3:5]:
            left = " and ".join(x for x, gone in (("shipping", ship is None), ("import tax", not (duties is True or tax))) if gone)
            best = (total, not left, left, unknown, total, o)
    return (best[:3] + ((best[5],) if with_offer else ())) if best else None


def sweep(tax):
    """Every region in the tax config: EU average + each country, Canada's own rate + each province (as the page's
    JSON has them, so YAML's `ON:` -> True arrives as "true"), the rest with no area; x every payment x every currency."""
    out = [TITLE]
    for region, cfg in tax.items():
        areas = [""] + (list(cfg.get("countries") or {}) if region == "EU" else list(cfg.get("provinces") or {}) if region == "CA" else [])
        out += [(region, a, p, c) for a in areas for p in PAYS for c in CURS if (region, a, p, c) != TITLE]
    return out


def py_view(c: pricing.Cost) -> dict:
    return {"total": c.total, "unknowns": pricing.unknowns(c), "payOk": c.pay_ok, "old": c.old, "approx": c.approx,
            "complete": c.complete, "taxAdded": c.tax_added, "taxEst": c.tax_est, "ship": c.ship,
            "promoPct": c.promo_pct, "adj": c.adj}


def differs(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
        return a != b
    return abs(a - b) >= 0.005   # money and percents: a cent apart counts (totals print rounded to the euro)


def main(out_path="build/parity.json"):
    pages = sorted(Path("build/phones").glob("*.html"))
    pages = [p for p in pages if OFFERS_RE.search(p.read_text())]
    index = Path("build/index.html").read_text()
    tax = json.loads(html.unescape(TAX_RE.search(index).group(1)))
    settings = sweep(tax)
    jobs = []
    for p in pages:
        t = p.read_text()
        offers = json.loads(OFFERS_RE.search(t).group(1))
        page_tax = json.loads(TAX_RE.search(t).group(1))
        assert page_tax == tax, f"{p.name}: tax config differs from the index's"
        live = [i for i, o in enumerate(offers) if o.get("available") and (o.get("ship") or {}).get("EU") is not False]
        jobs.append({"id": "phone:" + p.stem, "offers": offers, "pick": live})
    for slug, raw in ROW_RE.findall(index):
        jobs.append({"id": "index:" + slug, "offers": json.loads(html.unescape(raw)), "pick": None})
    feed = "".join(json.dumps({**j, "tax": tax, "settings": settings}) + "\n" for j in jobs)
    r = subprocess.run(["node", "tools/parity_appjs.mjs"], input=feed, capture_output=True, text=True, check=True)
    js = {x["id"]: x for x in map(json.loads, r.stdout.splitlines())}

    diffs, n = [], 0
    for j in jobs:
        for si, s in enumerate(settings):
            st = pricing.Settings(*s)
            rule = pricing.tax_rule(tax, st)
            for oi, o in enumerate(j["offers"]):
                n += 1
                py, jv = py_view(pricing.cost(o, st, rule)), js[j["id"]]["costs"][si][oi]
                bad = {k: (py[k], jv[k]) for k in py if differs(py[k], jv[k])}
                if bad:
                    diffs.append({"job": j["id"], "settings": s, "offer": oi, "store": o.get("store_label"), "fields": bad})

    titles = []
    rule = pricing.tax_rule(tax, pricing.Settings(*TITLE))
    eu_avg = (tax.get("EU") or {}).get("rate_pct")
    for j in jobs:
        if not j["id"].startswith("phone:"):
            continue
        offers = j["offers"]
        who = lambda o: o and f'{o["store_label"]} {o["edition"]} {o["storage"]}'
        old = old_title_price(offers, eu_avg, with_offer=True)
        ranked = pricing.rank(offers, pricing.Settings(*TITLE), rule)
        new = None
        if ranked:
            o, k = ranked[0]
            new = (k.total, not pricing.left_out(k), pricing.left_out(k), o)
        pi = js[j["id"]]["pick"]
        page = None
        if pi is not None:
            k = pricing.cost(offers[pi], pricing.Settings(*TITLE), rule)
            page = (k.total, not pricing.left_out(k), pricing.left_out(k), offers[pi])
        # what the title, JSON-LD and deals.json carry: the total to the cent and what it leaves out (and, for deals.json, the offer)
        same = lambda a, b: (a is None) == (b is None) and (a is None or (round(a[0], 2) == round(b[0], 2) and a[2] == b[2]))
        view = lambda x: x and [round(x[0], 2), x[2], who(x[3])]
        title = site._title_price(offers, tax, with_offer=True)   # the wrapper the build uses now
        titles.append({"phone": j["id"][6:], "old": view(old), "new": view(new), "page": view(page), "title": view(title),
                       "old_vs_page": same(old, page), "new_vs_page": same(new, page), "old_vs_new": same(old, new),
                       "title_vs_old": same(title, old) and (old and who(old[3])) == (title and who(title[3])),
                       "offer_old_vs_new": (old and who(old[3])) == (new and who(new[3]))})

    summary = {"phone_pages": len(pages), "index_rows": len(jobs) - len(pages), "settings": len(settings),
               "offer_settings_checked": n, "differences": len(diffs),
               "title_old_ne_page": [t["phone"] for t in titles if not t["old_vs_page"]],
               "title_new_ne_page": [t["phone"] for t in titles if not t["new_vs_page"]],
               "title_wrapper_ne_old": [t["phone"] for t in titles if not t["title_vs_old"]],
               "title_old_ne_new": [t["phone"] for t in titles if not t["old_vs_new"]],
               "deals_offer_old_ne_new": [t["phone"] for t in titles if not t["offer_old_vs_new"]]}
    Path(out_path).write_text(json.dumps({"summary": summary, "differences": diffs, "titles": titles}, indent=1))
    print(json.dumps(summary, indent=1))
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
