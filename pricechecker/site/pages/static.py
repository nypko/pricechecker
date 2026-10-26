"""/about, /methodology and /privacy (affiliate networks look for /about and /privacy)."""
from jinja2 import Environment

from ..context import SiteData


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    return {f"{page}.html": env.get_template(f"{page}.html").render(phones=phones, root="", path=page, **ctx)
            for page in ("about", "methodology", "privacy")}
