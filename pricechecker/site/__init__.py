"""Generates the static website into build/ from data/latest.json, data/history/ and config/.

context.load() reads every input once (SiteData), offers.assemble() makes the per-phone dicts, each pages/ module
renders its pages to {path: html}, seo makes robots.txt, sitemap.xml and the feeds; only build() writes files."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import terms
from . import assets, blocks, cards, context, data_files, offers, seo
from .charts import (
    LABELS,
    _all_stats,
    _chart,
    _charts,
    _series,
    _stats,
    _ticks,
    _tier_chart,
    _trend,
)
from .common import (
    CURRENCIES,
    EDITION_LABEL,
    EDITIONS,
    STORE_COLORS,
    SYMBOL,
    _money,
    _spec_parts,
    _specs,
    _storage_key,
    _usd_money,
    ed_labels,
    spec,
)
from .context import SiteData, _ship_notes, _tax_config
from .offers import OLD_AFTER, _changes, _models, _too_old, _trust
from .pages import compare, drops, home, phone, static, stores
from .pages import history as history_pages
from .pages import specs as specs_pages
from .pages.stores import REGION_CUR, REGION_LABEL, _ship_cell, _store_pages
from .seo import _feeds, _product_ld, _seo_files, _title_price

__all__ = ["CURRENCIES", "EDITIONS", "EDITION_LABEL", "LABELS", "OLD_AFTER", "OUT", "REGION_CUR", "REGION_LABEL", "STORE_COLORS",
           "SYMBOL", "SiteData", "_all_stats", "_changes", "_chart", "_charts", "_feeds", "_models", "_money", "_product_ld",
           "_seo_files", "_series", "_ship_cell", "_ship_notes", "_spec_parts", "_specs", "_stats", "_storage_key",
           "_store_pages", "_tax_config", "_ticks", "_tier_chart", "_title_price", "_too_old", "_trend", "_trust",
           "_usd_money", "build", "ed_labels", "spec"]

OUT = Path("build")
PAGES = (home, drops, phone, specs_pages, history_pages, compare, stores, static)


def _write(files: dict[str, str]) -> None:
    """Write {path relative to build/: text}, making folders as needed."""
    for rel, text in files.items():
        path = OUT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())
    env.filters["spec"] = spec
    env.filters["spec_parts"] = _spec_parts
    env.filters["month"] = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%b %Y") if d else ""
    blocks.register(env)
    return env


def _share_cards(phones: list[dict], ctx: dict) -> None:
    """Link-preview images: cards/<slug>.png per phone with its cheapest delivered price (EU, card, in EUR - the page
    title's number) and cards/site.png for every other page. ?v= changes with the card's text, so a new share shows
    the new price instead of a platform's cached image."""
    n_stores = len({s["name"] for s in ctx["stores"] if s["ok"] is not None and not s["part_of"]})
    cards.site_card(OUT / "cards" / "site.png", len(phones), n_stores)
    ctx["site_card_v"] = hashlib.sha256(f"{len(phones)}/{n_stores}".encode()).hexdigest()[:8]
    for p in phones:
        tp = p["title_price"]
        price = f"from €{tp[0]:,.0f}" if tp else None
        note = ("delivered to the EU" if tp[1] else f"+ {tp[2]}, " + ("to the EU" if "shipping" in tp[2] else "delivered to the EU")) if tp else ""
        eds = [(e, p["ed_label"][e]) for e in p["editions"]]
        cards.phone_card(OUT / "cards" / f'{p["slug"]}.png', p["name"], eds, price, note, p["n_stores"])
        p["card_v"] = hashlib.sha256(f'{p["name"]}|{eds}|{price}|{note}|{p["n_stores"]}'.encode()).hexdigest()[:8]
    # each phone's headline price, for the Telegram price-drop channel (pricechecker/telegram.py) - not linked from any page
    deals = []
    for p in phones:
        tp, o = p["title_price"], p["title_offer"]
        if tp and o:
            deals.append({"slug": p["slug"], "name": p["name"], "eur": round(tp[0], 2), "left": tp[2], "store": o["store_label"],
                          "edition": p["ed_label"][o["edition"]], "storage": o["storage"], "n_stores": p["n_stores"]})
    (OUT / "deals.json").write_text(json.dumps({"updated": ctx["updated"], "phones": deals}, ensure_ascii=False, indent=0))



def build(catalog: list[dict], stores_cfg: dict, rates_info: dict, terms_status: dict | None = None) -> None:
    data = context.load(catalog, stores_cfg, rates_info, terms_status)
    LABELS.update({k: v.get("label", k) for k, v in stores_cfg.items()})
    phones = offers.assemble(data)
    env = _env()
    ctx = context.page_context(data, phones)
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "phones").mkdir(parents=True)
    (OUT / "history").mkdir()
    shutil.copytree("static", OUT / "static", ignore=shutil.ignore_patterns("package.json"))  # package.json only makes node read pricing.js as a module
    for name, (text, _) in assets.versioned_modules(Path("static/js")).items():   # imports between modules get ?v=<hash>
        (OUT / "static/js" / name).write_text(text)
    shutil.copy("static/favicon.ico", OUT / "favicon.ico")   # browsers ask for /favicon.ico at the root
    # Cloudflare Pages caching: app.js, style.css, d.css and js/*.js are linked with ?v=<content hash>, so a year is safe; fonts and
    # icons keep their names when they change, so a month. Pages themselves keep the default (revalidate every visit).
    (OUT / "_headers").write_text("/static/app.js\n  Cache-Control: public, max-age=31536000, immutable\n"
                                  "/static/style.css\n  Cache-Control: public, max-age=31536000, immutable\n"
                                  "/static/d.css\n  Cache-Control: public, max-age=31536000, immutable\n"
                                  "/static/js/*\n  Cache-Control: public, max-age=31536000, immutable\n"
                                  "/static/fonts/*\n  Cache-Control: public, max-age=2592000\n"
                                  "/static/icons/*\n  Cache-Control: public, max-age=2592000\n"
                                  "/data/v1/*\n  Cache-Control: public, max-age=31536000, immutable\n")   # names carry a content hash
    if data.site_cfg.get("indexnow_key"):   # IndexNow ownership file (pricechecker/indexnow.py)
        (OUT / f'{data.site_cfg["indexnow_key"]}.txt').write_text(data.site_cfg["indexnow_key"])
    files = data_files.write(data, OUT, phones)   # build/data/v1/: the browser's phone, home and tax files
    ctx["data_files"], ctx["tax_file"] = files, files["tax"]   # published paths, for the pages that load them
    ctx["home_files"] = {r: files[f"home/{r}"] for r in terms.REGIONS}   # the home page's parts per region
    _share_cards(phones, ctx)   # also sets the cards' ?v= in ctx and on each phone, so it comes before the pages
    (OUT / "stores").mkdir()
    for page in PAGES:
        _write(page.render(env, data, ctx, phones))
    _write(seo._seo_files(ctx["site"], phones, stores.page_names(stores_cfg)))
    _write(seo._feeds(ctx["site"], phones, data.rows_all, stores_cfg, data.updated_at, drops.this_week(data, phones)))
    print(f"  site: {len(phones)} phone pages + price history pages -> {OUT}/")
