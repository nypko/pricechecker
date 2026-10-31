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
