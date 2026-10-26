"""Price storage, kept small enough to commit every hour:
  data/latest.json  - current offers per store (a store that fails a run keeps its last offers, marked stale)
  data/history/YYYY-MM.csv - one row only when a price or availability CHANGES (plus the first sighting), one file per
                    month of the row's own (UTC) time
  data/history/last.json - the last recorded [price, available] per "store|model_id|edition|storage", so a run
                    compares against that instead of reading all history"""
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from .models import Offer

LATEST = Path("data/latest.json")
HISTORY_DIR = Path("data/history")
LAST = HISTORY_DIR / "last.json"
FIELDS = ["time", "store", "model_id", "edition", "storage", "price", "currency", "available"]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_latest() -> dict:
    return json.loads(LATEST.read_text()) if LATEST.exists() else {"stores": {}}


def save(results: dict[str, list[Offer]], failures: dict[str, str]) -> dict:
    now = _now()
    prev = load_latest()
    # compare with the last recorded row per offer, not with latest.json: an offer that drops out of a store's listing
    # for a run and comes back at the same price is no change
    prev_prices = load_last()
    new_rows = []
    stores = {s: st for s, st in prev["stores"].items() if s not in results and s not in failures}  # not checked this run
    for store, offers in results.items():
        stores[store] = {"checked": now, "ok": True, "offers": [o.to_dict() for o in offers]}
        for o in offers:
            if prev_prices.get("|".join(o.key)) != [o.price, int(o.available)]:
                new_rows.append([now, *o.key, o.price, o.currency, int(o.available)])
    for store, err in failures.items():
        old = prev["stores"].get(store)
        stores[store] = {**(old or {"offers": []}), "ok": False, "error": err, "last_attempt": now}
    latest = {"updated": now, "stores": stores}
    # history first, then latest.json (via a temp file): if the run dies in between, the next run sees the same
    # changes again instead of losing them
    append(new_rows)
    tmp = LATEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(latest, indent=1))
    tmp.replace(LATEST)
    print(f"  history: {len(new_rows)} price changes recorded")
    return latest


def month_file(ts: str) -> Path:
    """The file a row stamped `ts` (UTC, YYYY-MM-DDTHH:MM:SSZ) belongs in."""
    return HISTORY_DIR / f"{ts[:7]}.csv"


def _month_files() -> list[Path]:
    return sorted(HISTORY_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].csv"))


def _read(path: Path) -> list[dict]:
    with path.open() as f:
        return [{**r, "price": float(r["price"]), "available": r["available"] == "1"} for r in csv.DictReader(f)]


def write_last(last: dict) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LAST.with_suffix(".tmp")
    tmp.write_text(json.dumps(last, indent=0, sort_keys=True))
    tmp.replace(LAST)


def load_last() -> dict:
    """{"store|model_id|edition|storage": [price, available 0/1]}; rebuilt from the month files if last.json is missing."""
    if LAST.exists():
        return json.loads(LAST.read_text())
    last = {}
    for p in _month_files():
        for r in _read(p):
            last["|".join((r["store"], r["model_id"], r["edition"], r["storage"]))] = [r["price"], int(r["available"])]
    return last


def append(rows: list[list]) -> None:
    """Add rows (oldest first) to their month files, then update last.json (CSVs first: a crash in between only repeats rows' keys)."""
    if not rows:
        return
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    by_file: dict[Path, list[list]] = {}
    for r in rows:
        by_file.setdefault(month_file(r[0]), []).append(r)
    for path, rs in by_file.items():
        new_file = not path.exists()
        with path.open("a", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(FIELDS)
            w.writerows(rs)
    last = load_last()
    for r in rows:
        last["|".join(map(str, r[1:5]))] = [float(r[5]), int(r[7])]
    write_last(last)


def load_history(months: int | None = None) -> list[dict]:
    """Rows oldest first; months=N reads only the newest N month files."""
    files = _month_files()
    if months is not None:
        files = files[len(files) - months:] if months > 0 else []
    return [r for p in files for r in _read(p)]
