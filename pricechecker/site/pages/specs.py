"""One specs page per phone whose sheet lists fields: phones/<slug>/specs.html (spec §5.3), served as /phones/<slug>/specs.
Rows come from config/specs/<id>.yaml (pricechecker/specs.py): a field the two brand pages give differently splits into
a China half and a Global half; a field only one page lists (same hardware) is one plain cell; the page exists exactly
where specs.has_page(sheet) is true, the rule pages/phone.py uses for its "All N specs" link."""
from datetime import date, datetime

from jinja2 import Environment

from ... import specs
from ..common import ed_labels
from ..context import SiteData

EDS = ("china", "global")
GROUP_TITLE = {"battery": "Battery and charging"}   # every other group is its key, capitalised


def _group_id(title: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in title.lower())


def _day(d) -> str:
    if not isinstance(d, date):
        d = datetime.strptime(str(d), "%Y-%m-%d")
    return f"{d.day} {d:%b %Y}"


def _cell(v) -> dict:
    """What the template draws for one value: kind none (brand's page doesn't give it), plain, or split."""
    if v is None:
        return {"kind": "none"}
    if isinstance(v, str):
        return {"kind": "plain", "text": v}
    if set(v) == {"value", "from"}:
        return {"kind": "plain", "text": v["value"]}
    if v["china"] == v["global"] and v["china"] is not None:
        return {"kind": "plain", "text": v["china"]}
    both = v["china"] is not None and v["global"] is not None
    return {"kind": "split", "china": v["china"], "global": v["global"], "diff": both}


def _bands(sheet: dict, e: str) -> dict | None:
    have = (sheet.get("bands") or {}).get(e)
    chk = specs.band_check(sheet, e)
    if not have or chk is None:
        return None
    why = chk["why"]
    return {"lte": sorted(have.get("lte", [])), "nr": sorted(have.get("nr", [])),
            "miss_lte": chk["lte"], "miss_nr": chk["nr"],
            "missing": [f"LTE {b}" for b in chk["lte"]] + [f"5G n{b}" for b in chk["nr"]],
            "why": [(b, why[b]) for b in dict.fromkeys(chk["lte"] + chk["nr"]) if b in why]}


def page(p: dict, sheet: dict) -> dict:
    labels = ed_labels(p["brand"])
    groups = []
    for g, fields in sheet["groups"].items():
        rows = [{"label": specs.FIELDS[g][f], **_cell(v)} for f, v in (fields or {}).items()]
        if rows:
            title = GROUP_TITLE.get(g, g.capitalize())
            groups.append({"title": title, "id": _group_id(title), "rows": rows})
    srcs = sheet.get("sources") or {}
    eds = [e for e in EDS if e in srcs or e in (sheet.get("bands") or {}) or e in p["editions"]]
    return {
        "labels": labels, "groups": groups, "diffs": specs.differences(sheet),
        "sources": [{"e": e, "url": srcs[e]["url"], "day": _day(srcs[e]["checked"]), "lang": srcs[e].get("lang")}
                    for e in EDS if e in srcs],
        "unread": [e for e in EDS if e not in srcs and e in p["editions"]],
        "one_sided": len(srcs) > 1 and any(isinstance(f, dict) and set(f) == {"value", "from"}
                                            for fields in sheet["groups"].values() for f in (fields or {}).values()),
        "bands": [(e, _bands(sheet, e)) for e in eds],
        "eu": specs._regions()["EU"],
    }


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    tpl = env.get_template("specs.html")
    out = {}
    for p in phones:
        sheet = data.spec_sheets.get(p["id"]) or {}
        if specs.has_page(sheet):
            out[f'phones/{p["slug"]}/specs.html'] = tpl.render(
                p=p, v=page(p, sheet), root="../../", path=f'phones/{p["slug"]}/specs', **ctx)
    return out
