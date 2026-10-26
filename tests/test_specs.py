from copy import deepcopy
from pathlib import Path

import yaml

from pricechecker import specs


def _sheets():
    return specs.load()


def test_every_catalog_phone_has_a_valid_sheet():
    ids = {p["id"] for p in yaml.safe_load(Path("config/catalog.yaml").read_text())["phones"]}
    sheets = _sheets()
    assert set(sheets) == ids, (ids - set(sheets), set(sheets) - ids)
    for i, s in sheets.items():
        assert specs.validate(s) == [], (i, specs.validate(s))


def test_oneplus16_china_misses_eu_800mhz():
    r = specs.band_check(_sheets()["oneplus-16"], "china")
    assert r["lte"] == [20] and r["nr"] == [20]
    assert "800 MHz" in r["why"][20]


def test_x9_ultra_china_has_main_eu_bands():
    r = specs.band_check(_sheets()["oppo-find-x9-ultra"], "china")
    assert r["lte"] == [] and r["nr"] == []


def test_unread_version_is_none():
    s = deepcopy(_sheets()["oppo-find-x9-ultra"])
    del s["bands"]["china"]
    assert specs.band_check(s, "china") is None
    assert specs.band_check(s, "global") is not None


def test_x9_ultra_has_7_differences():
    s = _sheets()["oppo-find-x9-ultra"]
    assert specs.differences(s) == 7
    assert s["groups"]["other"]["in_the_box"] == {"china": "Charger, cable, case", "global": None}   # shown split, not counted


def test_validate_rejects_unknown_field_and_third_party_source():
    base = _sheets()["oppo-find-x9-ultra"]
    assert specs.validate(base) == []
    bad = deepcopy(base)
    bad["groups"]["display"]["sparkle"] = "yes"
    assert any("sparkle" in p for p in specs.validate(bad))
    bad = deepcopy(base)
    bad["sources"]["global"]["url"] = "https://www.gsmarena.com/oppo_find_x9_ultra.php"
    assert any("gsmarena" in p for p in specs.validate(bad))
    bad = deepcopy(base)
    bad["sources"]["global"]["url"] = "https://notoppo.com/x"
    assert any("notoppo" in p for p in specs.validate(bad))


def test_every_catalog_brand_has_hosts_and_fields_are_snake_case():
    cat = yaml.safe_load(Path("config/catalog.yaml").read_text())["phones"]
    for b in {(p.get("brand") or p["name"].split()[0]).lower() for p in cat}:
        assert specs.BRAND_HOSTS[b], b
    assert specs.FIELDS["performance"]["top_cpu_speed"] == "Top CPU speed"
    assert specs.FIELDS["connectivity"]["china_model_number"] == "China model number"
    assert tuple(specs.FIELDS) == specs.GROUPS
