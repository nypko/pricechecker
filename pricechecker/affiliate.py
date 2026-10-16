"""Builds tracking links from each store's link template in config/stores.yaml.
Template placeholders: {url} plain product URL, {url_enc} URL-encoded, {sep} '?' or '&', {id} your affiliate id."""
import os
from urllib.parse import quote


def link(url: str, cfg: dict) -> str:
    tpl = cfg.get("affiliate_link")
    aff_id = os.environ.get(cfg.get("affiliate_id_env", ""), "") or cfg.get("affiliate_id", "")
    if not tpl or not aff_id or "YOUR_" in str(aff_id):
        return url  # not configured yet: plain link, so the site still works
    url, hash_, fragment = url.partition("#")   # tracking parameters must come before any #anchor
    out = tpl.format(url=url, url_enc=quote(url, safe=""), sep="&" if "?" in url else "?", id=aff_id)
    return out + hash_ + fragment
