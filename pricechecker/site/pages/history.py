"""One price-history page per phone: history/<slug>.html."""
from jinja2 import Environment

from ..context import SiteData


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    return {f'history/{p["slug"]}.html': env.get_template("history.html").render(p=p, root="../", path=f'history/{p["slug"]}', **ctx)
            for p in phones}
