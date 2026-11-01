import json
import re
import shutil
import subprocess
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


def test_build_names_the_file_for_yaml_syntax_errors_and_non_mapping_files(tmp_path):
    from pricechecker.site import check_carriers
    (tmp_path / "FR.yaml").write_text("country: FR\nnetworks: [unclosed\n  - x: : :\n")
    with pytest.raises(SystemExit) as e:
        check_carriers(tmp_path)
    assert "FR.yaml" in str(e.value) and "YAML" in str(e.value)
    (tmp_path / "FR.yaml").write_text("- id: a\n- id: b\n")
    with pytest.raises(SystemExit) as e:
        check_carriers(tmp_path)
    assert "FR.yaml" in str(e.value) and "mapping" in str(e.value) and "list" in str(e.value)


def test_name_has_no_brackets_or_commas():
    for bad in ("Rogers (incl. Fido)", "TDC Net, YouSee"):
        d = _doc()
        _net(d)["name"] = bad
        assert any("de-telekom" in e and "plain brand name" in e for e in carriers.validate(d, TABLE)), bad


def test_build_logs_stale_networks(tmp_path, capsys):
    from pricechecker.site import check_carriers
    d = _doc()
    _net(d)["sources"][0]["checked"] = "2020-01-01"
    (tmp_path / "DE.yaml").write_text(yaml.safe_dump(d))
    check_carriers(tmp_path)
    assert "de-telekom (DE)" in capsys.readouterr().out


# ---- verdict and country summary (mirrored by static/js/carriers.js) ----

def _b(mhz, cls, use):
    return {"mhz": mhz, "class": cls, "use": use}


VT = {  # a synthetic band table, so the cases do not move with config/bands.yaml
    "lte": {1: _b(2100, "mid", "2100 MHz: mid"), 2: _b(1900, "mid", "1900 MHz: mid"), 3: _b(1800, "mid", "1800 MHz: mid"),
            7: _b(2600, "mid", "2600 MHz: extra speed in busy areas"), 20: _b(800, "low", "800 MHz: coverage indoors and outside towns"),
            28: _b(700, "low", "700 MHz: low"), 12: _b(700, "low", "700 MHz: low12"), 17: _b(700, "low", "700 MHz: low17"),
            25: _b(1900, "mid", "1900 MHz: mid25"),
            29: {**_b(700, "low", "700 MHz: extra download speed"), "supplementary": True}},
    "nr": {78: _b(3500, "high", "3.5 GHz: fast 5G"), 77: _b(3700, "high", "3.7 GHz: fast 5G"), 3: _b(1800, "mid", "1800 MHz: mid"),
           28: _b(700, "low", "700 MHz: low"), 258: _b(26000, "mmwave", "26 GHz: very fast 5G at short range")},
    "covers": {"lte": {12: [17], 25: [2], 3: [2, 1]}, "nr": {77: [78], 78: [3]}},
}


def _n(name="O2", lte=(1, 7, 20), nr=(78,), basis="licensed", complete=True):
    return {"id": name.lower(), "name": name, "lte": None if lte is None else list(lte),
            "nr": None if nr is None else list(nr), "basis": basis, "complete": complete}


def _p(lte=(1, 7, 20), nr=(78,)):
    return {"lte": None if lte is None else list(lte), "nr": None if nr is None else list(nr)}


def _v(phone, net):
    return carriers.verdict(phone, net, VT)


def test_verdict_unknown_phone_or_network():
    assert _v(None, _n())["kind"] == "unknown"
    assert _v(None, _n())["text"] == "Bands not published for this version"
    assert _v(_p(None, None), _n())["kind"] == "unknown"
    r = _v(_p(), _n(lte=None, nr=None))
    assert r["kind"] == "unknown" and r["missing"] == []
    assert _v(_p(lte=[]), _n(lte=None, nr=None, complete=False))["kind"] == "unknown"   # beats risk: nothing to judge


def test_verdict_risk_names_the_band_and_who_holds_it():
    r = _v(_p(lte=[1, 7]), _n())
    assert r["kind"] == "risk"
    assert r["text"] == "Coverage risk: no band 20, which O2 holds (800 MHz: coverage indoors and outside towns)"
    assert r["missing"] == [{"kind": "lte", "n": 20, "mhz": 800, "use": "800 MHz: coverage indoors and outside towns"}]
    r = _v(_p(lte=[1, 7]), _n(basis="used"))
    assert "which O2 uses (800" in r["text"]


def test_verdict_missing_supplementary_band_is_minor_never_risk():
    net = _n("T", lte=[1, 29, 12], nr=[78], basis="used")
    r = _v(_p(lte=[1, 12], nr=[78]), net)
    assert r["kind"] == "minor" and r["text"].startswith("Works; no band 29, which T uses (700 MHz: extra download speed)")
    r = _v(_p(lte=[1], nr=[78]), net)
    assert r["kind"] == "risk" and r["text"].startswith("Coverage risk: no band 12,") and "band 29" not in r["text"]
    assert [m["n"] for m in r["missing"]] == [29, 12]
    assert _v(_p(lte=[1, 12, 29], nr=[78]), {**net, "complete": True})["kind"] == "full"


def test_verdict_risk_beats_4g_only_and_minor():
    r = _v(_p(lte=[1], nr=[]), _n(lte=[1, 7, 20], nr=[78]))   # misses low 20, also mid 7 and all NR
    assert r["kind"] == "risk"
    assert [(m["kind"], m["n"]) for m in r["missing"]] == [("lte", 7), ("lte", 20), ("nr", 78)]
    assert r["text"].count("band") == 1   # only the low band is named as the risk


def test_verdict_low_nr_band_is_a_risk_too():
    r = _v(_p(nr=[78]), _n(lte=[1], nr=[28, 78]))
    assert r["kind"] == "risk"
    assert r["text"].startswith("Coverage risk: no 5G band n28, which O2 holds (700 MHz")


def test_verdict_4g_only():
    r = _v(_p(nr=[]), _n())
    assert r["kind"] == "4g" and r["text"] == "4G works; no 5G on this network"
    assert _v(_p(nr=[3]), _n())["kind"] == "4g"   # has an NR band, but none of the network's
    assert _v(_p(nr=None), _n())["kind"] == "nogaps"   # phone nr unknown: not "no 5G"


def test_verdict_never_4g_only_without_network_5g():
    assert _v(_p(nr=[]), _n(nr=[]))["kind"] == "full"
    assert _v(_p(nr=[]), _n(nr=[], complete=False))["kind"] == "nogaps"
    assert _v(_p(nr=[]), _n(nr=None))["kind"] == "nogaps"


def test_verdict_4g_only_needs_every_lte_band():
    r = _v(_p(lte=[1], nr=[]), _n(lte=[1, 7], nr=[78]))   # misses mid 7: minor, with the NR band listed
    assert r["kind"] == "minor"


def test_verdict_minor_lists_every_missing_band_nr_included():
    r = _v(_p(lte=[1, 20], nr=[3]), _n(lte=[1, 7, 20], nr=[3, 78, 258], basis="used"))
    assert r["kind"] == "minor"
    assert [(m["kind"], m["n"]) for m in r["missing"]] == [("lte", 7), ("nr", 78), ("nr", 258)]
    assert r["text"] == ("Works; no band 7, which O2 uses (2600 MHz: extra speed in busy areas); "
                         "no 5G band n78, which O2 uses (3.5 GHz: fast 5G); "
                         "no 5G band n258, which O2 uses (26 GHz: very fast 5G at short range)")
    assert "uses" in _v(_p(lte=[1, 20]), _n(basis="used"))["text"]


def test_verdict_minor_all_nr_missing_is_one_clause_but_missing_stays_complete():
    r = _v(_p(lte=[1, 20], nr=[3]), _n(lte=[1, 7, 20], nr=[78, 258], basis="used"))
    assert r["kind"] == "minor"
    assert r["text"] == "Works; no band 7, which O2 uses (2600 MHz: extra speed in busy areas); no 5G on this network"
    assert [(m["kind"], m["n"]) for m in r["missing"]] == [("lte", 7), ("nr", 78), ("nr", 258)]


def test_verdict_mmwave_counts_only_on_used_networks():
    phone = _p(lte=[1, 7, 20], nr=[78])
    r = _v(phone, _n(nr=[78, 258], basis="licensed"))
    assert r["kind"] == "full" and r["missing"] == []
    r = _v(phone, _n(nr=[78, 258], basis="used"))
    assert r["kind"] == "minor" and [m["n"] for m in r["missing"]] == [258]
    assert _v(_p(nr=[]), _n(nr=[258], basis="licensed"))["kind"] == "full"   # nothing but mmWave: no 5G network to miss
    assert _v(_p(nr=[]), _n(nr=[258], basis="used"))["kind"] == "4g"


def test_verdict_nothing_compared_is_unknown():
    ver, net = "Bands not published for this version", "Bands not published for this network"
    r = _v(_p(), _n(lte=None, nr=[]))
    assert (r["kind"], r["text"]) == ("unknown", net)
    assert _v(_p(), _n(lte=[], nr=[]))["text"] == net
    assert _v(_p(), _n(lte=None, nr=[258], basis="licensed"))["text"] == net   # mmWave ignored: nothing left
    assert _v(_p(lte=None, nr=[78]), _n(lte=[1], nr=[]))["text"] == ver
    assert _v(_p(lte=None), _n(lte=[1], nr=None))["text"] == ver
    assert _v(_p(), _n(lte=[], nr=[78]))["kind"] != "unknown"   # 5G is compared
    assert _v(_p(lte=None, nr=[78]), _n(lte=[1], nr=[78]))["kind"] == "nogaps"


def test_verdict_no_gaps_found_versus_works_fully():
    assert _v(_p(), _n(complete=False)) == {"kind": "nogaps", "missing": [], "text": "No gaps on the bands we could confirm"}
    assert _v(_p(), _n()) == {"kind": "full", "missing": [], "text": "Works fully on 4G and 5G"}
    assert _v(_p(lte=[1, 7, 20, 28], nr=[78, 3]), _n())["kind"] == "full"   # extra phone bands do not matter


def test_verdict_null_on_one_side_judges_the_known_part_and_is_never_full():
    r = _v(_p(), _n(lte=None, nr=[78]))
    assert r["kind"] == "nogaps"
    r = _v(_p(nr=[]), _n(lte=None, nr=[78]))
    assert r["kind"] == "minor" and r["missing"][0]["n"] == 78   # LTE unknown: no "4G works" claim
    r = _v(_p(lte=[1]), _n(lte=[1, 7], nr=None))
    assert r["kind"] == "minor" and [m["n"] for m in r["missing"]] == [7]
    assert _v(_p(lte=[1, 7]), _n(lte=[1, 7], nr=None))["kind"] == "nogaps"
    assert _v(_p(lte=[1]), _n(lte=[1, 20], nr=None))["kind"] == "risk"


def test_verdict_phone_null_list_judges_the_known_part_and_is_never_full():
    r = _v(_p(nr=None), _n())
    assert r["kind"] == "nogaps" and r["missing"] == []
    r = _v(_p(nr=None, lte=[1]), _n())
    assert r["kind"] == "risk" and [m["n"] for m in r["missing"]] == [7, 20]
    assert _v(_p(nr=None, lte=[1, 20]), _n())["kind"] == "minor"
    assert _v(_p(nr=None), _n(lte=[1], nr=[78]))["kind"] == "nogaps"
    assert _v(_p(nr=None), _n(lte=None, nr=[78]))["text"] == "Bands not published for this version"   # nothing left to judge
    r = _v(_p(lte=None, nr=[78]), _n())
    assert r["kind"] == "nogaps"
    assert _v(_p(lte=None, nr=[]), _n())["kind"] == "minor"   # lte unknown, 5G judged: lacks n78
    assert _v({"lte": [1, 7, 20]}, _n())["kind"] == "nogaps"   # absent nr = null


def test_verdict_superset_bands_count_as_having_the_band():
    assert _v(_p(nr=[77]), _n(lte=[1], nr=[78]))["kind"] == "full"        # n77 holds n78
    assert _v(_p(lte=[1, 12], nr=[78]), _n(lte=[1, 17], nr=[78]))["kind"] == "full"   # 12 holds 17
    assert _v(_p(lte=[1, 25], nr=[78]), _n(lte=[1, 2], nr=[78]))["kind"] == "full"
    r = _v(_p(nr=[78]), _n(lte=[1], nr=[77]))                             # the reverse does not hold
    assert r["kind"] == "4g" and [m["n"] for m in r["missing"]] == [77]
    r = _v(_p(lte=[1, 17], nr=[78]), _n(lte=[1, 12], nr=[78]))
    assert r["kind"] == "risk" and r["missing"][0]["n"] == 12
    assert _v(_p(nr=[77]), _n(lte=[1], nr=[78]))["missing"] == []


def test_verdict_superset_follows_chains():
    assert _v(_p(lte=[3], nr=[78]), _n(lte=[1, 2], nr=[3]))["kind"] == "full"   # 3 covers 2 and 1; n78 covers n3 (chain n77 > n78 > n3)
    assert _v(_p(lte=[1], nr=[77]), _n(lte=[1], nr=[3]))["kind"] == "full"


def test_covers_has_no_unclosed_chain_in_the_real_table():
    for kind, d in TABLE["covers"].items():
        for big, smalls in d.items():
            assert set(carriers._held(kind, [big], TABLE)) == {big, *smalls}, (kind, big)


def test_verdict_superset_is_per_kind():
    assert _v(_p(lte=[1, 77], nr=[]), _n(lte=[1], nr=[78]))["kind"] == "4g"   # lte "77" is no nr band


def test_real_covers_pairs_exist_in_the_table_and_nest_by_frequency():
    cov = TABLE["covers"]
    assert {(k, a, b) for k in cov for a, bs in cov[k].items() for b in bs} >= {
        ("nr", 77, 78), ("lte", 66, 4), ("lte", 12, 17), ("lte", 25, 2), ("lte", 26, 5), ("nr", 25, 2), ("nr", 26, 5)}
    for kind, d in cov.items():
        for big, smalls in d.items():
            assert big in TABLE[kind]
            for s in smalls:
                assert s in TABLE[kind] and s != big, (kind, big, s)
                assert d.get(s, []) == [] or big not in d[s]   # no loops
    r = carriers.verdict(_p(lte=[1], nr=[77]), {**_n(lte=[1], nr=[78]), "complete": True}, TABLE)
    assert r["kind"] == "full"
    r = carriers.verdict(_p(lte=[1], nr=[78]), {**_n(lte=[1], nr=[77]), "complete": True}, TABLE)
    assert [m["n"] for m in r["missing"]] == [77]


def _doc3(*nets):
    return {"country": "DE", "networks": list(nets)}


def test_summary_wording():
    full = [_n("A"), _n("B")]
    s = carriers.summary(_p(), _doc3(*full), VT, "Germany")
    assert s["text"] == "In Germany: works fully on all 2 networks"
    assert s["counts"] == {"unknown": 0, "risk": 0, "4g": 0, "minor": 0, "nogaps": 0, "full": 2}
    s = carriers.summary(_p(lte=[1, 7]), _doc3(_n("Telekom", lte=[1, 7]), _n("Vodafone", lte=[1, 7]), _n("O2")), VT, "Germany")
    assert s["text"] == "In Germany: coverage risk on O2 (no band 20); works fully on 2 of 3 networks"
    assert s["counts"]["full"] == 2 and s["counts"]["risk"] == 1


def test_summary_groups_networks_by_verdict_in_network_order():
    nets = [_n("A", lte=[1], nr=[78]), _n("B", lte=[1, 3], nr=[78]), _n("C", lte=[1], nr=[77]), _n("D", lte=None, nr=None),
            _n("E", lte=[1], nr=[78], complete=False), _n("F", lte=[28]), _n("G", lte=[1, 7]), _n("H", lte=[1], nr=[78], complete=False),
            _n("I", lte=[1], nr=[77]), _n("J", lte=[20])]
    s = carriers.summary(_p(lte=[1, 7], nr=[78]), _doc3(*nets), VT, "Germany")
    assert s["text"] == ("In Germany: coverage risk on F (no band 28) and J (no band 20); 4G only on C and I (no 5G); "
                         "minor gaps on B (no band 3); no gaps found on E and H; works fully on 2 of 10 networks; "
                         "bands unknown on D")
    assert s["counts"] == {"unknown": 1, "risk": 2, "4g": 2, "minor": 1, "nogaps": 2, "full": 2}
    s = carriers.summary(_p(lte=[1, 7], nr=[3]), _doc3(_n("B", lte=[1], nr=[3, 78])), VT, "Germany")
    assert s["text"] == "In Germany: minor gaps on B (no 5G band n78)"
    s = carriers.summary(_p(lte=[1, 7], nr=[3]), _doc3(_n("B", lte=[1, 3], nr=[78])), VT, "Germany")
    assert s["text"] == "In Germany: minor gaps on B (no band 3)"
    s = carriers.summary(_p(lte=[1, 7, 20], nr=[3]), _doc3(_n("B", lte=[1, 7, 20], nr=[78, 258], basis="used")), VT, "Germany")
    assert s["text"] == "In Germany: 4G only on B (no 5G)"
    s = carriers.summary(_p(lte=[1, 20], nr=[3]), _doc3(_n("B", lte=[1, 7], nr=[78], basis="used")), VT, "Germany")
    assert s["text"] == "In Germany: minor gaps on B (no band 7)"


def test_summary_no_gaps_found_names_all_networks():
    nets = [_n(x, complete=False) for x in ("Telekom", "Vodafone", "O2", "1&1")]
    assert carriers.summary(_p(), _doc3(*nets), VT, "Germany")["text"] == \
        "In Germany: no gaps found on Telekom, Vodafone, O2 and 1&1"
    assert carriers.summary(_p(), _doc3(*nets[:2]), VT, "Germany")["text"] == "In Germany: no gaps found on Telekom and Vodafone"


def test_summary_one_network_works_fully():
    assert carriers.summary(_p(), _doc3(_n("A")), VT, "Malta")["text"] == "In Malta: works fully on its only network"


def test_summary_all_unknown_and_phone_unknown():
    s = carriers.summary(_p(), _doc3(_n("A", lte=None, nr=None), _n("B", lte=None, nr=None)), VT, "Germany")
    assert s["text"] == "In Germany: bands unknown on A and B"
    assert s["counts"]["unknown"] == 2 and s["counts"]["full"] == 0
    for ph in (None, _p(None, None)):
        s = carriers.summary(ph, _doc3(_n("A"), _n("B")), VT, "Germany")
        assert s["text"] == "In Germany: bands not published for this version"
        assert s["counts"] == {"unknown": 2, "risk": 0, "4g": 0, "minor": 0, "nogaps": 0, "full": 0}


def test_summary_none_full_starts_with_the_first_reason():
    s = carriers.summary(_p(lte=[1]), _doc3(_n("A", lte=[1, 20]), _n("B", lte=[1, 7], nr=[])), VT, "Germany")
    assert s["text"] == "In Germany: coverage risk on A (no band 20); minor gaps on B (no band 7)"


def test_country_names_cover_every_country():
    assert set(carriers.COUNTRY_NAMES) == set(carriers.COUNTRIES)
    assert carriers.COUNTRY_NAMES["DE"] == "Germany"


def _cases():
    nets = [_n(), _n(basis="used"), _n("X", lte=None, nr=[78]), _n("Y", lte=[1, 12], nr=[77, 78], complete=False),
            _n("Z", lte=None, nr=None), _n("W", lte=[1], nr=[]), _n("V", lte=[1, 17, 2], nr=[78, 28, 258]),
            _n("M", lte=[1, 7], nr=[78, 258], basis="used"), _n("Q", lte=None, nr=[]), _n("R", lte=[], nr=[258]), _n("S", lte=[1, 7, 20], nr=[3, 78, 3], complete=False),
            _n("T", lte=[1, 29, 12], nr=[78], basis="used")]
    phones = [None, _p(None, None), _p(nr=None), _p(lte=None), _p(), _p(lte=[1, 7]), _p(lte=[1], nr=[]), _p(nr=[77]), _p(lte=[1, 12, 25], nr=[3, 77]),
              _p(lte=[], nr=None), _p(lte=[1, 7, 20], nr=[]), _p(lte=None, nr=[78]), _p(lte=[3], nr=[77]), {"lte": [1, 7, 20]}, _p(lte=[1, 7, 20, 28], nr=[78, 28, 258]),
              _p(lte=[1, 12], nr=[78]), _p(lte=[1], nr=[78]), _p(lte=[1, 12, 29], nr=[78])]
    return nets, phones


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_verdict_and_summary_match_the_js(tmp_path):
    nets, phones = _cases()
    names = ["Germany", "Chad"]
    doc = {"phones": phones, "networks": nets, "table": VT, "names": names}
    f = tmp_path / "c.json"
    f.write_text(json.dumps(doc))
    r = subprocess.run(["node", "tests/js/carrier_cases.mjs", str(f)], check=False, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    want_v = [[carriers.verdict(p, n, VT) for n in nets] for p in phones]
    assert got["verdicts"] == want_v
    want_s = [carriers.summary(p, _doc3(*nets[:k]), VT, names[0]) for p in phones for k in (1, 3, 7, 11)]
    assert got["summaries"] == want_s
    assert {v["kind"] for row in want_v for v in row} == {"unknown", "risk", "4g", "minor", "nogaps", "full"}


def test_country_for_settings_python():
    from pricechecker.pricing import Settings
    s = lambda region, area="": Settings(region, area, "card", "eur")
    assert carriers.country_for(s("EU", "DE")) == "DE" and carriers.country_for(s("EU")) is None
    assert carriers.country_for(s("UK")) == "GB" and carriers.country_for(s("CA", "ON")) == "CA" and carriers.country_for(s("Global", "DE")) is None


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_country_for_and_names_match_the_js():
    from pricechecker.pricing import Settings
    cases = [(r, a) for r in ("EU", "UK", "US", "CA", "AU", "Global") for a in ("", "DE", "ON")]
    js = ('import {countryFor, COUNTRY_NAMES} from "./static/js/carriers.js";'
          f'const c = {json.dumps(cases)};'
          'console.log(JSON.stringify({got: c.map(([region, area]) => countryFor({region, area})), names: COUNTRY_NAMES}));')
    r = subprocess.run(["node", "--input-type=module", "-e", js], check=False, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["got"] == [carriers.country_for(Settings(r_, a, "card", "eur")) for r_, a in cases]
    assert out["names"] == carriers.COUNTRY_NAMES and list(out["names"]) == list(carriers.COUNTRY_NAMES)
