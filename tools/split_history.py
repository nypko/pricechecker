"""Rebuild data/history/YYYY-MM.csv and data/history/last.json from one history.csv (default data/history.csv).
Safe to re-run: existing month files are replaced, so the result depends only on the input. Run from the repo root.
Used once for the migration, and again when main (which still writes data/history.csv) is merged into newsite.
  python tools/split_history.py [path/to/history.csv]"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricechecker import history  # noqa: E402


def main(src: Path) -> int:
    with src.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0] != history.FIELDS:
        print(f"{src}: unexpected header {rows[:1]}", file=sys.stderr)
        return 1
    rows = rows[1:]
    history.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    for old in history.HISTORY_DIR.glob("*.csv"):
        old.unlink()
    last: dict = {}
    by_file: dict[Path, list[list[str]]] = {}
    for r in rows:
        by_file.setdefault(history.month_file(r[0]), []).append(r)
        last["|".join(r[1:5])] = [float(r[5]), int(r[7])]
    for path, rs in by_file.items():
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(history.FIELDS)
            w.writerows(rs)
    history.write_last(last)
    print(f"{len(rows)} rows -> {len(by_file)} month files, {len(last)} last-known prices")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/history.csv")))
