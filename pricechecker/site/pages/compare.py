"""/compare: every phone's specs and in-stock offers in one JSON block; the browser shows up to three side by side
(picked in the page, kept in the URL hash so a comparison can be shared) and prices them for the chosen Ship-to."""
import json

from jinja2 import Environment

from ..common import _spec_parts
from ..context import SiteData


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    cmp = [{"s": p["slug"], "n": p["name"], "b": p["brand"], "d": p["announced"], "e": p["editions"], "cl": p["ed_label"]["china"],
            "sp": [[k, _spec_parts(v)] for k, v in p["specs"]], "g": p["google"]["short"] if "china" in p["editions"] else "",
            "st": [st for st, _ in p["by_storage"]], "o": json.loads(p["offers_json"])}
           for p in sorted(phones, key=lambda q: q["name"])]
    return {"compare.html": env.get_template("compare.html").render(
        root="", path="compare", cmp_phones=cmp, cmp_json=json.dumps(cmp, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"), **ctx)}
