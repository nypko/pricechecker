"""Everything the site is built from, loaded once: the catalog, store config, exchange rates, latest prices, price
history, import tax, variants, specs, site settings, Google Play notes and buyer reports (SiteData) - and the template
context every page shares (page_context)."""
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .. import buyer_reports, fx, history, terms
from .. import specs as specs_cfg
from . import assets
from .common import CURRENCIES, EDITION_LABEL, STORE_COLORS, _google, _usd_money


@dataclass
class SiteData:
    catalog: list[dict]              # config/catalog.yaml entries, one per phone edition
    stores_cfg: dict                 # config/stores.yaml stores, by key (disabled ones included)
    rates_info: dict                 # fx.rates() / fx.cached(): {"rates": ..., "date": ...}
    rates: dict                      # rates_info["rates"]
    terms_status: dict               # terms.check_pages() / terms.saved_status(), by store ({} when not given)
    latest: dict                     # data/latest.json: {"updated": ..., "stores": {key: {"ok", "checked", "offers", ...}}}
    rows_all: list[dict]             # every recorded change: history pages and feeds
    rows: list[dict]                 # the last 3 months of changes: charts, trends and stats
    updated_at: datetime | None      # latest["updated"] parsed (naive UTC); None if missing or malformed
    tax_cfg: dict                    # config/import_tax.yaml regions, EU courier fee minimums in every site currency
    variants: dict                   # config/variants.yaml: RAM/storage options each brand makes
    site_cfg: dict                   # config/site.yaml, with testing/indexnow_key overridden when DOORPRICE_ENV=testing
    specs: dict                      # phone id -> key specs block from config/specs/ (or None)
    spec_sheets: dict                # phone id -> the whole sheet from config/specs/ (bands, groups, ...)
    google: dict                     # config/google.yaml: Google Play on each brand's China version
    buyers: dict                     # approved buyer reports per store and region (buyer_reports.summary)
    live_stores: dict                # latest["stores"] limited to stores still enabled in stores.yaml
    colors: dict                     # store key -> chart line colour, by stores.yaml order


def _tax_config(rates: dict) -> dict:
    """config/import_tax.yaml regions, with each courier fee's minimum (EUR) also in the other display currencies,
    since the browser works out the fee in whatever currency the visitor picked."""
    regions = yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"]
    for c in (regions.get("EU") or {}).get("countries", {}).values():
        if c.get("fee"):
            c["fee"]["min_m"] = {cur.lower(): round(fx.convert(c["fee"]["min"], "EUR", cur, rates), 2) for cur in CURRENCIES}
    return regions


def load(catalog: list[dict], stores_cfg: dict, rates_info: dict, terms_status: dict | None = None) -> SiteData:
    rates = rates_info["rates"]
    terms_status = terms_status or {}
    latest = history.load_latest()
    rows_all = history.load_history()        # every change: history pages and feeds
    rows = history.load_history(months=3)    # charts, trends and stats only look back a few weeks
    store_names = list(stores_cfg)
    colors = {s: STORE_COLORS[i % len(STORE_COLORS)] for i, s in enumerate(store_names)}
    try:
        updated_at = datetime.strptime(latest.get("updated", ""), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        updated_at = None
    tax_cfg = _tax_config(rates)
    variants = yaml.safe_load(Path("config/variants.yaml").read_text()) or {}   # RAM/storage options each brand makes
    site_cfg = yaml.safe_load(Path("config/site.yaml").read_text()) if Path("config/site.yaml").exists() else {}
    if os.environ.get("DOORPRICE_ENV") == "testing":   # testing.doorprice.app: banner, hidden from search engines, no IndexNow key
        site_cfg = {**site_cfg, "testing": True, "indexnow_key": None}
    spec_sheets = specs_cfg.load()   # one file per phone in config/specs/
    specs = {i: sheet.get("key") for i, sheet in spec_sheets.items()}   # key specs only
    google = _google()   # Google Play on each brand's China version
    buyers = buyer_reports.summary(updated_at.replace(tzinfo=UTC) if updated_at else None)   # approved buyer reports per store, region
    # only stores still enabled in stores.yaml: a switched-off or removed store's last prices must not show as current
    live_stores = {s: st for s, st in latest["stores"].items() if s in stores_cfg and stores_cfg[s].get("enabled", True)}
    return SiteData(catalog=catalog, stores_cfg=stores_cfg, rates_info=rates_info, rates=rates, terms_status=terms_status,
                    latest=latest, rows_all=rows_all, rows=rows, updated_at=updated_at, tax_cfg=tax_cfg, variants=variants,
                    site_cfg=site_cfg, specs=specs, spec_sheets=spec_sheets, google=google, buyers=buyers, live_stores=live_stores, colors=colors)


def _ship_notes(by_region: dict) -> list[tuple[str, list[str]]]:
    """{'EU': a, 'UK': b, 'US': b} -> [(a, ['EU']), (b, ['UK', 'US'])]: identical terms listed once."""
    grouped: dict[str, list[str]] = {}
    for region, note in by_region.items():
        if note:
            grouped.setdefault(note, []).append(region)
    return list(grouped.items())


def page_context(data: SiteData, phones: list[dict]) -> dict:
    """The template variables every page gets (header, footer, Ship-to and currency pickers, report form)."""
    latest, stores_cfg, terms_status, rates, tax_cfg = data.latest, data.stores_cfg, data.terms_status, data.rates, data.tax_cfg
    upd = latest.get("updated", "")
    try:
        upd_label = datetime.strptime(upd, "%Y-%m-%dT%H:%M:%SZ").strftime("%-d %b, %H:%M UTC")
    except ValueError:
        upd_label = upd
    # ?v=<content hash> on the script and stylesheet: browsers cache them for hours (Cloudflare's default), and an old
    # app.js on a new page breaks it (Chrome on Android kept a pre-Phase-2 app.js and the brand filters stopped working)
    # keyed by path relative to static/: app.js and style.css (old design, removed with it), d.css and every js/*.js module
    ver = {f: hashlib.sha256(Path("static", f).read_bytes()).hexdigest()[:10] for f in ("app.js", "style.css", "d.css")}
    ver.update({f"js/{n}": h for n, (_, h) in assets.versioned_modules(Path("static/js")).items()})   # hash of the rewritten module
    return {"asset_v": ver, "updated": upd, "updated_label": upd_label, "fx_date": data.rates_info.get("date"), "colors": data.colors,
            "stores": [{"name": s, "label": c.get("label", s), "ok": latest["stores"].get(s, {}).get("ok"), "part_of": c.get("part_of"),
                        "error": latest["stores"].get(s, {}).get("error", ""), "count": len(latest["stores"].get(s, {}).get("offers", [])),
                        "terms_ok": terms_status.get(s, {}).get("ok", True), "notes": terms.notes(c),
                        "pay": {m: terms.payment_pct(c, m) for m in terms.METHODS},
                        "pay_min": {m: _usd_money(terms.min_order_usd(c, m), rates) for m in terms.METHODS},
                        "ship_notes": _ship_notes(terms.notes(c)["ship"])}
                       for s, c in stores_cfg.items() if c.get("enabled", True)],
            "month": data.updated_at.strftime("%B %Y") if data.updated_at else "",   # "October 2026" in page titles
            "site": data.site_cfg,
            "brands": sorted({p["brand"] for p in phones}), "edition_label": EDITION_LABEL,
            "report_stores": [{"name": s, "label": c.get("label", s)} for s, c in stores_cfg.items() if c.get("enabled", True)],
            "report_countries": sorted(buyer_reports.COUNTRIES.items(), key=lambda kv: (kv[0] == "XX", kv[1])),
            "nav_phones": [{"name": p["name"], "slug": p["slug"]} for p in phones],   # header search suggestions on every page
            "eu_countries": sorted(tax_cfg["EU"]["countries"].items(), key=lambda kv: kv[1]["name"]), "eu_avg_vat": tax_cfg["EU"]["rate_pct"],
            "ca_provinces": sorted(tax_cfg["CA"]["provinces"].items(), key=lambda kv: kv[1]["name"]),
            "store_page_map": json.dumps({n: c.get("part_of") or n for n, c in stores_cfg.items() if c.get("enabled", True)
                                          and (c.get("terms") or {}).get("shipping")}),
            "tax_regions": tax_cfg, "import_tax_json": json.dumps(tax_cfg)}
