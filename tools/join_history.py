"""Rebuild one data/history.csv (the layout main uses) from data/history/YYYY-MM.csv, rows in order. Rollback tool:
run it before reverting newsite's history change. Run from the repo root.
  python tools/join_history.py [output.csv]   (default data/history.csv)"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricechecker import history  # noqa: E402


def main(dst: Path) -> int:
    files = history._month_files()
    if not files:
        print(f"no month files in {history.HISTORY_DIR}", file=sys.stderr)
        return 1
    n = 0
    with dst.open("w", newline="") as out:
        w = csv.writer(out)
        w.writerow(history.FIELDS)
        for path in files:
            with path.open(newline="") as f:
                rows = list(csv.reader(f))
            if not rows or rows[0] != history.FIELDS:
                print(f"{path}: unexpected header {rows[:1]}", file=sys.stderr)
                return 1
            w.writerows(rows[1:])
            n += len(rows) - 1
    print(f"{n} rows from {len(files)} month files -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/history.csv")))
