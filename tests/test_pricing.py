"""pricing.py against shared cases (the JS port in static/ is tested against the same file)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pricechecker import pricing

CASES = json.loads(Path("tests/fixtures/pricing_cases.json").read_text())


def _run(case):
    s = pricing.Settings(*case["settings"])
    return pricing.cost(case["offer"], s, pricing.tax_rule(CASES["tax"], s))


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
def test_case(case):
    c = _run(case)
    exp = case["expect"]
    assert round(c.total, 2) == exp["total"]
    if "tax_added" in exp:
        assert round(c.tax_added, 2) == exp["tax_added"]
    if "unknowns" in exp:
        assert pricing.unknowns(c) == exp["unknowns"]
    if "approx" in exp:
        assert c.approx is exp["approx"]
    if "pay_ok" in exp:
        assert c.pay_ok is exp["pay_ok"]


def test_bank_vs_sale_splits_promo_and_adjustment():
    c = _run(next(x for x in CASES["cases"] if x["name"] == "bank_vs_sale_no_stack"))
    assert (c.promo_pct, round(c.adj_amt, 2)) == (0, -47.5)


def test_left_out():
    by = {x["name"]: _run(x) for x in CASES["cases"]}
    assert pricing.left_out(by["card_free_ship_tax_paid"]) == ""
    assert pricing.left_out(by["ship_not_listed"]) == "shipping and import tax"
    assert pricing.left_out(by["duties_false_eu_avg"]) == ""


def _c(**kw):
    base = dict(list=100, promo_amt=0, promo_pct=0, base=100, adj=0, adj_amt=0, ship=0.0, ship_min=False,
                tax_est=None, tax_added=0, total=100, approx=False, complete=True, pay_ok=True, old=False, duties=True)
    return pricing.Cost(**{**base, **kw})


def test_better_order():
    assert pricing.better(_c(), _c(pay_ok=False, total=1))              # payment accepted beats price
    assert pricing.better(_c(total=500), _c(old=True, total=1))         # current beats old
    assert pricing.better(_c(total=108), _c(ship=None, total=100))      # fewer unknowns beat 8 cheaper
    assert pricing.better(_c(total=99), _c(total=100))                  # then price
    assert not pricing.better(_c(total=100), _c(total=100))


def test_rank_skips_base_and_out_of_stock_and_orders_best_first():
    cheap, dear = (next(x for x in CASES["cases"] if x["name"] == n)["offer"] for n in ("duties_false_eu_avg", "card_free_ship_tax_paid"))
    s = pricing.Settings("EU", "", "card", "eur")
    rule = pricing.tax_rule(CASES["tax"], s)
    offers = [{**cheap, "storage": "base"}, {**dear, "available": False}, cheap, dear]
    assert [o for o, _ in pricing.rank(offers, s, rule)] == [dear, cheap]   # 1047 < 1113.20


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_mirror_matches_cases():
    r = subprocess.run(["node", "tests/js/pricing_cases.mjs"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
