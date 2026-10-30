"""The home page (spec §5.1) and the 404 page. Every phone is a `home_row` block (templates/_d/blocks.html) rendered for
the default settings from the same rows the browser loads (data_files.home_offers, EU); static/js/home.js filters, sorts
and, for other settings or a storage size, re-renders the rows from the region's home files with blocks.js. The page
also embeds a small summary per phone (what the chips, sorts and storage list need) so they work without fetching."""
from collections import Counter
from datetime import UTC

from jinja2 import Environment

from ... import derive
from ..context import SiteData
from ..data_files import home_offers
from ..view import DEFAULT, best_of, gap
from ..view import rows as view_rows
from .stores import page_names

MIN_PHONES_PER_ROM = 3   # a storage size is offered in the list when this many phones are sold with it
FIRST = 20               # rows shown before "Show all"


def _rom(storage: str) -> int | None:
    ram, _, rom = (storage or "").partition("/")
    return int(rom) if ram.isdigit() and rom.isdigit() else None


def summary(rows: list[dict]) -> dict:
    """What home.js summarize() works out from a phone's rows (the same keys, only those that apply): which versions
    have a current price, the lowest current total, the settled China saving and the storage sizes sold."""
    ok = [r for r in rows if r["state"] == "ok"]
    out: dict = {}
    for e in ("china", "global"):
        if best_of(rows, e):
            out[e] = 1
    if ok:
        out["cheap"] = round(min(r["total"] for r in ok), 2)
    g = gap(rows)
    if g:
        out["gap"] = round(g["diff"], 2)
    roms = sorted({r for r in (_rom(x["storage"]) for x in rows) if r})
    if roms:
        out["roms"] = roms
    return out


def _drops(data: SiteData) -> list[dict]:
    """Listings that got cheaper this week by at least 3% and EUR 20 (the Drops page's rule)."""
    if not data.updated_at:
        return []
    return [d for d in derive.listing_drops(data.rows, data.rates, data.updated_at.replace(tzinfo=UTC)) if d["real"]]


def _label(n: int) -> str:
    return f"{n // 1024} TB" if n >= 1024 else f"{n} GB"


def page(data: SiteData, ctx: dict, phones: list[dict]) -> dict:
    """The home page's own context, `v`."""
    drops = _drops(data)
    big: dict[str, float] = {}
    for d in drops:
        big[d["slug"]] = max(big.get(d["slug"], 0), d["eur"])
    ordered = sorted(phones, key=lambda p: p["announced"] or "", reverse=True)   # newest first, ties keep the catalog order
    meta, rows = [], {}
    for p in ordered:
        rows[p["id"]] = view_rows([{k: v for k, v in o.items() if k != "id"} for o in home_offers(p, DEFAULT.region)], data.tax_cfg, DEFAULT)
        m = {"id": p["id"], "name": p["name"], "brand": p["brand"], "announced": p["announced"] or "", "s": summary(rows[p["id"]])}
        if p["ed_label"]["china"] != "China":
            m["l"] = p["ed_label"]["china"]
        if p["id"] in big:
            m["drop"] = round(big[p["id"]])
        meta.append(m)
    count = Counter(r for m in meta for r in m["s"].get("roms", []))
    files = ctx.get("home_files") or {}
    pages = set(page_names(data.stores_cfg))
    return {"s": DEFAULT, "ordered": ordered, "rows": rows, "meta": meta, "n_drops": len(drops), "drops": set(big), "first": FIRST,
            "roms": [(r, _label(r)) for r in sorted(count) if count[r] >= MIN_PHONES_PER_ROM],
            "brands": sorted({p["brand"] for p in phones}),
            "files": {r: [x.lstrip("/") for x in paths] for r, paths in files.items()},
            "tax_file": (ctx.get("tax_file") or "").lstrip("/"),
            "store_pages": {s["name"] for s in ctx["stores"] if (s["part_of"] or s["name"]) in pages}}


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    v = page(data, ctx, phones)
    return {"index.html": env.get_template("index.html").render(v=v, root="", path="", **ctx),
            # a real 404 (Cloudflare Pages serves /404.html with status 404), so a mistyped address isn't indexed as a page
            "404.html": env.get_template("404.html").render(root="/", path="404", **ctx)}


