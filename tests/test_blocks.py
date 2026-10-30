"""The D blocks: each exists once as a Jinja macro (templates/_d/blocks.html) and once as a JS function
(static/js/blocks.js). These tests keep their text equal and check the price states of spec §4.2."""
import html
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from pricechecker import fx, run, terms
from pricechecker.pricing import Settings
from pricechecker.site import _env, blocks, context, offers, view
from pricechecker.site.common import ed_labels

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "states_phone.json"
HARNESS = ROOT / "tests" / "js" / "render_blocks.mjs"
UK_PAYPAL = Settings("UK", "", "paypal", "gbp")
NAMES = ["price_box", "gap_line", "mem_chips", "verdict", "receipt", "store_row", "store_list", "buy_bar", "home_row", "ledger"]
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def text(h: str) -> str:
    """What a reader sees: tags stripped, entities unescaped, whitespace collapsed."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def root_of(h: str) -> str:
    """The root element's tag, class and data-block, e.g. 'div|side cn on|price_box'."""
    m = re.match(r'\s*<(\w+)([^>]*)>', h)
    if not m:
        return ""
    cls = re.search(r'class="([^"]*)"', m[2])
    blk = re.search(r'data-block="([^"]*)"', m[2])
    return f"{m[1]}|{cls[1] if cls else ''}|{blk[1] if blk else ''}"


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.seq: list = []

    def handle_starttag(self, tag, attrs):
        self.seq.append((tag, tuple(sorted(attrs))))

    def handle_endtag(self, tag):
        self.seq.append(("/" + tag, ()))


def structure(h: str) -> list:
    """Every element in order: (tag, sorted (attribute, unescaped value) pairs), and the end tags."""
    t = _Tags()
    t.feed(h)
    t.close()
    return t.seq


_ENV = None


def macro(name: str, *args):
    global _ENV
    _ENV = _ENV or _env()
    tpl = _ENV.from_string('{% from "_d/blocks.html" import ' + name + ' %}{{ ' + name + '(*a) }}')
    return tpl.render(a=args)


def render_py(rows, s, labels, edition, storage, meta, now, root="../", marks=()):
    """The same set of blocks render_blocks.mjs prints, from the Jinja macros."""
    pick = [r for r in rows if r["edition"] == edition and r["storage"] == storage]
    best = view.best_of(rows, edition, storage)
    both = all(view.best_of(rows, e) for e in ("china", "global"))
    return {
        "price_box": macro("price_box", rows, edition, s, labels, True),
        "gap_line": macro("gap_line", view.gap(rows), both, s, labels),
        "mem_chips": macro("mem_chips", rows, edition, storage, s),
        "verdict": macro("verdict", best, pick, s, labels, now),
        "receipt": macro("receipt", best, s, labels),
        "store_row": [macro("store_row", r, s, labels, now) for r in rows],
        "store_list": macro("store_list", [r for r in pick if r is not best], s, labels, now),
        "buy_bar": macro("buy_bar", best, s, labels),
        "home_row": macro("home_row", meta, rows, s, labels, root, list(marks)),
        "ledger": [macro("ledger", rows, s, labels, k) for k in ("rank", "total", "list")],
    }


def render_js(phone_file, tax_file, s, labels, edition, storage, meta, now, root="../", marks=()):
    r = subprocess.run(["node", str(HARNESS), "--phone", str(phone_file), "--tax", str(tax_file), "--edition", edition,
                        "--storage", storage, "--settings", ",".join(s), "--labels", json.dumps(labels),
                        "--meta", json.dumps(meta), "--now", now, "--root", root, "--marks", json.dumps(list(marks))],
                       check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def assert_same(py: dict, js: dict, where: str):
    assert set(js) == set(NAMES), where
    for name in NAMES:
        a, b = py[name], js[name]
        if name in ("store_row", "ledger"):
            assert len(a) == len(b), where
            pairs = list(zip(a, b))
        else:
            pairs = [(a, b)]
        for x, y in pairs:
            assert text(x) == text(y), f"{where} {name}"
            assert root_of(x) == root_of(y), f"{where} {name}"
            assert structure(x) == structure(y), f"{where} {name}"
            if x.strip():
                assert f'data-block="{name}"' in x, f"{where} {name}"


@pytest.fixture(scope="module")
def fixture_doc():
    return json.loads(FIXTURE.read_text())


@pytest.fixture(scope="module")
def tax_file(site_build):
    return next((site_build / "data" / "v1").glob("tax.*.json"))


@pytest.fixture(scope="module")
def tax(tax_file):
    return json.loads(tax_file.read_text())


@pytest.fixture(scope="module")
def phones():
    stores, catalog = run.load_config()
    return offers.assemble(context.load(catalog, stores, fx.cached(), terms.saved_status()))


def _fixture_cases(doc, tmp_path):
    """(phone file, offers, settings, edition, storage): the full fixture under both settings, the China-only variant."""
    full = tmp_path / "states.json"
    full.write_text(json.dumps(doc))
    china = tmp_path / "states-china.json"
    china_offers = [o for o in doc["offers"] if o["edition"] == "china"]
    china.write_text(json.dumps({**doc, "offers": china_offers}))
    return [(full, doc["offers"], view.DEFAULT, "china", "12/256"), (full, doc["offers"], UK_PAYPAL, "global", "12/256"),
            (full, doc["offers"], view.DEFAULT, "global", "12/512"), (china, china_offers, view.DEFAULT, "china", "12/256")]


@needs_node
def test_blocks_parity_fixture(fixture_doc, tax_file, tax, tmp_path):
    labels = ed_labels(fixture_doc["meta"]["brand"])
    for f, inputs, s, e, st in _fixture_cases(fixture_doc, tmp_path):
        rows = view.rows(inputs, tax, s)
        py = render_py(rows, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])
        js = render_js(f, tax_file, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])
        assert_same(py, js, f"{f.name} {tuple(s)} {e} {st}")


def test_home_row_marks_parity(fixture_doc, tax_file, tax, tmp_path):
    """home_row with marks (a drop and a watch pill, one text needing escapes) is the same in Jinja and JS, and the
    marks sit inside the li after the link; without marks no marks element is written."""
    labels = ed_labels(fixture_doc["meta"]["brand"])
    marks = [{"kind": "drop", "text": "↓ this week"}, {"kind": "watch", "text": "Watched <&>"}]
    f, inputs, s, e, st = next(iter(_fixture_cases(fixture_doc, tmp_path)))
    rows = view.rows(inputs, tax, s)
    for m in (marks, []):
        py = render_py(rows, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"], marks=m)
        js = render_js(f, tax_file, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"], marks=m)
        assert_same(py, js, f"marks {len(m)}")
        h = py["home_row"]
        if m:
            assert h.endswith('</a><span class="marks"><span class="mark drop">↓ this week</span>'
                              '<span class="mark watch">Watched &lt;&amp;&gt;</span></span></li>')
        else:
            assert "marks" not in h


def _real_samples(phones):
    """One phone each: both versions, China only, Global only, with a sale, with a stale store."""
    def first(pred, taken):
        return next((p for p in phones if p["id"] not in taken and pred(p)), None)
    eds = lambda p: {o["edition"] for o in p["offers"] if o["available"]}
    out: list = []
    for pred in (lambda p: eds(p) == {"china", "global"}, lambda p: eds(p) == {"china"}, lambda p: eds(p) == {"global"},
                 lambda p: any(o.get("promo") for o in p["offers"]), lambda p: any(o.get("old") for o in p["offers"])):
        p = first(pred, {q["id"] for q in out})
        if p is None:
            print("no real phone for one of the sample kinds: skipped")
        else:
            out.append(p)
    return out


@needs_node
def test_blocks_parity_real_phones(site_build, phones, tax_file, tax):
    v1 = site_build / "data" / "v1"
    samples = _real_samples(phones)
    assert len(samples) >= 3
    now = "2026-10-30T12:00:00Z"
    for p in samples:
        f = next((v1 / "phone").glob(f"{p['id']}.*.json"))
        inputs = json.loads(f.read_text())["offers"]
        meta = {"id": p["id"], "name": p["name"], "announced": p["announced"], "brand": p["brand"]}
        labels = ed_labels(p["brand"])
        rows = view.rows(inputs, tax, view.DEFAULT)
        picks = {(r["edition"], r["storage"]) for r in rows if r["storage"] != "base"} or {("china", "12/256")}
        for e, st in sorted(picks)[:4]:
            py = render_py(rows, view.DEFAULT, labels, e, st, meta, now)
            js = render_js(f, tax_file, view.DEFAULT, labels, e, st, meta, now)
            assert_same(py, js, f"{p['id']} {e} {st}")


def test_money_python_matches_js_rule():
    m = blocks.money
    assert m(1049.5, "eur") == "€1,050" and m(1048.5, "eur") == "€1,049"   # half up, not Python's half-even
    assert m(0.125, "gbp", True) == "£0.13" and m(1234567.891, "usd", True) == "$1,234,567.89"
    assert m(-12.5, "cad", True) == "−C$12.50" and m(999.996, "aud") == "A$1,000" and m(None, "eur") == "–"


@needs_node
def test_money_parity():
    vals = [0, 0.005, 0.125, 0.5, 1.5, 2.5, 12.345, 999.5, 1049.5, 1048.5, 1234.565, 1234567.891, -0.4, -12.5, 18.4999, 2.675]
    cases = [[v, c, d] for v in vals for c in ("eur", "gbp", "usd", "cad", "aud") for d in (False, True)]
    r = subprocess.run(["node", str(HARNESS), "--money", json.dumps(cases)], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout) == [blocks.money(v, c, d) for v, c, d in cases]


# --- the states of spec §4.2, on the fixture ---

@pytest.fixture(scope="module")
def states(fixture_doc, tax):
    rows = view.rows(fixture_doc["offers"], tax, view.DEFAULT)
    return fixture_doc, rows, {r["store"]: r for r in rows}


def test_state_markers(states, tax):
    doc, rows, by = states
    labels, now = ed_labels(doc["meta"]["brand"]), doc["now"]
    pick = [r for r in rows if r["edition"] == "china" and r["storage"] == "12/256"]
    best = view.best_of(rows, "china", "12/256")

    # stale: "price from N days ago", last among the priced rows (view.rows order, kept by store_list), never the
    # verdict, receipt or buy bar
    stale = macro("store_row", by["Old Store"], view.DEFAULT, labels, now)
    assert "stale" in root_of(stale) and "price from 5 days ago" in text(stale)
    lst = macro("store_list", pick, view.DEFAULT, labels, now)
    main, _, sold = lst.partition("Sold out at")
    priced = [li for li in re.findall(r"<li[^>]*>.*?</li>", main, re.DOTALL) if 'class="t' in li]
    assert "Old Store" in priced[-1]
    v = macro("verdict", best, pick, view.DEFAULT, labels, now)
    assert "Old Store" not in text(v) and "€700" not in text(v)
    assert "Old Store" not in text(macro("verdict", by["Old Store"], pick, view.DEFAULT, labels, now))
    assert "Old Store" not in text(macro("price_box", rows, "china", view.DEFAULT, labels, True))
    for st in ("Old Store", "Gone Shop", "No Ship Co"):
        r = by[st] if st != "No Ship Co" else {**by[st], "state": "nopay"}
        assert macro("buy_bar", r, view.DEFAULT, labels) == ""
        assert text(macro("receipt", r, view.DEFAULT, labels)) == ""

    # sold out: under "Sold out at", last price, no store button
    assert "Gone Shop" in sold and "Gone Shop" not in main
    gone = macro("store_row", by["Gone Shop"], view.DEFAULT, labels, now)
    assert "soldout" in root_of(gone) and "<a" not in gone and "€1,100" in text(gone)

    # not delivered / payment not accepted (UK, PayPal)
    uk = {r["store"]: r for r in view.rows(doc["offers"], tax, UK_PAYPAL)}
    nod = macro("store_row", uk["EU Only"], UK_PAYPAL, labels, now)
    assert "nodelivery" in root_of(nod) and "Doesn't deliver to the UK" in text(nod) and "£" not in text(nod)
    nop = macro("store_row", uk["Card Only"], UK_PAYPAL, labels, now)
    assert "nopay" in root_of(nop) and "Doesn't take PayPal" in text(nop)

    # sale: its own receipt line and a tag on the row
    assert best["store"] == "Sale <Store>"
    rc = macro("receipt", best, view.DEFAULT, labels)
    assert "Summer sale, 2% off at checkout" in text(rc) and "You pay at the door" in text(rc)
    assert "2% sale" in text(macro("store_row", best, view.DEFAULT, labels, now))
    assert "Sale &lt;Store&gt;" in v and "<Store>" not in v   # escaped

    # settled / unsettled
    assert "✓ delivered, tax settled" in text(macro("price_box", rows, "china", view.DEFAULT, labels, True))
    unset = macro("store_row", by["No Ship Co"], view.DEFAULT, labels, now)
    assert "+ shipping" in text(unset)
    assert "≈" in text(macro("store_row", by["Ship From"], view.DEFAULT, labels, now))

    # verdict and buy bar copy, links
    assert "View at Sale <Store>" in text(v) and "Affiliate link: we may earn a commission; it never changes the order." in text(v)
    bb = macro("buy_bar", best, view.DEFAULT, labels)
    assert "View deal" in text(bb) and 'rel="sponsored nofollow noopener"' in bb and 'target="_blank"' in bb
    assert "&amp;b=2" in bb


def test_base_storage_and_home_row(states):
    doc, rows, _ = states
    labels = ed_labels(doc["meta"]["brand"])
    base_only = [r for r in rows if r["store"] == "Mystery Mem"]
    assert "RAM/storage not listed" in text(macro("price_box", base_only, "global", view.DEFAULT, labels, True))
    chips = macro("mem_chips", rows, "global", "12/256", view.DEFAULT)
    assert "base" not in chips and "12 GB · 256 GB" in text(chips)
    h = macro("home_row", doc["meta"], rows, view.DEFAULT, labels, "../")
    assert root_of(h).startswith("li|pair|home_row") and 'href="../phones/state-phone"' in h
    t = text(h)
    assert "Oct 2026" in t and "State Phone <X>" in t and f"{labels['china']} €170 less at 12 + 256" in t
    china_only = macro("home_row", doc["meta"], [r for r in rows if r["edition"] == "china"], view.DEFAULT, labels, "")
    assert "–" in text(china_only) and "less at" not in text(china_only)


@needs_node
def test_js_buy_bar_and_receipt_refuse_rows_not_ok(states):
    *_, by = states
    picked = [by["Old Store"], by["Gone Shop"], {**by["No Ship Co"], "state": "nopay"}, {**by["Card Only"], "state": "nodelivery"}]
    src = (ROOT / "static" / "js" / "blocks.js").as_uri()
    js = (f'import {{ buyBar, receipt }} from "{src}";\n'
          f'const rows = {json.dumps(picked)}, s = {{region: "EU", area: "", pay: "card", cur: "eur"}}, l = {{global: "Global", china: "China"}};\n'
          'console.log(JSON.stringify(rows.map((r) => [buyBar(r, s, l), receipt(r, s, l)])));')
    r = subprocess.run(["node", "--input-type=module", "-e", js], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    for bb, rc in json.loads(r.stdout):
        assert bb == "" and text(rc) == ""
