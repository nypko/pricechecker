"""Hourly job: check every enabled store, record price changes, rebuild the site.
Usage: python -m pricechecker.run [--only wonda,giztop] [--no-build]
Exit codes: 0 ok, 3 no store could be checked this time (the site is still rebuilt from the last known prices)."""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import yaml

from . import fx, history, site, terms, promos
from .models import StoreNotConfigured
from .stores import ADAPTERS


def load_config():
    stores = yaml.safe_load(Path("config/stores.yaml").read_text())["stores"]
    catalog = yaml.safe_load(Path("config/catalog.yaml").read_text())["phones"]
    for p in catalog:
        p.setdefault("edition", "china")
        p.setdefault("brand", p["name"].split()[0])
    return stores, catalog


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated store names to check")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--build-only", action="store_true", help="rebuild the site from saved data, no price checks")
    args = ap.parse_args(argv)
    os.chdir(Path(__file__).resolve().parent.parent)
    stores, catalog = load_config()
    if args.build_only:
        site.build(catalog, stores, fx.rates(), terms.check_pages(stores))
        return 0
    tracked = {p["id"] for p in catalog}   # by model: any edition a store sells is shown (Global and China side by side)
    only = set(args.only.split(",")) if args.only else None
    results, failures, untracked_lines = {}, {}, []
    had = {s: len(st.get("offers", [])) for s, st in history.load_latest()["stores"].items()}   # offers each store had last time
    for name, cfg in stores.items():
        if not cfg.get("enabled", True) or cfg.get("part_of") or (only and name not in only):
            continue   # part_of: filled in by its parent store's check (e.g. an EU-warehouse section)
        print(f"[{name}] checking ({cfg['type']})")
        try:
            offers = ADAPTERS[cfg["type"]](name, cfg, catalog)
        except StoreNotConfigured as e:
            print(f"  skipped: {e}")
            continue
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            failures[name] = f"{type(e).__name__}: {e}"[:300]
            for sub, sub_cfg in stores.items():
                if sub_cfg.get("part_of") == name:
                    failures[sub] = failures[name]
            continue
        if not offers and had.get(name):
            # an answer with nothing in it (a changed page layout, a half-written sitemap) is a failure, not a sold-out store:
            # keep the last prices, marked stale, rather than wiping the store off the site
            print("  FAILED: no offers returned (had %d last run)" % had[name])
            failures[name] = "no offers returned"
            for sub, sub_cfg in stores.items():
                if sub_cfg.get("part_of") == name:
                    failures[sub] = failures[name]
            continue
        kept = [o for o in offers if o.model_id in tracked]
        untracked = Counter(o.model_id + "/" + o.edition for o in offers if o.model_id not in tracked)
        print(f"  {len(offers)} offers, {len(kept)} for tracked phones" + (f"; untracked models: {len(untracked)}" if untracked else ""))
        untracked_lines += [f"{name}\t{k}\n" for k in sorted(untracked)]
        results[name] = [o for o in kept if o.store == name]
        for sub, sub_cfg in stores.items():
            if sub_cfg.get("part_of") == name:
                results[sub] = [o for o in kept if o.store == sub]
    Path("data/untracked.txt").write_text("".join(untracked_lines))  # models seen but not in catalog.yaml
    history.save(results, failures)
    try:
        promos.scan(stores)   # once a day: new promotion text -> report; configured promotions expire with their banner
    except Exception as e:
        print(f"  [promos] scan failed: {type(e).__name__}: {e}")
    if not args.no_build:
        site.build(catalog, stores, fx.rates(), terms.check_pages(stores))
    return 0 if results else 3


if __name__ == "__main__":
    sys.exit(main())
