"""The home page (every phone, ranked in the browser) and the 404 page."""
from collections import defaultdict

from jinja2 import Environment

from ..context import SiteData


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    # storage sizes for the home page filter: those at least 3 phones are sold with (in stock somewhere)
    rom_phones = defaultdict(set)
    for p in phones:
        for o in p["offers"]:
            if o["available"] and "/" in o["storage"]:
                rom_phones[int(o["storage"].split("/")[1])].add(p["id"])
    roms = [(r, f"{r // 1024} TB" if r >= 1024 else f"{r} GB") for r in sorted(rom_phones) if len(rom_phones[r]) >= 3]
    return {"index.html": env.get_template("index.html").render(phones=phones, root="", path="", roms=roms, **ctx),
            # a real 404 (Cloudflare Pages serves /404.html with status 404), so a mistyped address isn't indexed as a page
            "404.html": env.get_template("404.html").render(root="/", path="404", **ctx)}
