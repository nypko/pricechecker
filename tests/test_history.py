import csv
import json
import subprocess
import sys
from pathlib import Path

from pricechecker import history
from pricechecker.models import Offer

ROOT = Path(__file__).resolve().parent.parent


def _row(ts, price=1000.0, model="phone-a", avail=1):
    return [ts, "a", model, "china", "12/256", price, "USD", avail]


def test_append_splits_by_row_month(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    history.append([_row("2026-10-31T23:59:00Z"), _row("2026-11-01T00:17:00Z", 990.0)])
    history.append([_row("2026-11-02T00:17:00Z", 980.0)])
    assert history.month_file("2026-10-31T23:59:00Z") == Path("data/history/2026-10.csv")
    for name, n in (("2026-10", 1), ("2026-11", 2)):
        lines = Path(f"data/history/{name}.csv").read_text().splitlines()
        assert lines[0] == ",".join(history.FIELDS) and len(lines) == 1 + n
    assert json.loads(history.LAST.read_text())["a|phone-a|china|12/256"] == [980.0, 1]


def _offer(price):
    return Offer(store="a", model_id="phone-a", edition="china", storage="12/256", price=price, currency="USD", available=True,
                 url="u", title="t")


def test_last_known_price_crosses_months(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("data").mkdir()
    history.append([_row("2026-10-31T23:59:00Z", 1000.0)])
    monkeypatch.setattr(history, "_now", lambda: "2026-11-01T00:17:00Z")
    history.save({"a": [_offer(1000.0)]}, {})   # same price, now in November: no row
    assert [r["price"] for r in history.load_history()] == [1000.0]
    assert not Path("data/history/2026-11.csv").exists()
    history.save({"a": [_offer(900.0)]}, {})
    assert Path("data/history/2026-11.csv").exists()
    assert [r["price"] for r in history.load_history()] == [1000.0, 900.0]


def test_load_history_months(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    history.append([_row("2026-08-01T00:00:00Z", 1.0), _row("2026-09-01T00:00:00Z", 2.0), _row("2026-10-01T00:00:00Z", 3.0)])
    assert [r["price"] for r in history.load_history(months=2)] == [2.0, 3.0]
    assert [r["price"] for r in history.load_history()] == [1.0, 2.0, 3.0]
    assert history.load_history() and history.load_history(months=0) == []


def test_split_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "history.csv"
    rows = [_row("2026-09-30T23:00:00Z", 1000.0), _row("2026-10-01T00:00:00Z", 990.0), _row("2026-10-02T00:00:00Z", 500.0, "phone-b", 0),
            _row("2026-11-01T00:00:00Z", 980.0)]
    with src.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(history.FIELDS)
        w.writerows(rows)
    cmd = [sys.executable, str(ROOT / "tools" / "split_history.py"), str(src)]
    for _ in range(2):   # safe to re-run
        subprocess.run(cmd, check=True, cwd=tmp_path)
    got = history.load_history()
    assert [(r["time"], r["model_id"], r["price"], r["available"]) for r in got] == \
        [(r[0], r[2], float(r[5]), bool(r[7])) for r in rows]
    assert sorted(p.name for p in Path("data/history").iterdir()) == ["2026-09.csv", "2026-10.csv", "2026-11.csv", "last.json"]
    assert json.loads(history.LAST.read_text()) == {"a|phone-a|china|12/256": [980.0, 1], "a|phone-b|china|12/256": [500.0, 0]}
