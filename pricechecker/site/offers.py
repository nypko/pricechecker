"""Per phone: every store's offers with terms, payment, shipping, trend and trust attached, plus what each page shows
from them (charts, stats, compare cells, title price, related phones). assemble() returns the phone dicts the pages use."""
import json
from collections import defaultdict
from datetime import datetime, timedelta

from .. import affiliate, fx, normalize, promos, terms
from .charts import _all_stats, _charts, _series, _tier_chart, _trend
from .common import EDITIONS, _money, _specs, _storage_key, ed_labels
from .context import SiteData
from .seo import _product_ld, _title_price

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


def _trust(t: dict | None) -> dict | None:
    """stores.yaml trust block, JSON-ready (YAML reads the checked date as a date)."""
    return {**t, "checked": str(t["checked"])} if t and t.get("checked") else t


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


def assemble(data: SiteData) -> list[dict]:
    """One dict per phone, newest first, with its offers and everything its pages show; `related` links them up."""
    stores_cfg, rates, terms_status, updated_at = data.stores_cfg, data.rates, data.terms_status, data.updated_at
    live_stores, buyers, tax_cfg, specs, google, variants = data.live_stores, data.buyers, data.tax_cfg, data.specs, data.google, data.variants
    site_cfg, colors = data.site_cfg, data.colors
    old = {s: _too_old(st.get("checked"), updated_at) for s, st in live_stores.items()}
    by_model = defaultdict(list)   # history rows per phone, so each phone's charts and trends scan only its own rows
    for r in data.rows:
        by_model[r["model_id"]].append(r)
    all_by_model = defaultdict(list)
    for r in data.rows_all:
        all_by_model[r["model_id"]].append(r)
    phones = []
    for m in _models(data.catalog, [o for st in live_stores.values() for o in st["offers"]]):
        mrows = by_model[m["id"]]
        offers = []
        for store, st in live_stores.items():
            # an EU-warehouse section (part_of) shares its store's promotions, coupons and their watch state
            shop = stores_cfg[store]["part_of"] if stores_cfg[store].get("part_of") in stores_cfg else store
            for o in st["offers"]:
                if normalize._CHINA_UNIT.search(o.get("title") or ""):   # saved before the rule existed: same verdict now
                    o = {**o, "edition": "china"}
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
                                   "grom": 1 if normalize.GLOBAL_ROM.search(o.get("title") or "") else 0,   # China unit, global software
                                   "gplay": stores_cfg[store].get("google_play") or stores_cfg.get(stores_cfg[store].get("part_of"), {}).get("google_play")
                                            if o["edition"] == "china" else None,
                                   "trust": _trust(stores_cfg[store].get("trust") or stores_cfg.get(stores_cfg[store].get("part_of"), {}).get("trust")),
                                   "trend": _trend(mrows, m["id"], {**o, "store": store}, updated_at),
                                   "terms_ok": terms_status.get(store, {}).get("ok", True)})
        offers.sort(key=lambda o: (not o["available"], o["usd"]))
        offers.sort(key=lambda o: o["old"])   # stable: current prices first, a store that hasn't answered for days last
        in_stock = [o for o in offers if o["available"] and not o["old"]]   # what the index, compare, title and search data rank
        js = lambda o: {k: o[k] for k in ("store_label", "edition", "storage", "link", "money", "pay", "pay_ok", "ship", "notes", "duties", "promo", "coupons", "days", "trend", "store", "trust", "buyers", "gplay", "old", "grom")}
        # index rows: only what the ranking needs (store notes, links and coupons are for the phone page), so the page stays light
        lean = lambda o: {**{k: o[k] for k in ("store_label", "edition", "storage", "money", "pay", "pay_ok", "ship", "duties", "trend", "grom")},
                          "promo": {k: o["promo"][k] for k in ("pct", "stacks_with_bank") if k in o["promo"]} if o.get("promo") else None}
        # phone page: every offer (out of stock too) - the browser builds the price grid, answer and store list from it
        full = lambda o: {**js(o), "available": o["available"], "stale": o["stale"], "store": o["store"]}  # noqa: B023 - used in this pass only
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
                       "title_price": _title_price(offers, tax_cfg),
                       "title_offer": (_title_price(offers, tax_cfg, with_offer=True) or [None] * 4)[3],
                       "ld": _product_ld(m, in_stock, site_cfg),
                       "specs": _specs(specs.get(m["id"])),
                       "ed_label": ed_labels(m["brand"]),
                       "google": {**google["brands"].get(m["brand"].lower(), google["brands"]["default"]),
                                  "caveat": google["caveat"] if m["brand"].lower() != "huawei" else ""},
                       "chart": _charts(mrows, m, rates, colors, updated_at),
                       "chart_stats": _all_stats(mrows, m, rates, updated_at),
                       "tier_charts": {s: _tier_chart(mrows, m, s, rates, colors, updated_at) for s in storages}, "changes": _changes(all_by_model[m["id"]], m, stores_cfg, rates),
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
    return phones
