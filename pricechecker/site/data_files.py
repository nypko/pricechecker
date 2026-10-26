"""The versioned data files the browser loads (build/data/v1/): one per phone, one for the home page, one for the import
tax config. Each is named <name>.<first 10 hex of its sha256>.json, so a changed file gets a new URL and can be cached
for a year; every file stays under BUDGET bytes (before gzip). Store notes, coupons and other prose stay in the HTML."""
import hashlib
import json
from pathlib import Path

from .. import derive, pricing, specs
from . import offers as offers_mod
from .common import EDITIONS
from .context import SiteData

VERSION = "v1"
BUDGET = 60_000

# what pricing.cost()/rank() read, plus what the page shows for a row
_COST_KEYS = ("money", "pay", "pay_ok", "ship", "duties", "old", "available")
_SHOW_KEYS = ("store_label", "edition", "storage", "link", "days", "trust")
_PAGE_ONLY = ("link", "days", "trust")   # shown on the phone page, not in the home list (keeps home.json inside BUDGET)


def _promo(p: dict | None) -> dict | None:
    return {k: p[k] for k in ("pct", "stacks_with_bank", "label") if k in p} if p else None


def _lean(v):
    """Without the nulls (pricing.js reads an absent key as null) and the `_approx` flags that are 0 (it tests == 1)."""
    if isinstance(v, dict):
        return {k: _lean(x) for k, x in v.items() if x is not None and not (k.endswith("_approx") and x == 0)}
    return v


def offer_inputs(o: dict) -> dict:
    """One offer as the browser needs it: exactly what pricing.js cost() reads, and the fields a row displays.
    Null values are left out (the browser reads a missing key as null) to keep the files small."""
    return _lean({**{k: o.get(k) for k in _COST_KEYS + _SHOW_KEYS}, "promo": _promo(o.get("promo"))})


def _dump(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()


def _put(out: Path, name: str, doc) -> str:
    """Write data/v1/<name>.<hash>.json under out; return the published path."""
    body = _dump(doc)
    rel = f"data/{VERSION}/{name}.{hashlib.sha256(body).hexdigest()[:10]}.json"
    path = out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return "/" + rel


def _phone_doc(data: SiteData, p: dict) -> dict:
    sheet = data.spec_sheets.get(p["id"]) or {}
    labels = {s: c.get("label", s) for s, c in data.stores_cfg.items()}
    lines = {}
    for e in p["editions"]:
        per_store = derive.store_lines(data.rows, p["id"], e, data.rates)
        lines[e] = {labels.get(s, s): [list(pt) for pt in pts] for s, pts in per_store.items()}
    return {"v": 1, "offers": [offer_inputs(o) for o in p["offers"]], "lines": lines,
            "bands": {e: specs.band_check(sheet, e) if sheet else None for e in p["editions"]}}


def _home_offer(o: dict) -> dict:
    """The home list answers one question (EU, card, any display currency), so only the EU's shipping and duties
    are kept and the page-only fields are left out; with every region the file passes BUDGET."""
    i = offer_inputs(o)
    out = {k: v for k, v in i.items() if k not in _PAGE_ONLY}
    for k in ("ship", "duties"):
        if k in out:
            out[k] = {r: v for r, v in out[k].items() if r == "EU"}
    return out


def _home_doc(data: SiteData, phones: list[dict]) -> dict:
    """Per phone and version, the offer the page title would lead with for the EU, card, EUR (pricing.rank)."""
    s = pricing.Settings("EU", "", "card", "eur")
    rule = pricing.tax_rule(data.tax_cfg, s)
    out = []
    for p in phones:
        eds = {}
        for e in sorted(p["editions"], key=EDITIONS.index):
            ranked = pricing.rank([o for o in p["offers"] if o["edition"] == e], s, rule, with_base=True)
            best = next((o for o, k in ranked if k.pay_ok and not k.old), None)
            if best:
                eds[e] = _home_offer(best)
        out.append({"id": p["id"], "editions": eds})
    return {"v": 1, "phones": out}


def write(data: SiteData, out: Path, phones: list[dict] | None = None) -> dict[str, str]:
    """Write the data files under out/data/v1/. Returns {logical name: published path}: "tax", "home" and
    "phone/<id>" for the templates."""
    phones = offers_mod.assemble(data) if phones is None else phones
    names = {"tax": _put(out, "tax", data.tax_cfg)}
    names["home"] = _put(out, "home", _home_doc(data, phones))
    for p in phones:
        names[f"phone/{p['id']}"] = _put(out, f"phone/{p['id']}", _phone_doc(data, p))
    return names
