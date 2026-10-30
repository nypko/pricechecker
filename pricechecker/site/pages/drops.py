"""The Drops page (spec §5.4) and the one list of this week's real drops that the home page's count, this page and
feeds/drops.xml all use. A drop is a store listing (store, phone, version, memory) that got cheaper by MIN_PCT and
MIN_EUR over seven days (derive.week_drops). Each row shows the listing's CURRENT delivered total as the `store_row`
block for the default settings (from the phone's offer inputs); static/js/drops.js re-prices it with blocks.js from the
phones' own data files when the visitor's settings differ."""
import json
from datetime import UTC
from pathlib import Path

from jinja2 import Environment

from ... import derive
from ..common import ed_labels
from ..context import SiteData
from ..data_files import offer_inputs
from ..view import DEFAULT
from ..view import rows as view_rows

N_OLDER = 5   # earlier drops shown in a week with none
TELEGRAM_STATE = Path("data/telegram.json")


def _telegram_state() -> dict:
    try:
        return json.loads(TELEGRAM_STATE.read_text())
    except (OSError, ValueError):
        return {}


def _items(drops: list[dict], data: SiteData, phones: list[dict]) -> list[dict]:
    """Drops of listings we can show: the phone has a page and the store still lists that version and memory. Each
    gets the phone, its default-settings view row (the current total) and the labels the page prints."""
    by_id = {p["id"]: p for p in phones}
    cache: dict[str, list[dict]] = {}
    out = []
    for d in drops:
        p = by_id.get(d["slug"])
        store = data.stores_cfg.get(d["store"])
        if not p or store is None or d["store"] not in data.live_stores:
            continue
        rows = cache.setdefault(p["id"], view_rows([offer_inputs(o) for o in p["offers"]], data.tax_cfg, DEFAULT))
        label = store.get("label", d["store"])
        row = next((r for r in rows if r["store"] == label and r["edition"] == d["edition"] and r["storage"] == d["storage"]), None)
        if row is None:
            continue
        out.append({**d, "name": p["name"], "brand": p["brand"], "labels": ed_labels(p["brand"]), "store_label": label, "row": row})
    return out


def this_week(data: SiteData, phones: list[dict]) -> list[dict]:
    """This week's real drops that can be shown, biggest saving first (home.py counts them, the page and feed list them)."""
    if not data.updated_at:
        return []
    now = data.updated_at.replace(tzinfo=UTC)
    items = _items(derive.week_drops(data.rows, data.rates, now, _telegram_state()), data, phones)
    return sorted(items, key=lambda d: (-d["eur"], d["slug"], d["store"]))


def earlier(data: SiteData, phones: list[dict]) -> list[dict]:
    """The latest N_OLDER real drops of the last OLDER_DAYS days that are not this week's (shown when this week has none)."""
    if not data.updated_at:
        return []
    now = data.updated_at.replace(tzinfo=UTC)
    return _items(derive.older_drops(data.rows, data.rates, now), data, phones)[:N_OLDER]


def page(data: SiteData, ctx: dict, phones: list[dict]) -> dict:
    """The page's own context, `v`."""
    week = this_week(data, phones)
    old = [] if week else earlier(data, phones)
    shown = week or old
    files = ctx.get("data_files") or {}
    rel = lambda path: path.lstrip("/") if path else ""
    slugs = sorted({d["slug"] for d in shown})
    return {"s": DEFAULT, "week": week, "older": old, "min_pct": derive.MIN_PCT, "min_eur": derive.MIN_EUR,
            "older_days": derive.OLDER_DAYS, "brands": sorted({d["brand"] for d in week}),
            "files": {slug: rel(files.get(f"phone/{slug}")) for slug in slugs},
            "tax_file": rel(ctx.get("tax_file")), "now": ctx.get("updated") or None}


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    return {"drops.html": env.get_template("drops.html").render(v=page(data, ctx, phones), root="", path="drops", **ctx)}
