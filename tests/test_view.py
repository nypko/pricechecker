"""The shared view model (pricechecker/site/view.py, mirrored by static/js/view.js)."""
import json
import shutil
import subprocess

import pytest

from pricechecker import derive, fx, pricing, run, terms
from pricechecker.site import context, data_files, offers, seo, view

# reads the saved prices or the real build: excluded from the hourly production run (pytest -m "not live")
live = pytest.mark.live

SETTINGS = [("EU", "", "card", "eur"), ("EU", "DE", "paypal", "eur"), ("UK", "", "bank", "gbp"),
            ("CA", "ON", "card", "cad"), ("US", "", "card", "usd")]


@pytest.fixture(scope="module")
def data():
    stores, catalog = run.load_config()
    return context.load(catalog, stores, fx.cached(), terms.saved_status())


@pytest.fixture(scope="module")
def phones(data):
    return offers.assemble(data)


def _inputs(p):
    return [data_files.offer_inputs(o) for o in p["offers"]]


def _o(**kw):
    base = {"money": {"eur": 1000}, "pay": {"card": 0}, "ship": {"EU": {"eur": 0}, "US": {"eur": 0}}, "duties": {"EU": True},
            "available": True, "store_label": "S", "edition": "global", "storage": "12/256"}
    return {**base, **kw}


@live
def test_headline_matches_title_price(phones, data):
    seen = 0
    for p in phones:
        t = seo._title_price(p["offers"], data.tax_cfg)
        if t is None:
            continue
        seen += 1
        first = next(r for r in view.rows(_inputs(p), data.tax_cfg, view.DEFAULT) if r["state"] == "ok")
        assert first["total"] == pytest.approx(t[0])
    assert seen


def _stale_case():
    """Stale rows go after every other priced row, a store that doesn't take the payment included (spec 4.2)."""
    return [_o(money={"eur": 500}, old=True, store_label="old"), _o(money={"eur": 900}, store_label="new"),
            _o(money={"eur": 400}, pay_ok={"card": False}, store_label="nopay"), _o(money={"eur": 300}, ship={}, store_label="unk"),
            _o(available=False, store_label="sold"), _o(ship={"EU": False}, store_label="nod")]


STALE_ORDER = [("new", "ok"), ("unk", "ok"), ("nopay", "nopay"), ("old", "stale"), ("nod", "nodelivery"), ("sold", "soldout")]


def test_stale_cheaper_offer_ranks_after_current_and_best_of_skips_it():
    cheap_old, dear = _o(money={"eur": 500}, old=True, store_label="old"), _o(money={"eur": 900}, store_label="new")
    rs = view.rows([cheap_old, dear], {}, view.DEFAULT)
    assert [(r["store"], r["state"]) for r in rs] == [("new", "ok"), ("old", "stale")]
    assert [(r["store"], r["state"]) for r in view.rows(_stale_case(), {}, view.DEFAULT)] == STALE_ORDER
    assert view.best_of(rs, "global")["store"] == "new"
    assert view.best_of(view.rows([cheap_old], {}, view.DEFAULT), "global") is None


def test_no_delivery_state_and_ordering_and_precedence():
    nod = _o(ship={"US": False}, store_label="nod")
    sold = _o(available=False, store_label="sold")
    soldnod = _o(available=False, ship={"US": False}, store_label="soldnod")
    ok = _o(ship={"US": {"eur": 0}}, store_label="ok")
    rs = view.rows([soldnod, sold, nod, ok], {}, pricing.Settings("US", "", "card", "eur"))
    assert [(r["store"], r["state"]) for r in rs] == [("ok", "ok"), ("nod", "nodelivery"), ("soldnod", "soldout"), ("sold", "soldout")]
    assert rs[1]["delivers"] is False and rs[1]["available"] is True


def test_nopay_and_tail_and_base():
    nopay = _o(pay_ok={"card": False}, store_label="np")
    unk = _o(ship={}, duties=None, storage="base", store_label="unk")
    rs = view.rows([nopay, unk], {"EU": {"rate_pct": 20}}, view.DEFAULT)
    by = {r["store"]: r for r in rs}
    assert by["np"]["state"] == "nopay"
    assert by["unk"]["tail"] == "+ shipping, tax?" and by["unk"]["settled"] is False
    assert view.best_of(rs, "global", "12/256") is None          # exact storage match; the only 12/256 row is nopay
    assert view.best_of(rs, "global")["store"] == "unk"           # a base row may be the best (it leads the title price)
    assert view.best_of(rs, "global", "base")["store"] == "unk"


@live
def test_gap_matches_derive_gap(phones, data):
    rule = pricing.tax_rule(data.tax_cfg, view.DEFAULT)
    n = 0
    for p in phones:
        want = derive.gap(p["offers"], rule)
        got = view.gap(view.rows(_inputs(p), data.tax_cfg, view.DEFAULT))
        assert got == want, p["id"]
        n += want is not None
    assert n


def _close(a, b, path=""):
    if isinstance(a, float) or isinstance(b, float):
        assert a is not None and b is not None and abs(a - b) < 0.01, (path, a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            _close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _close(x, y, f"{path}[{i}]")
    else:
        assert a == b, (path, a, b)


def _samples(phones):
    ids = ["oppo-find-x9-ultra", "oneplus-16", "google-pixel-11-pro"]
    by = {p["id"]: p for p in phones}
    ids = [i for i in ids if i in by]
    promo = next((p["id"] for p in phones if any(o.get("promo") for o in p["offers"]) and p["id"] not in ids), None)
    stale = next((p["id"] for p in phones if any(o.get("old") for o in p["offers"]) and p["id"] not in ids + [promo]), None)
    if promo is None:
        print("no phone with a promo in the saved data: promo case skipped")
    if stale is None:
        print("no phone with an old offer in the saved data: stale case skipped")
    return ids + [i for i in (promo, stale) if i]


@live
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_view_matches_python(site_build, phones, data):
    v1 = site_build / "data" / "v1"
    tax_file = next(v1.glob("tax.*.json"))
    tax = json.loads(tax_file.read_text())
    ids = _samples(phones)
    assert len(ids) >= 3
    for pid in ids:
        f = next((v1 / "phone").glob(f"{pid}.*.json"))
        inputs = json.loads(f.read_text())["offers"]
        for st in SETTINGS:
            r = subprocess.run(["node", "tests/js/view_cases.mjs", "--phone", str(f), "--tax", str(tax_file), "--settings", ",".join(st)],
                               check=False, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
            _close(json.loads(r.stdout), json.loads(json.dumps(view.rows(inputs, tax, pricing.Settings(*st)))), f"{pid}{st}")


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_rows_order_stale_last(tmp_path):
    """The saved prices may have no stale store, so the JS order is checked on a made-up phone too."""
    f = tmp_path / "phone.json"
    f.write_text(json.dumps({"offers": _stale_case()}))
    tax = tmp_path / "tax.json"
    tax.write_text("{}")
    r = subprocess.run(["node", "tests/js/view_cases.mjs", "--phone", str(f), "--tax", str(tax), "--settings", "EU,,card,eur"],
                       check=False, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert [(x["store"], x["state"]) for x in json.loads(r.stdout)] == STALE_ORDER


def _picks_case():
    """China 12/256 + 16/512 current; Global 12/512 + 16/512 current, 16/1024 sold out; Global also lists 'base'."""
    return [_o(edition="china", storage="12/256"), _o(edition="china", storage="16/512", money={"eur": 1200}),
            _o(edition="global", storage="12/512"), _o(edition="global", storage="16/512", money={"eur": 1300}),
            _o(edition="global", storage="16/1024", available=False), _o(edition="global", storage="base", money={"eur": 900})]


def _picks_rows(offers=None):
    return view.rows(offers if offers is not None else _picks_case(), {}, view.DEFAULT)


def test_nearest_memory():
    rs = _picks_rows()
    assert view.nearest_memory(rs, "global", "16/1024") == "16/512"   # the sold-out 16/1024 doesn't count
    assert view.nearest_memory(rs, "global", "12/512") == "12/512"
    assert view.nearest_memory(rs, "china", "12/512") == "16/512"
    assert view.nearest_memory(rs, "global", "base") in ("12/512", "16/512")   # "base" is never offered back
    only_sold = _picks_rows([_o(edition="china", available=False), _o(edition="global")])
    assert view.nearest_memory(only_sold, "china", "12/256") is None


def test_default_pick_is_first_ok_row():
    rs = _picks_rows()
    first = next(r for r in rs if r["state"] == "ok")
    assert view.default_pick(rs) == {"ed": first["edition"], "mem": first["storage"]}
    assert view.default_pick(_picks_rows([_o(available=False)])) is None


def test_pick_for_memory():
    rs = _picks_rows()
    assert view.pick_for_memory(rs, "16/512", "china") == {"ed": "china", "mem": "16/512"}   # preferred has it: kept
    assert view.pick_for_memory(rs, "12/512", "china") == {"ed": "global", "mem": "12/512"}   # only the other version has it
    assert view.pick_for_memory(rs, "12/256", "global") == {"ed": "china", "mem": "12/256"}
    assert view.pick_for_memory(rs, "16/1024", "global") == view.default_pick(rs)   # neither has it current: the default
    assert view.pick_for_memory(_picks_rows([_o(available=False)]), "12/256", "china") == {"ed": "china", "mem": "12/256"}


def _run_picks(phone_file, tax_file, st):
    r = subprocess.run(["node", "tests/js/view_cases.mjs", "--picks", "--phone", str(phone_file), "--tax", str(tax_file), "--settings", st],
                       check=False, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def _py_picks(inputs, tax, st):
    rs = view.rows(inputs, tax, pricing.Settings(*st.split(",")))
    out = {"default": view.default_pick(rs), "nearest": {}, "pick": {}}
    for mem in {r["storage"] for r in rs}:
        for ed in ("china", "global"):
            out["nearest"][f"{ed} {mem}"] = view.nearest_memory(rs, ed, mem)
            out["pick"][f"{ed} {mem}"] = view.pick_for_memory(rs, mem, ed)
    return out


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_picks_match_python_synthetic(tmp_path):
    f = tmp_path / "phone.json"
    f.write_text(json.dumps({"offers": _picks_case()}))
    tax = tmp_path / "tax.json"
    tax.write_text("{}")
    assert _run_picks(f, tax, "EU,,card,eur") == json.loads(json.dumps(_py_picks(_picks_case(), {}, "EU,,card,eur")))


@live
@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_picks_match_python(site_build, phones, data):
    v1 = site_build / "data" / "v1"
    tax_file = next(v1.glob("tax.*.json"))
    tax = json.loads(tax_file.read_text())
    for pid in _samples(phones):
        f = next((v1 / "phone").glob(f"{pid}.*.json"))
        inputs = json.loads(f.read_text())["offers"]
        for st in SETTINGS:
            s = ",".join(st)
            assert _run_picks(f, tax_file, s) == json.loads(json.dumps(_py_picks(inputs, tax, s))), (pid, st)


def _ser(*pts, cur="eur"):
    return {"cur": cur, "pts": [list(p) for p in pts]}


_TODAY = "2026-10-08"


def _trend_case():
    inputs = [_o(money={"eur": 1000}, ship={"EU": {"eur": 20}}, store_label="a"),
              _o(money={"eur": 900}, ship={"EU": {"eur": 0}}, pay_ok={"paypal": False}, store_label="b"),
              _o(money={"eur": 500}, ship={"EU": False}, store_label="far"),
              _o(money={"eur": 800, "usd": 900, "usd_approx": True}, available=False, store_label="c")]
    trend = {"global": {"12/256": {"a": _ser(("2026-10-01", 1.1), ("2026-10-02", 1.0), ("2026-10-07", 0.9)),
                                    "b": _ser(("2026-10-01", 1.0), ("2026-10-02", 1.2)),
                                    "far": _ser(("2026-10-01", 0.5)), "c": _ser(("2026-10-02", 1.0), ("2026-10-04", None))}}}
    return inputs, trend


def test_daily_best_carries_change_points_forward_to_today():
    inputs, trend = _trend_case()
    tax = {"EU": {"rate_pct": 20}}
    out = view.daily_best(inputs, trend, "global", "12/256", tax, view.DEFAULT, _TODAY)
    # b alone on 10-01; c (out of stock from 10-04, carried until then) is cheapest on 10-02 and 10-03; then a at the
    # ratio it last had, one entry per day up to today
    assert [(d["day"], d["store"]) for d in out] == [("2026-10-01", "b"), ("2026-10-02", "c"), ("2026-10-03", "c")] + \
        [(f"2026-10-0{n}", "a") for n in range(4, 9)]
    one = lambda r, today: view.daily_best(inputs, {"global": {"12/256": {"a": _ser(("2026-10-05", r))}}}, "global", "12/256", tax, view.DEFAULT, today)
    assert [d["day"] for d in one(0.9, "2026-10-07")] == ["2026-10-05", "2026-10-06", "2026-10-07"]   # nothing before its first point
    assert one(0.9, "2026-10-04") == []                                                                  # nothing after today either
    scaled = [_o(money={"eur": 1100}, ship={"EU": {"eur": 20}}, store_label="a")]
    assert one(1.1, "2026-10-05")[0]["total"] == view.best_of(view.rows(scaled, tax, view.DEFAULT), "global", "12/256")["total"]   # list x1.1, shipping unchanged, tax recomputed
    assert all(d["store"] != "far" for d in out)                                                         # never delivers here
    pp = view.daily_best(inputs, trend, "global", "12/256", tax, pricing.Settings("EU", "", "paypal", "eur"), _TODAY)
    assert pp[0]["store"] == "a"                                                                         # b refuses paypal: excluded
    assert view.daily_best(inputs, trend, "global", "16/512", tax, view.DEFAULT, _TODAY) == []


def _usd_case(cur):
    inputs = [_o(money={"eur": 1000, "usd": 1100}, ship={"EU": {"eur": 0, "usd": 0}}, store_label="a")]
    return inputs, {"global": {"12/256": {"a": _ser(("2026-10-01", 0.9), cur=cur)}}}


def test_daily_best_marks_other_currencies_of_a_past_day_approximate():
    tax = {"EU": {"rate_pct": 0}}
    for cur, shown, approx in (("eur", "eur", False), ("eur", "usd", True), ("usd", "usd", False), ("usd", "eur", True)):
        inputs, trend = _usd_case(cur)
        out = view.daily_best(inputs, trend, "global", "12/256", tax, pricing.Settings("EU", "", "card", shown), "2026-10-01")
        assert out[0]["approx"] is approx, (cur, shown)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_daily_best_matches_python_synthetic(tmp_path):
    tax = tmp_path / "tax.json"
    tax.write_text(json.dumps({"EU": {"rate_pct": 20}}))
    cases = [(*_trend_case(), st) for st in ("EU,,card,eur", "EU,,paypal,eur")] + \
            [(*_usd_case(c), st) for c in ("eur", "usd") for st in ("EU,,card,eur", "EU,,card,usd")]
    for n, (inputs, trend, st) in enumerate(cases):
        f = tmp_path / f"phone{n}.json"
        f.write_text(json.dumps({"offers": inputs, "trend": trend}))
        r = subprocess.run(["node", "tests/js/view_cases.mjs", "--daily", "global,12/256", "--phone", str(f), "--tax", str(tax), "--settings", st,
                            "--today", _TODAY], check=False, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        want = view.daily_best(inputs, trend, "global", "12/256", {"EU": {"rate_pct": 20}}, pricing.Settings(*st.split(",")), _TODAY)
        assert json.loads(r.stdout) == json.loads(json.dumps(want)), (n, st)


def _days(*pairs, store="s", approx=False):
    return [{"day": d, "total": t, "store": store, "approx": approx} for d, t in pairs]


def _span(start_day, totals, **kw):
    """One point per day from 2026-10-<start_day>, one total each."""
    return _days(*[(f"2026-10-{start_day + i:02d}", t) for i, t in enumerate(totals)], **kw)


_NOW = {"total": 900.0, "approx": False, "store": "now"}
_TREND_CASES = {
    "new_low_full_window": (_span(1, [1000, 980, 960, 950, 940, 1000, 990, 980, 970, 960, 950, 940, 930, 920, 910, 905, 1000, 990,
                                      980, 970, 960, 950, 940, 930, 920, 950, 960, 970, 980, 990]), _NOW, "2026-10-31"),
    "new_low_12_days": (_span(20, [1000, 990, 980, 970, 960, 950, 940, 930, 920, 960, 950, 940]), _NOW, "2026-10-31"),
    "above_low_9_days_ago": (_span(1, [1000] * 21 + [900] + [950] * 9, store="old")[:21] + _days(("2026-10-22", 800)) + _span(23, [950] * 8, store="x"),
                             {"total": 840.0, "approx": True, "store": "now"}, "2026-10-31"),
    "gone_store_cheaper": (_span(20, [700, 1000, 990, 980, 970, 960, 950, 940]), _NOW, "2026-10-31"),
    "short_six_days": (_span(25, [1000, 990, 980, 970, 960]), _NOW, "2026-10-31"),
    "flat_after_higher": (_days(("2026-09-15", 1000)) + _span(2, [900] * 29), _NOW, "2026-10-31"),
    "back_after_35_days": (_days(("2026-09-20", 1000), ("2026-09-25", 1000)), _NOW, "2026-10-31"),
    "differs_by_7_cents": (_span(2, [1000.04, 999.97] * 14 + [1000.04]), {"total": 1000.0, "approx": False, "store": "now"}, "2026-10-31"),
    "week_old_too_far": (_span(1, [1000] * 10), _NOW, "2026-10-31"),
    "week_within_14": (_span(1, [1000] * 10) + _span(20, [950] * 4), _NOW, "2026-10-31"),
    "high_approx": (_days(("2026-10-02", 1100), approx=True) + _span(3, [1000] * 28), _NOW, "2026-10-31"),
    "flat": (_span(1, [900] * 30), {"total": 900.0, "approx": False, "store": "now"}, "2026-10-31"),
    "no_day_7_back": (_span(26, [1000, 990, 980, 970, 960, 950]), _NOW, "2026-10-31"),
    "today_replaced": (_span(20, [1000] * 12), _NOW, "2026-10-31"),
    "empty_list": ([], _NOW, "2026-10-31"),
    "gap_flat": (_days(("2026-08-12", 1000)) + _span(20, [900] * 11), _NOW, "2026-10-31"),
    "gap_lower": (_days(("2026-08-12", 1000)) + _span(20, [950, 940, 930, 920, 960, 940, 930, 950, 960, 970, 980]), _NOW, "2026-10-31"),
    "no_now": (_span(1, [1000] * 5), None, "2026-10-31"),
}


def test_price_trend_numbers():
    t = lambda k: view.price_trend(*_TREND_CASES[k])
    assert t("no_now") is None
    a = t("new_low_full_window")
    assert (a["full_window"], a["short"], a["is_low"], a["low"], a["low_day"], a["low_store"], a["now"]) == (True, False, True, 900, "2026-10-31", "now", 900)
    assert a["first_day"] == "2026-10-01" and a["window_start"] == "2026-10-02" and a["high"] == 1000
    assert a["since_first"] is False and a["change_pct"] == round((900 - 980) / 980 * 100, 1) and a["change_7d"] == -3.2   # 10-24 was 930
    b = t("new_low_12_days")
    assert (b["full_window"], b["is_low"], b["first_day"], b["since_first"], b["short"]) == (False, True, "2026-10-20", True, False)
    assert b["change_pct"] == -10.0
    c = t("above_low_9_days_ago")
    assert (c["is_low"], c["low"], c["low_day"], c["low_store"], c["approx"]) == (False, 800, "2026-10-22", "s", True)
    assert c["change_pct"] == -16.0
    d = t("gone_store_cheaper")
    assert (d["is_low"], d["low"], d["low_day"]) == (False, 700, "2026-10-20")
    assert t("short_six_days")["short"] is True and t("empty_list")["short"] is True
    assert t("empty_list")["first_day"] == "2026-10-31" and t("empty_list")["change_pct"] is None
    f = t("flat")
    assert (f["low"], f["high"], f["is_low"], f["change_pct"], f["change_7d"]) == (900, 900, True, 0.0, 0.0)
    assert t("no_day_7_back")["change_7d"] is None
    assert t("short_six_days")["recent_gap"] is False and t("empty_list")["recent_gap"] is False   # history starts inside the window
    g = t("flat_after_higher")                       # 30 flat days after a higher price before the window
    assert (g["short"], g["full_window"], g["first_day"], g["low"], g["high"]) == (False, True, "2026-09-15", 900, 900)
    h = t("back_after_35_days")                      # only today inside the window, history from before it
    assert (h["short"], h["recent_gap"], h["first_day"]) == (True, True, "2026-09-20")
    k = t("differs_by_7_cents")                      # compared as displayed: 1000.04 and 999.97 are both 1000
    assert (k["low"], k["high"], k["now"], k["is_low"], k["change_pct"]) == (1000, 1000, 1000, True, 0.0)
    assert t("week_old_too_far")["change_7d"] is None           # the newest point is 21 days back
    assert t("week_within_14")["change_7d"] == -5.3             # 950 on 10-23, the latest day at least 7 days back
    assert (t("high_approx")["high"], t("high_approx")["high_approx"], t("high_approx")["approx"]) == (1100, True, False)
    assert t("flat")["high_approx"] is False
    for k in ("gap_flat", "gap_lower"):              # one day in August, away, back from 20 Oct: 12 days in the window, not short
        x = t(k)
        assert (x["short"], x["full_window"], x["since_day"], x["first_day"], x["since_first"]) == (False, False, "2026-10-20", "2026-08-12", False)
    assert (t("gap_flat")["low"], t("gap_flat")["high"]) == (900, 900)
    assert (t("gap_lower")["is_low"], t("gap_lower")["change_pct"]) == (True, -5.3)
    assert (a["since_day"], t("new_low_12_days")["since_day"], g["since_day"]) == ("2026-10-02", "2026-10-20", "2026-10-02")
    r = view.price_trend(_TREND_CASES["today_replaced"][0] + _days(("2026-10-31", 5)), _NOW, "2026-10-31")
    assert r["low"] == 900 and r["low_day"] == "2026-10-31"          # now replaces the list's entry for today


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_price_trend_matches_python_synthetic(tmp_path):
    for name, (days, now, today) in _TREND_CASES.items():
        f = tmp_path / f"{name}.json"
        f.write_text(json.dumps({"days": days, "now": now, "today": today}))
        r = subprocess.run(["node", "tests/js/view_cases.mjs", "--trend", str(f)], check=False, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert json.loads(r.stdout) == json.loads(json.dumps(view.price_trend(days, now, today))), name
