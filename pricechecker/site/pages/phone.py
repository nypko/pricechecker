"""One page per phone: phones/<slug>.html."""
from jinja2 import Environment

from ..context import SiteData


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    return {f'phones/{p["slug"]}.html': env.get_template("phone.html").render(p=p, root="../", path=f'phones/{p["slug"]}', **ctx)
            for p in phones}
