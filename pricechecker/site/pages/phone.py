"""One page per phone: phones/<slug>.html (spec §5.2). Every price on it is a shared block (templates/_d/blocks.html)
rendered for the default settings from the same offer inputs the browser loads (data_files.offer_inputs over the
phone's v1 file), so static/js/phone.js re-renders the same blocks from the same data for other settings."""
from datetime import datetime

from jinja2 import Environment

from ... import derive, specs
from ..blocks import PLACE, ledger_rows
from ..context import SiteData
from ..data_files import offer_inputs
from ..view import DEFAULT, best_of, default_pick
from ..view import rows as view_rows

EDS = ("china", "global")   # box order: the China version (red) left, Global (blue) right
W, H, PAD = 600, 130, 8     # history SVG viewBox

# "Other stores" delivery filters: key, chip label, test on a view row (static/js/phone.js FILTERS: the same three)
FILTERS = (("tax", "Import tax paid by store", lambda r: r["duties"] is True),
           ("ship", "Free shipping", lambda r: r["ship"] == 0),
           ("fast", "Arrives within 10 days", lambda r: bool(r["days"]) and r["days"][1] <= 10))


def _missing(p: dict, e: str, labels: dict) -> str:
    """Why a version has no price box: the brand doesn't make it, or no store we check lists it."""
    if e in p["editions"]:
        return f"No store we check lists the {labels[e]} version"
    if e == "china":
        return f"{p['brand']} doesn't make a {labels['china']} version"
    return f"No {labels['global']} version so far: {p['brand']} sells this phone in {'China' if labels['china'] == 'China' else 'Asia'} only"


def _day(d: str) -> str:
    return datetime.strptime(d, "%Y-%m-%d").strftime("%-d %b")


def store_lines_svg(lines: dict[str, list]) -> dict | None:
    """{store label: [(day, EUR)]} -> what templates/_d/history_svg.html draws: one polyline per store (cheapest last
    price first, colours --s1..--s6), a dot at each line's last price, and the first day. None without any point."""
    names = sorted((k for k, v in lines.items() if v), key=lambda k: lines[k][-1][1])
    if not names:
        return None
    days = sorted({d for k in names for d, _ in lines[k]})
    at = {d: i for i, d in enumerate(days)}
    ps = [v for k in names for _, v in lines[k]]
    lo, hi = min(ps), max(ps)
    if hi - lo < 1:
        lo, hi = lo - 50, hi + 50
    x = lambda d: PAD + at[d] / max(1, len(days) - 1) * (W - 2 * PAD)
    y = lambda v: H - PAD - (v - lo) / (hi - lo) * (H - 2 * PAD)
    out = []
    for i, k in enumerate(names):
        pts = lines[k]
        out.append({"name": k, "n": i % 6 + 1, "points": " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in pts),
                    "cx": f"{x(pts[-1][0]):.1f}", "cy": f"{y(pts[-1][1]):.1f}", "last": pts[-1][1]})
    return {"w": W, "h": H, "stores": out, "since": _day(days[0]), "days": len(days)}


def buyers_text(b: dict | None, region: str) -> str:
    """Approved buyer reports for a store and region: "12 buyers to the EU: 8–21 days (typically 11) · 3 of 10 paid
    import tax" (static/js/phone.js buyersText: the same)."""
    b = (b or {}).get(region)
    if not b or not b.get("n"):
        return ""
    x = []
    if b.get("nd"):
        x.append((str(b["dmin"]) if b["dmin"] == b["dmax"] else f"{b['dmin']}–{b['dmax']}") + " days"
                 + (f" (typically {b['dmed']})" if b["nd"] > 2 else ""))
    if b.get("tk"):
        x.append(f"{b['tx']} of {b['tk']} paid import tax")
    return f"{b['n']} {'buyer' if b['n'] == 1 else 'buyers'} to {PLACE[region]}: " + " · ".join(x) if x else ""


def _rows(p: dict, tax_cfg: dict) -> list[dict]:
    return view_rows([offer_inputs(o) for o in p["offers"]], tax_cfg, DEFAULT)


def _bands(sheet: dict, e: str) -> dict:
    c = specs.band_check(sheet, e) if sheet else None
    if c is None:
        return {"e": e, "checked": False}
    missing = [f"LTE {b}" for b in c["lte"]] + [f"5G n{b}" for b in c["nr"]]
    why = [f"band {b} is {t}" for b, t in c["why"].items()]
    return {"e": e, "checked": True, "missing": missing, "why": "; ".join(why)}


def page(p: dict, data: SiteData, ctx: dict, by_id: dict[str, dict]) -> dict:
    """The phone page's own context, `v`: the default-settings rows and the picks the blocks are rendered with."""
    labels = p["ed_label"]
    rows = _rows(p, data.tax_cfg)
    eds = [e for e in EDS if any(r["edition"] == e for r in rows)]
    # the page opens on the cheapest current row of both versions (its total is the <title> price); with none, the first
    # version's first listed memory
    dp = default_pick(rows)
    ed = dp["ed"] if dp else (eds[0] if eds else None)
    mem = dp["mem"] if dp else next((r["storage"] for r in rows if r["edition"] == ed), None)
    best = best_of(rows, ed, mem) if ed else None
    pick = [r for r in rows if r["edition"] == ed and r["storage"] == mem]
    rest = [r for r in pick if r is not best]
    cand = [r for r in rest if r["state"] not in ("soldout", "nodelivery")]
    sheet = data.spec_sheets.get(p["id"]) or {}
    names = {s: c.get("label", s) for s, c in data.stores_cfg.items()}
    hist = {}
    for e in p["editions"]:
        lines = derive.store_lines(data.rows, p["id"], e, data.rates)
        hist[e] = store_lines_svg({names.get(s, s): pts for s, pts in lines.items()})
    more = [by_id[c["slug"]] for c in p["related"]["brand"][:3] if c["slug"] in by_id]
    files = ctx.get("data_files") or {}
    rel = lambda path: ctx["root_rel"] + path.lstrip("/") if path else ""
    return {
        "s": DEFAULT, "rows": rows, "eds": eds,
        "missing": [_missing(p, e, labels) for e in EDS if e not in eds] if eds else [],
        "ed": ed, "mem": mem, "best": best, "pick": pick, "rest": rest,
        "filters": [(k, label, sum(1 for r in cand if f(r))) for k, label, f in FILTERS],
        "n_ledger": len(ledger_rows(rows)), "hist": hist,
        "bands": [_bands(sheet, e) for e in (eds or p["editions"])],
        "spec_count": specs.spec_count(sheet) if specs.has_page(sheet) else 0,
        "more": [(q, _rows(q, data.tax_cfg)) for q in more],
        "more_meta": [{"id": q["id"], "name": q["name"], "announced": q["announced"], "file": rel(files.get(f"phone/{q['id']}"))}
                      for q in more],
        "data_file": rel(files.get(f"phone/{p['id']}")), "tax_file": rel(ctx.get("tax_file")),
        "buyers": {o["store_label"]: o["buyers"] for o in p["offers"] if o.get("buyers")},
        "buyers_line": buyers_text(next((o.get("buyers") for o in p["offers"] if best and o["store_label"] == best["store"]), None),
                                   DEFAULT.region),
        "now": ctx.get("updated") or None,
    }


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    by_id = {q["id"]: q for q in phones}
    tpl = env.get_template("phone.html")
    out = {}
    for p in phones:
        v = page(p, data, {**ctx, "root_rel": "../"}, by_id)
        out[f'phones/{p["slug"]}.html'] = tpl.render(p={**p, "data_file": v["data_file"]}, v=v, root="../",
                                                     path=f'phones/{p["slug"]}', **ctx)
    return out
