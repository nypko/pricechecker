"""/about, /methodology and /privacy (affiliate networks look for /about and /privacy)."""
from jinja2 import Environment

from ... import derive, telegram
from ..context import SiteData


def render(env: Environment, data: SiteData, ctx: dict, phones: list[dict]) -> dict[str, str]:
    # the numbers the Drops page and the Telegram channel count by, so the methodology page quotes the code's own rule
    rules = {"drop_pct": derive.MIN_PCT, "drop_eur": derive.MIN_EUR,
             "tg_pct": round(telegram.MIN_PCT * 100, 1) if telegram.MIN_PCT * 100 % 1 else int(telegram.MIN_PCT * 100), "tg_eur": telegram.MIN_EUR}
    return {f"{page}.html": env.get_template(f"{page}.html").render(phones=phones, root="", path=page, **rules, **ctx)
            for page in ("about", "methodology", "privacy")}
