import re
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
import yaml

from pricechecker import carriers

TABLE = carriers.band_table()


def _doc():
    return {"country": "DE", "networks": [{
        "id": "de-telekom", "name": "Telekom", "lte": [1, 3, 7, 20], "nr": [1, 3, 78],
        "basis": "used", "complete": False, "mvnos": ["Congstar"],
        "sources": [{"url": "https://www.telekom.de/netz", "kind": "carrier", "checked": "2026-10-01"}]}]}


def _net(doc):
    return doc["networks"][0]


def test_valid_sample_passes():
    assert carriers.validate(_doc(), TABLE) == []


def test_licensed_and_complete_with_a_regulator_source_passes():
    d = _doc()
    _net(d).update(basis="licensed", complete=True)
    _net(d)["sources"].append({"url": "https://www.bundesnetzagentur.de/x", "kind": "regulator", "checked": "2026-10-01"})
    assert carriers.validate(d, TABLE) == []


def test_licensed_needs_a_regulator_source():
    d = _doc()
    _net(d).update(basis="licensed")
    errs = carriers.validate(d, TABLE)
    assert errs and all("de-telekom" in e for e in errs) and any("regulator" in e for e in errs)


@pytest.mark.parametrize("nulled", ["lte", "nr"])
def test_complete_true_needs_both_band_lists(nulled):
    d = _doc()
    _net(d).update(complete=True, **{nulled: None})
    errs = carriers.validate(d, TABLE)
    assert errs and all("de-telekom" in e for e in errs) and any("complete" in e for e in errs)


def test_null_band_lists_and_no_mvnos_are_valid():
    d = _doc()
    _net(d).update(lte=None, nr=None)
    del _net(d)["mvnos"]
    assert carriers.validate(d, TABLE) == []


def test_thirty_one_countries():
    assert len(carriers.COUNTRIES) == len(set(carriers.COUNTRIES)) == 31
    assert {"DE", "GB", "US", "CA", "AU"} <= set(carriers.COUNTRIES)


@pytest.mark.parametrize("edit", [
    lambda n: n.update(name=""),
    lambda n: n.update(id=""),
    lambda n: n.update(lte=[1, 999]),
    lambda n: n.update(nr=[4]),            # an LTE-only number is not an NR band
    lambda n: n.update(lte="1,3"),
    lambda n: n.update(mvnos="Congstar"),
    lambda n: n.pop("basis"),
    lambda n: n.update(basis="guessed"),
    lambda n: n.pop("complete"),
    lambda n: n.update(complete="yes"),
    lambda n: n.update(complete=None),
    lambda n: n.update(mvnos=[1]),
    lambda n: n.update(sources=[]),
    lambda n: n["sources"][0].update(url="http://www.telekom.de"),
    lambda n: n["sources"][0].update(kind="blog"),
    lambda n: n["sources"][0].update(checked="Oct 2026"),
    lambda n: n["sources"][0].update(kind="other"),    # all sources "other"
])
def test_each_rule_fails_naming_the_network(edit):
    d = _doc()
    edit(_net(d))
    errs = carriers.validate(d, TABLE)
    assert errs and all("de-telekom" in e or "no id" in e for e in errs), errs


def test_one_good_source_is_enough_beside_other():
    d = _doc()
    _net(d)["sources"].append({"url": "https://example.org/x", "kind": "other", "checked": "2026-10-01"})
    assert carriers.validate(d, TABLE) == []


def test_bad_country_and_duplicate_id_in_file():
    d = _doc()
    d["country"] = "XX"
    assert any("XX" in e for e in carriers.validate(d, TABLE))
    d = _doc()
    d["networks"].append(deepcopy(_net(d)))
    assert any("de-telekom" in e and "twice" in e for e in carriers.validate(d, TABLE))


def test_validate_all_checks_file_name_and_ids_across_files():
    de, at = _doc(), _doc()
    at["country"] = "AT"
    assert carriers.validate_all({"DE": de, "AT": at}, TABLE) != []          # same id in two files
    _net(at)["id"] = "at-a1"
    assert carriers.validate_all({"DE": de, "AT": at}, TABLE) == []
    assert any("file" in e for e in carriers.validate_all({"FR": de}, TABLE))   # DE doc in FR.yaml


def test_stale_lists_networks_checked_over_a_year_ago():
    d = _doc()
    _net(d)["sources"][0]["checked"] = "2025-09-30"
    assert carriers.stale(d, date(2026, 10, 31)) == ["de-telekom"]
    _net(d)["sources"][0]["checked"] = date(2025, 11, 15)
    assert carriers.stale(d, date(2026, 10, 31)) == []
    assert carriers.stale(d, date(2026, 10, 31), months=11) == ["de-telekom"]


def test_stale_uses_the_newest_source():
    d = _doc()
    _net(d)["sources"].append({"url": "https://example.org/x", "kind": "brand", "checked": "2020-01-01"})
    assert carriers.stale(d, date(2026, 10, 31)) == []


def test_load_reads_files_by_country(tmp_path):
    (tmp_path / "DE.yaml").write_text(yaml.safe_dump(_doc()))
    assert carriers.load(tmp_path)["DE"]["networks"][0]["id"] == "de-telekom"
    assert carriers.load(tmp_path / "missing") == {}


def test_band_class():
    assert carriers.band_class("lte", 20) == "low"
    assert carriers.band_class("lte", 7) == "mid"
    assert carriers.band_class("nr", 78) == "high"
    assert carriers.band_class("nr", 258) == "mmwave"


def test_band_table_covers_the_planned_bands_with_valid_classes():
    lte = [1, 2, 3, 4, 5, 7, 8, 12, 13, 14, 17, 18, 19, 20, 25, 26, 28, 29, 30, 32, 34, 38, 39, 40, 41, 42, 43, 46,
           48, 53, 66, 71, 106]
    nr = [1, 2, 3, 5, 7, 8, 12, 14, 20, 25, 26, 28, 29, 30, 38, 40, 41, 48, 53, 66, 70, 71, 75, 76, 77, 78, 79,
          257, 258, 260, 261]
    assert set(lte) <= set(TABLE["lte"]) and set(nr) <= set(TABLE["nr"])
    for kind in ("lte", "nr"):
        for n, b in TABLE[kind].items():
            c = b["class"]
            assert c in ("low", "mid", "high", "mmwave") and b["use"] and len(b["use"]) < 50, (kind, n)
            want = "low" if b["mhz"] < 1000 else "mid" if b["mhz"] <= 2700 else "mmwave" if b["mhz"] > 24000 else "high"
            assert c == want, (kind, n, c, b["mhz"])


def test_all_carrier_files_valid():
    docs = carriers.load(Path("config/carriers"))
    assert carriers.validate_all(docs, TABLE) == []


UPLOAD_ONLY = {("nr", n) for n in (80, 81, 83, 84, 89, 95, 98)}
DOWNLOAD_ONLY = {("lte", 29), ("lte", 32), ("lte", 75), ("nr", 29), ("nr", 75), ("nr", 76)}


def _expected_use(kind, n, b):
    mhz = b["mhz"]
    freq = f"{mhz} MHz" if mhz < 3000 else f"{mhz / 1000:g} GHz"
    if (kind, n) in UPLOAD_ONLY:
        purpose = "extra upload capacity"
    elif (kind, n) in DOWNLOAD_ONLY:
        purpose = "extra download speed"
    else:
        purpose = {"low": "coverage indoors and outside towns", "mid": "extra speed in busy areas",
                   "high": "fast 5G" if kind == "nr" else "extra speed in busy areas",
                   "mmwave": "very fast 5G at short range"}[b["class"]]
    return f"{freq}: {purpose}"


def test_band_use_is_generic_frequency_and_purpose():
    for kind in ("lte", "nr"):
        for n, b in TABLE[kind].items():
            assert b["use"] == _expected_use(kind, n, b), (kind, n, b["use"])


def test_build_stops_on_an_invalid_carrier_file(tmp_path, capsys):
    from pricechecker.site import check_carriers
    d = _doc()
    _net(d)["lte"] = [999]
    (tmp_path / "DE.yaml").write_text(yaml.safe_dump(d))
    with pytest.raises(SystemExit) as e:
        check_carriers(tmp_path)
    assert "DE.yaml" in str(e.value) and "de-telekom" in str(e.value)
    d = _doc()
    _net(d)["sources"][0]["checked"] = date.today().isoformat()
    (tmp_path / "DE.yaml").write_text(yaml.safe_dump(d))
    check_carriers(tmp_path)
    assert capsys.readouterr().out == ""   # checked today: not stale


def test_build_logs_stale_networks(tmp_path, capsys):
    from pricechecker.site import check_carriers
    d = _doc()
    _net(d)["sources"][0]["checked"] = "2020-01-01"
    (tmp_path / "DE.yaml").write_text(yaml.safe_dump(d))
    check_carriers(tmp_path)
    assert "de-telekom (DE)" in capsys.readouterr().out
