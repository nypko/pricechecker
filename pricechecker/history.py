"""Price storage, kept small enough to commit every hour:
  data/latest.json  - current offers per store (a store that fails a run keeps its last offers, marked stale)
  data/history.csv  - one row only when a price or availability CHANGES (plus the first sighting)"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Offer

LATEST = Path("data/latest.json")
HISTORY = Path("data/history.csv")
FIELDS = ["time", "store", "model_id", "edition", "storage", "price", "currency", "available"]


def load_latest() -> dict:
    return json.loads(LATEST.read_text()) if LATEST.exists() else {"stores": {}}


def save(results: dict[str, list[Offer]], failures: dict[str, str]) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = load_latest()
    prev_prices = {(s, o["model_id"], o["edition"], o["storage"]): (o["price"], o["available"])
                   for s, st in prev["stores"].items() for o in st["offers"]}
    new_rows = []
    stores = {s: st for s, st in prev["stores"].items() if s not in results and s not in failures}  # not checked this run
    for store, offers in results.items():
        stores[store] = {"checked": now, "ok": True, "offers": [o.to_dict() for o in offers]}
        for o in offers:
            if prev_prices.get(o.key) != (o.price, o.available):
                new_rows.append([now, *o.key, o.price, o.currency, int(o.available)])
    for store, err in failures.items():
        old = prev["stores"].get(store)
        stores[store] = {**(old or {"offers": []}), "ok": False, "error": err, "last_attempt": now}
    latest = {"updated": now, "stores": stores}
    LATEST.write_text(json.dumps(latest, indent=1))
    new_file = not HISTORY.exists()
    with HISTORY.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(FIELDS)
        w.writerows(new_rows)
    print(f"  history: {len(new_rows)} price changes recorded")
    return latest


def load_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    with HISTORY.open() as f:
        return [{**r, "price": float(r["price"]), "available": r["available"] == "1"} for r in csv.DictReader(f)]
