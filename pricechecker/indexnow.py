"""After a deploy, tell IndexNow search engines (Bing, Yandex, Seznam, Naver...) which pages changed, so new prices are
picked up within hours instead of whenever the crawler next comes by. `python -m pricechecker.indexnow`

A page counts as changed when this run recorded a price move of at least 0.5% or a stock change for that phone - the same
rule as the RSS feeds, so a store re-converting its prices by a cent doesn't resubmit every page every hour. Never fails
the job: a refused or unreachable endpoint is only logged."""
import json
import sys
from pathlib import Path

import requests
import yaml

from . import history
from .http import USER_AGENT

ENDPOINT = "https://api.indexnow.org/indexnow"
MIN_MOVE = 0.005


def changed_slugs(latest: Path = Path("data/latest.json")) -> list[str]:
    """Phones with a real price or stock change in the latest run (history rows stamped with latest.json's time)."""
    if not latest.exists():
        return []
    now = json.loads(latest.read_text()).get("updated")
    last: dict[tuple, dict] = {}
    slugs = set()
    for r in history.load_history(months=2):   # the run's rows are in the newest file, the price before them at most one month back
        key = (r["store"], r["model_id"], r["edition"], r["storage"])
        prev = last.get(key)
        if r["time"] == now and (prev is None or prev["available"] != r["available"] or
                                 abs(r["price"] - prev["price"]) >= MIN_MOVE * prev["price"]):
            slugs.add(r["model_id"])
        last[key] = r
    return sorted(slugs)


def urls(site_cfg: dict, slugs: list[str], known: set[str]) -> list[str]:
    base = site_cfg["base_url"].rstrip("/")
    pages = [f"{base}/{kind}/{s}" for s in slugs if s in known for kind in ("phones", "history")]
    return [f"{base}/", f"{base}/compare"] + pages if pages else []


def main() -> int:
    site_cfg = yaml.safe_load(Path("config/site.yaml").read_text())
    key = site_cfg.get("indexnow_key")
    if not (key and site_cfg.get("domain_live") and site_cfg.get("base_url")):
        print("indexnow: not configured or domain not live - skipped")
        return 0
    known = {p["id"] for p in yaml.safe_load(Path("config/catalog.yaml").read_text())["phones"]}
    url_list = urls(site_cfg, changed_slugs(), known)
    if not url_list:
        print("indexnow: no page changed enough - nothing to submit")
        return 0
    host = site_cfg["base_url"].split("//", 1)[1].strip("/")
    body = {"host": host, "key": key, "keyLocation": f'{site_cfg["base_url"].rstrip("/")}/{key}.txt', "urlList": url_list}
    try:
        r = requests.post(ENDPOINT, json=body, headers={"User-Agent": USER_AGENT}, timeout=30)
        print(f"indexnow: submitted {len(url_list)} URLs -> HTTP {r.status_code}")
    except requests.RequestException as e:
        print(f"indexnow: not submitted ({e})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
