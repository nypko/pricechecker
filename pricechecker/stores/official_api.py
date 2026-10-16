"""Amazon and AliExpress only allow automated price access through their official affiliate APIs
(scraping them breaks their terms). These are placeholders until you have API credentials:
  - Amazon Associates: Product Advertising API keys (Amazon grants them after qualifying sales).
  - AliExpress Portals: an app key/secret from the AliExpress affiliate open platform.
"""
import os

from ..models import Offer, StoreNotConfigured


def fetch(store: str, cfg: dict) -> list[Offer]:
    missing = [env for env in cfg.get("credential_envs", []) if not os.environ.get(env)]
    if missing:
        raise StoreNotConfigured(f"'{store}' needs API credentials in env: {', '.join(missing)}")
    raise StoreNotConfigured(f"'{store}' API client not implemented yet - add it once credentials are available")
