"""Versioned data files the browser loads (build/data/v1/): hashed names, no notes text, size budgets, and that the
offer inputs in them give pricing.js the same totals as pricing.py."""
import json
import re
import subprocess
from pathlib import Path

import pytest

from pricechecker import fx, pricing, run, terms
from pricechecker.site import context, data_files, offers

BUDGET = 60_000


@pytest.fixture(scope="module")
def data():
    stores, catalog = run.load_config()
    return context.load(catalog, stores, fx.cached(), terms.saved_status())


@pytest.fixture(scope="module")
def phones(data):
    return offers.assemble(data)


@pytest.fixture(scope="module")
def built(data, phones, tmp_path_factory):
    out = tmp_path_factory.mktemp("build")
    return out, data_files.write(data, out, phones)


def test_hash_names_change_with_content(data, phones, tmp_path):
    a = data_files.write(data, tmp_path / "a", phones)
    again = data_files.write(data, tmp_path / "b", phones)
    assert a == again                                   # same content, same names
    assert re.fullmatch(r"/data/v1/tax\.[0-9a-f]{10}\.json", a["tax"])
    assert re.fullmatch(r"/data/v1/home-EU-1\.[0-9a-f]{10}\.json", a["home/EU"][0])
    assert re.fullmatch(rf"/data/v1/phone/{phones[0]['id']}\.[0-9a-f]{{10}}\.json", a["phone/" + phones[0]["id"]])
    data.tax_cfg["EU"]["rate_pct"] += 1                 # content changes -> the tax file's name changes
    try:
        c = data_files.write(data, tmp_path / "c", phones)
    finally:
        data.tax_cfg["EU"]["rate_pct"] -= 1
    assert c["tax"] != a["tax"] and c["home/EU"] == a["home/EU"]


def test_phone_file_has_no_notes_text(built, phones):
    out, names = built
    p = next(p for p in phones if p["offers"])
    raw = (out / names["phone/" + p["id"]].lstrip("/")).read_text()
    doc = json.loads(raw)
    assert doc["v"] == 1 and set(doc) == {"v", "offers", "lines", "bands"}
    for o in doc["offers"]:
        assert not {"notes", "coupons", "buyers", "gplay", "trend", "url", "title"} & set(o)
    assert "notes" not in raw


def test_budgets(built):
    out, _ = built
    files = list((out / "data" / "v1").rglob("*.json"))
    assert files
    big = {str(f.relative_to(out)): f.stat().st_size for f in files if f.stat().st_size > BUDGET}
    assert not big, big


def _load(out, paths):
    return [o for path in paths for o in json.loads((out / path.lstrip("/")).read_text())["offers"]]


def test_every_region_has_home_files_within_budget(built):
    out, names = built
    for region in terms.REGIONS:
        paths = names[f"home/{region}"]
        assert paths and all(re.fullmatch(rf"/data/v1/home-{region}-\d+\.[0-9a-f]{{10}}\.json", x) for x in paths)
        for x in paths:
            assert (out / x.lstrip("/")).stat().st_size <= BUDGET
            for o in json.loads((out / x.lstrip("/")).read_text())["offers"]:
                assert set(o.get("ship") or {}) <= {region} and set(o.get("duties") or {}) <= {region}


@pytest.mark.parametrize("s", [pricing.Settings("UK", "", "bank", "gbp"), pricing.Settings("US", "", "card", "usd"),
                               pricing.Settings("EU", "DE", "paypal", "eur"), pricing.Settings("CA", "ON", "card", "cad")])
def test_home_files_rerank_like_the_phone_pages(built, data, phones, s):
    out, names = built
    rule = pricing.tax_rule(data.tax_cfg, s)
    rows = _load(out, names[f"home/{s.region}"])
    checked = 0
    for p in phones:
        full = [o for o in p["offers"] if o["available"] and not o["old"]]
        for e in p["editions"]:
            want = pricing.rank([o for o in full if o["edition"] == e], s, rule)
            got = pricing.rank([o for o in rows if o["id"] == p["id"] and o["edition"] == e], s, rule)
            assert bool(want) == bool(got)
            if want:
                checked += 1
                (w, wc), (g, gc) = want[0], got[0]
                assert (g["store_label"], g["storage"]) == (w["store_label"], w["storage"])
                assert round(gc.total, 2) == round(wc.total, 2)
    assert checked > 10


def test_offer_inputs_feed_pricing_js(built, data, phones):
    out, names = built
    p = max(phones, key=lambda p: len(p["offers"]))
    f = out / names["phone/" + p["id"]].lstrip("/")
    r = subprocess.run(["node", "tests/js/pricing_cases.mjs", "--offers", str(f), "--tax", str(out / names["tax"].lstrip("/"))],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    # non-EU combo through the same runner: UK, bank, GBP
    r2 = subprocess.run(["node", "tests/js/pricing_cases.mjs", "--offers", str(f), "--tax", str(out / names["tax"].lstrip("/")),
                         "--settings", "UK,,bank,gbp"], capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    uk = pricing.Settings("UK", "", "bank", "gbp")
    for g, o in zip(json.loads(r2.stdout), json.loads(f.read_text())["offers"]):
        assert round(g, 2) == round(pricing.cost(o, uk, pricing.tax_rule(data.tax_cfg, uk)).total, 2)
    doc = json.loads(f.read_text())
    s = pricing.Settings("EU", "", "card", "eur")
    rule = pricing.tax_rule(data.tax_cfg, s)
    assert len(got) == len(doc["offers"]) > 3
    for g, o in zip(got, doc["offers"]):
        assert round(g, 2) == round(pricing.cost(o, s, rule).total, 2)
    # and the file's inputs give the same totals as the full offers the pages use
    for o, full in zip(doc["offers"], p["offers"]):
        assert round(pricing.cost(o, s, rule).total, 2) == round(pricing.cost(full, s, rule).total, 2)
