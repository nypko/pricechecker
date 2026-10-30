"""/compare (spec §5.5): the page carries only the phone list (id, name, brand, versions, data file) and each phone's key
specs; static/js/compare.js fetches the chosen phones' v1 data files and prices them with the visitor's settings. The
choice lives in the URL hash (#a,b,c@16-512) so a comparison can be shared. Without JavaScript: the prompt and links."""
import json
import re

from jinja2 import Environment

from ..context import SiteData
from .specs import _cell

# _cell: the specs page's rule for a value (none, plain, or split between the versions)
# (id, label, group, field): the key specs compared; "battery" and "wired" are the rows the green checks go on
ROWS = (("chip", "Chip", "performance", "chip"), ("size", "Screen", "display", "size"),
        ("refresh", "Refresh rate", "display", "refresh_rate"), ("battery", "Battery", "battery", "battery"),
        ("wired", "Wired charging", "battery", "wired"), ("wireless", "Wireless charging", "battery", "wireless"),
        ("main", "Main camera", "cameras", "main"), ("weight", "Weight", "build", "weight"))


def _number(text) -> int | float:
    """'7,050 mAh' -> 7050, '66.5 W' -> 66.5; 0 when there is no number."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(text or ""))
    if not m:
        return 0
    n = float(m[0].replace(",", ""))
    return int(n) if n == int(n) else n


def _compact(v) -> str | list | None:
    """A cell as the page script reads it: null (not on the brand's page), text, or [China, Global] when they differ."""
    c = _cell(v)
    return None if c["kind"] == "none" else c["text"] if c["kind"] == "plain" else [c["china"], c["global"]]


def _phone(p: dict, sheet: dict, files: dict) -> dict:
    groups = sheet.get("groups")
    key = sheet.get("key") or {}
    return {"id": p["id"], "name": p["name"], "brand": p["brand"], "announced": p["announced"], "editions": p["editions"],
            "cl": p["ed_label"]["china"], "file": (files.get(f"phone/{p['id']}") or "").lstrip("/"),
            "k": {"battery": _number(key.get("battery")), "charging": _number(key.get("charging"))},
            "c": [_compact((groups.get(g) or {}).get(f)) for _, _, g, f in ROWS] if groups else None}


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    files = ctx.get("data_files") or {}
    lst = [_phone(p, data.spec_sheets.get(p["id"]) or {}, files) for p in sorted(phones, key=lambda q: q["name"])]
    doc = {"rows": [{"id": i, "label": label} for i, label, _, _ in ROWS], "phones": lst}
    return {"compare.html": env.get_template("compare.html").render(
        root="", path="compare", phones=lst, tax_rel=(ctx.get("tax_file") or "").lstrip("/"),
        cmp_json=json.dumps(doc, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"), **ctx)}
