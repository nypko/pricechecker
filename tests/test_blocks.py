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

# reads the saved prices or the real build: excluded from the hourly production run (pytest -m "not live")
live = pytest.mark.live

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "states_phone.json"
HARNESS = ROOT / "tests" / "js" / "render_blocks.mjs"
UK_PAYPAL = Settings("UK", "", "paypal", "gbp")
NAMES = ["price_box", "price_box_plain", "mem_chips", "verdict", "receipt", "store_row", "store_list", "buy_bar", "home_row", "ledger"]
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
    return {
        "price_box": macro("price_box", rows, edition, storage, s, labels, True),
        "price_box_plain": macro("price_box", rows, edition, storage, s, labels, False, False),
        "mem_chips": macro("mem_chips", rows, storage, s),
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
                assert f'data-block="{name.removesuffix("_plain")}"' in x, f"{where} {name}"


@pytest.fixture(scope="module")
def fixture_doc():
    return json.loads(FIXTURE.read_text())


@pytest.fixture(scope="module")
def tax_file(tmp_path_factory):
    """The tax config the browser loads (data_files writes data.tax_cfg as is), without building the whole site: these
    tests are about the blocks, not the pages."""
    stores, catalog = run.load_config()
    f = tmp_path_factory.mktemp("tax") / "tax.json"
    f.write_text(json.dumps(context.load(catalog, stores, fx.cached(), terms.saved_status()).tax_cfg))
    return f


@pytest.fixture(scope="module")
def tax(tax_file):
    return json.loads(tax_file.read_text())


@pytest.fixture(scope="module")
def phones():
    stores, catalog = run.load_config()
    return offers.assemble(context.load(catalog, stores, fx.cached(), terms.saved_status()))


def _oppo_docs(doc):
    """An Oppo-like phone: China sold with 12/256, 16/512, 16/1024; Global only with 12/256 and 16/512 (so Global has no
    16/1024). The second variant adds sold-out Global 16/1024 and a sold-out-only 24/2048 on both versions."""
    tpl = {o["store_label"]: o for o in doc["offers"]}
    def o(base, edition, storage, eur, **kw):
        x = {**tpl[base], "edition": edition, "storage": storage, "money": {**tpl[base]["money"], "eur": eur}, **kw}
        return x
    offers = [o("Settled Shop", "china", "12/256", 1000), o("Settled Shop", "china", "16/512", 1400), o("Settled Shop", "china", "16/1024", 1700),
              o("EU Only", "global", "12/256", 1200), o("EU Only", "global", "16/512", 1500)]
    sold = offers + [o("EU Only", "global", "16/1024", 1900, available=False), o("EU Only", "global", "24/2048", 2500, available=False),
                     o("Settled Shop", "china", "24/2048", 2400, available=False)]
    return {**doc, "offers": offers}, {**doc, "offers": sold}


def _gone_docs(doc):
    """Phones whose Global version has no current price anywhere, its rows at another memory only: {name: (offers,
    settings)}. China sells 12/256 and 16/1024 in all of them."""
    tpl = {o["store_label"]: o for o in doc["offers"]}
    cn = [{**tpl["Settled Shop"], "edition": "china", "storage": st} for st in ("12/256", "16/1024")]
    def gl(base, **kw):
        return cn + [{**tpl[base], "edition": "global", "storage": "12/256", **kw}]
    return {"gone-sold": (gl("EU Only", available=False), view.DEFAULT), "gone-nopay": (gl("Card Only"), UK_PAYPAL),
            "gone-stale": (gl("Old Store"), view.DEFAULT)}


def _fixture_cases(doc, tmp_path):
    """(phone file, offers, settings, edition, storage): the full fixture under both settings, the China-only variant,
    the variant whose China listings are all sold out, the Oppo-like phones (a memory only China has; sold-out Global)."""
    full = tmp_path / "states.json"
    full.write_text(json.dumps(doc))
    china = tmp_path / "states-china.json"
    china_offers = [o for o in doc["offers"] if o["edition"] == "china"]
    china.write_text(json.dumps({**doc, "offers": china_offers}))
    sold = tmp_path / "states-soldout.json"   # the China version sold out everywhere, Global still selling
    sold_offers = [{**o, "available": False} if o["edition"] == "china" else o for o in doc["offers"]]
    sold.write_text(json.dumps({**doc, "offers": sold_offers}))
    oppo, oppo_sold = _oppo_docs(doc)
    for name, d in (("oppo", oppo), ("oppo-sold", oppo_sold)):
        (tmp_path / f"{name}.json").write_text(json.dumps(d))
    base = {**doc, "offers": [{**o, "storage": "base"} for o in oppo["offers"] if o["storage"] == "12/256"]}
    (tmp_path / "oppo-base.json").write_text(json.dumps(base))
    gone = []
    for name, (offs, st) in _gone_docs(doc).items():
        (tmp_path / f"{name}.json").write_text(json.dumps({**doc, "offers": offs}))
        gone.append((tmp_path / f"{name}.json", offs, st, "global", "16/1024"))
    return [(full, doc["offers"], view.DEFAULT, "china", "12/256"), (full, doc["offers"], UK_PAYPAL, "global", "12/256"),
            (full, doc["offers"], view.DEFAULT, "global", "12/512"), (china, china_offers, view.DEFAULT, "china", "12/256"),
            (sold, sold_offers, view.DEFAULT, "china", "12/256"),
            (tmp_path / "oppo.json", oppo["offers"], view.DEFAULT, "china", "12/256"),
            (tmp_path / "oppo.json", oppo["offers"], UK_PAYPAL, "global", "16/1024"),
            (tmp_path / "oppo.json", oppo["offers"], view.DEFAULT, "china", "16/1024"),
            (tmp_path / "oppo-sold.json", oppo_sold["offers"], view.DEFAULT, "global", "16/1024"),
            (tmp_path / "oppo-base.json", base["offers"], view.DEFAULT, "china", "base")] + gone


@needs_node
def test_blocks_parity_fixture(fixture_doc, tax_file, tax, tmp_path):
    labels = ed_labels(fixture_doc["meta"]["brand"])
    for f, inputs, s, e, st in _fixture_cases(fixture_doc, tmp_path):
        rows = view.rows(inputs, tax, s)
        py = render_py(rows, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])
        js = render_js(f, tax_file, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])
        assert_same(py, js, f"{f.name} {tuple(s)} {e} {st}")


@needs_node
def test_price_box_of_a_version_sold_out_everywhere(fixture_doc, tax_file, tax, tmp_path):
    """All of a version's listings sold out: its box says so (Jinja and JS alike), not "No current price for your
    settings" (no setting would help); a version with no price for the settings keeps that line."""
    labels = ed_labels(fixture_doc["meta"]["brand"])
    f, inputs, s, e, st = _fixture_cases(fixture_doc, tmp_path)[4]
    rows = view.rows(inputs, tax, s)
    for box in (render_py(rows, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])["price_box"],
                render_js(f, tax_file, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])["price_box"]):
        assert "Sold out at every store we check" in text(box) and "No current price" not in text(box)
    # China listings that don't deliver to the UK (one of them sold out): a setting would help, so the usual line
    nod = [{**o, "ship": {**o["ship"], "UK": False}} if o["edition"] == "china" else o for o in fixture_doc["offers"]]
    box = macro("price_box", view.rows(nod, tax, UK_PAYPAL), "china", "12/256", UK_PAYPAL, labels, True)
    assert "No current price for your settings" in text(box) and "Sold out" not in text(box)


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


@live
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
    assert "Old Store" not in text(macro("price_box", rows, "china", "12/256", view.DEFAULT, labels, True))
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
    assert "✓ delivered, tax settled" in text(macro("price_box", rows, "china", "12/256", view.DEFAULT, labels, True))
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
    assert "RAM/storage not listed" in text(macro("price_box", base_only, "global", "base", view.DEFAULT, labels, True))
    chips = macro("mem_chips", rows, "12/256", view.DEFAULT)
    assert "base" not in chips and text(chips) == "12 GB + 256 GB 12 GB + 512 GB"
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


def test_price_box_without_the_version_switch(fixture_doc, tax):
    """switch=False: no buttons and no means-link, the store link stays; the default box keeps all of them."""
    rows = view.rows(fixture_doc["offers"], tax, view.DEFAULT)
    labels = {"global": "Global", "china": "China"}
    for e in ("china", "global"):
        plain = macro("price_box", rows, e, "12/256", view.DEFAULT, labels, False, False)
        full = macro("price_box", rows, e, "12/256", view.DEFAULT, labels, True)
        assert "<button" not in plain and "means-link" not in plain and "aria-pressed" not in plain and " on" not in root_of(plain)
        assert "role=" not in plain and "aria-pressed" not in plain and "id=" not in plain
        assert 'rel="sponsored nofollow noopener"' in plain and "View at" in plain and "delivered" in plain
        assert "<button" in full
    assert "means-link" in macro("price_box", rows, "china", "12/256", view.DEFAULT, labels, True)


@needs_node
def test_js_store_links_are_sponsored_and_open_in_a_new_tab(fixture_doc, tax_file):
    """Every store <a> the JS blocks build (View at ..., the bottom bar's View deal) carries the same rel and target as the
    templates' - for every version and memory of the sample phone, each in two currencies."""
    labels = {"global": "Global", "china": "China"}
    meta = {"id": "state-phone", "name": "State Phone", "announced": "2026-10", "brand": "State"}
    seen = set()
    for edition, storage in sorted({(o["edition"], o["storage"]) for o in fixture_doc["offers"]}):
        for cur in ("eur", "usd"):
            out = render_js(FIXTURE, tax_file, ("EU", "", "card", cur), labels, edition, storage, meta, "2026-10-20T12:00:00Z")
            htmls = [out[k] for k in NAMES if isinstance(out[k], str)] + [h for k in ("store_row", "ledger") for h in out[k]]
            for h in htmls:
                for m in re.finditer(r"<a\b([^>]*)>", h):
                    href = re.search(r'href="([^"]*)"', m[1])
                    if href and href[1].startswith("http"):
                        rel = re.search(r'rel="([^"]*)"', m[1])
                        assert rel and {"sponsored", "nofollow", "noopener"} <= set(rel[1].split()), m[0]
                        assert 'target="_blank"' in m[1], m[0]
                        seen.add(re.search(r'class="([^"]*)"', m[1])[1])
    assert {"go", "bb-go"} <= seen, seen


@needs_node
def test_store_button_only_for_an_https_link(fixture_doc, tax_file, tax, tmp_path):
    """An offer whose link is not https (offers.py drops those; this is the second line of defence) gets no store
    button and no buy bar, in Jinja and JS alike."""
    labels = ed_labels(fixture_doc["meta"]["brand"])
    for bad in ("javascript:alert(1)", "http://shop.example/p", None):
        offers_ = [{**o, "link": bad} for o in fixture_doc["offers"]]
        f = tmp_path / "bad-link.json"
        f.write_text(json.dumps({**fixture_doc, "offers": offers_}))
        rows = view.rows(offers_, tax, view.DEFAULT)
        py = render_py(rows, view.DEFAULT, labels, "china", "12/256", fixture_doc["meta"], fixture_doc["now"])
        js = render_js(f, tax_file, view.DEFAULT, labels, "china", "12/256", fixture_doc["meta"], fixture_doc["now"])
        assert_same(py, js, f"link {bad}")
        everything = "".join(x if isinstance(x, str) else "".join(x) for x in py.values())
        assert "javascript:" not in everything and 'class="go"' not in everything and py["buy_bar"] == ""


# --- memory-first blocks: chips, memory-priced boxes, details panel ---

@pytest.fixture(scope="module")
def oppo(fixture_doc, tax):
    doc, doc_sold = _oppo_docs(fixture_doc)
    return view.rows(doc["offers"], tax, view.DEFAULT), view.rows(doc_sold["offers"], tax, view.DEFAULT)


def test_gap_line_is_gone():
    assert not hasattr(blocks, "gap_line") and "gap_line" not in (ROOT / "templates" / "_d" / "blocks.html").read_text()
    assert "gapLine" not in (ROOT / "static" / "js" / "blocks.js").read_text()


def test_chips_are_the_union_of_both_versions_sizes_only(oppo):
    rows, rows_sold = oppo
    chips = macro("mem_chips", rows, "12/256", view.DEFAULT)
    assert text(chips) == "12 GB + 256 GB 16 GB + 512 GB 16 GB + 1 TB" and "€" not in chips   # 16/1024 is China-only
    assert re.findall(r'data-m="([^"]+)" aria-pressed="(\w+)"', chips) == [("12/256", "true"), ("16/512", "false"), ("16/1024", "false")]
    assert "disabled" not in chips
    # a memory with rows but no current price in either version: disabled; Global's sold-out 16/1024 doesn't disable it
    sold_chips = macro("mem_chips", rows_sold, "16/512", view.DEFAULT)
    assert re.findall(r'data-m="([^"]+)" aria-pressed="\w+"( disabled)?>', sold_chips) == [("12/256", ""), ("16/512", ""), ("16/1024", ""), ("24/2048", " disabled")]


def test_chips_empty_for_a_base_only_phone_and_the_box_shows_the_base_row(fixture_doc, tax):
    labels = ed_labels("Xiaomi")
    base_only = [o for o in fixture_doc["offers"] if o["storage"] == "base"]
    rows = view.rows(base_only, tax, view.DEFAULT)
    assert macro("mem_chips", rows, "base", view.DEFAULT).strip() == ""
    box = macro("price_box", rows, "global", "base", view.DEFAULT, labels, True)
    assert "RAM/storage not listed" in text(box) and "€1,180" in text(box) and "Not sold" not in text(box)


@needs_node
def test_price_box_for_a_base_pick_shows_the_other_versions_own_best_offer(fixture_doc, tax_file, tax, tmp_path):
    """The pick is "base" (an offer with no listed memory): the other version isn't "not sold" with it. Its box shows its
    own best current offer at any memory, with no nearest button and no "less" line (Jinja and JS alike)."""
    labels = {"global": "Global", "china": "China"}
    doc, _ = _oppo_docs(fixture_doc)
    base = {**next(o for o in doc["offers"] if o["edition"] == "china"), "storage": "base"}
    doc = {**doc, "offers": doc["offers"] + [base]}
    f = tmp_path / "base-pick.json"
    f.write_text(json.dumps(doc))
    rows = view.rows(doc["offers"], tax, view.DEFAULT)
    for e in ("china", "global"):
        py = render_py(rows, view.DEFAULT, labels, e, "base", doc["meta"], doc["now"])
        js = render_js(f, tax_file, view.DEFAULT, labels, e, "base", doc["meta"], doc["now"])
        assert_same(py, js, f"base pick {e}")
        box = py["price_box"]
        assert "Not sold" not in text(box) and "not listed" not in text(box).replace("RAM/storage not listed", "") and "near" not in box and "less" not in box
    gl = macro("price_box", rows, "global", "base", view.DEFAULT, labels, True)
    assert "12 GB" in text(gl) and "€1,200" in text(gl) and "big num" in gl     # its cheapest offer, whichever memory
    assert "RAM/storage not listed" in text(macro("price_box", rows, "china", "base", view.DEFAULT, labels, True))


@needs_node
def test_approximate_prices_keep_their_mark_on_the_nearest_button_and_the_less_line(oppo, fixture_doc, tax_file, tmp_path):
    """The nearest button's price and the "less" amount carry the "≈" the box's own price has when the row is approximate
    (Jinja and JS alike)."""
    rows, _ = oppo
    labels = {"global": "Global", "china": "China"}
    approx = [{**r, "approx": True} if r["edition"] == "global" and r["storage"] == "16/512" else r for r in rows]
    box = macro("price_box", approx, "global", "16/1024", view.DEFAULT, labels, True)
    assert "· ≈€1,500" in text(box) and ">Nearest: 16 GB + 512 GB · ≈€1,500<span" in box
    assert "· €1,500" in text(macro("price_box", rows, "global", "16/1024", view.DEFAULT, labels, True))
    # the "less" line: approximate when either side is
    for edition in ("china", "global"):
        mark = [{**r, "approx": True} if r["edition"] == edition and r["storage"] == "12/256" else r for r in rows]
        assert '<p class="less">≈€200 less</p>' in macro("price_box", mark, "china", "12/256", view.DEFAULT, labels, True)
    assert '<p class="less">€200 less</p>' in macro("price_box", rows, "china", "12/256", view.DEFAULT, labels, True)
    # JS: the same markup
    src = (ROOT / "static" / "js" / "blocks.js").as_uri()
    js = (f'import {{ priceBox }} from "{src}";\n'
          f'const rows = {json.dumps(approx)}, mark = {json.dumps(mark)}, s = {json.dumps(dict(view.DEFAULT._asdict()))}, l = {json.dumps(labels)};\n'
          'console.log(JSON.stringify([priceBox(rows, "global", "16/1024", s, l, true, true), priceBox(mark, "china", "12/256", s, l, true, true)]));')
    r = subprocess.run(["node", "--input-type=module", "-e", js], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    near_js, less_js = json.loads(r.stdout)
    assert text(near_js) == text(box) and "≈€1,500" in near_js
    assert text(less_js) == text(macro("price_box", mark, "china", "12/256", view.DEFAULT, labels, True)) and "≈€200 less" in text(less_js)


def test_price_box_not_sold_with_the_memory_offers_the_nearest(oppo):
    rows, rows_sold = oppo
    labels = {"global": "Global", "china": "China"}
    box = macro("price_box", rows, "global", "16/1024", view.DEFAULT, labels, False)
    assert text(box) == "Global version Not sold with 16 GB + 1 TB Nearest: 16 GB + 512 GB · €1,500 →"
    assert "big" not in box and '€1,500<span aria-hidden="true">&nbsp;→</span></button>' in box   # no lone placeholder; the arrow stays with the price, unread
    assert '<button type="button" class="near" data-m="16/512">' in box and "less" not in box and "€" in text(box)
    # the select button is the toggle; the root and the nearest button are not, and the nearest button is not inside it
    assert '<button type="button" class="pickbtn" data-e="global" aria-pressed="false" aria-controls="pick-panel" id="tab-global">' in box
    assert not re.match(r"<div[^>]*role=", box) and "role=" not in box and box.count("aria-pressed") == 1 and re.search(r"</button><button[^>]*class=\"near\"", box)
    # China does have it: priced, no "not sold" text
    ch = macro("price_box", rows, "china", "16/1024", view.DEFAULT, labels, True)
    assert "€1,700" in text(ch) and "Not sold" not in text(ch) and "near" not in ch
    # the plain box (compare page) states it and keeps the nearest button, but has no tab
    plain = macro("price_box", rows, "global", "16/1024", view.DEFAULT, labels, False, False)
    assert "Not sold with 16 GB + 1 TB" in text(plain) and plain.count("<button") == 1 and 'class="near" data-m="16/512"' in plain
    assert "role=" not in plain and "pickbtn" not in plain
    # sold out at that memory: the existing text, no nearest button (Global's 16/1024 is sold out in the second phone)
    so = macro("price_box", rows_sold, "global", "16/1024", view.DEFAULT, labels, True)
    assert "Sold out at every store we check" in text(so) and "Not sold" not in text(so) and "near" not in so
    # a version with nothing current anywhere keeps its whole-version state text, not "Not sold with ..."
    none_ok = [{**r, "state": "soldout"} for r in rows if r["edition"] == "global"]
    b = macro("price_box", none_ok, "global", "16/1024", view.DEFAULT, labels, True)
    assert text(b) == "Global version – Sold out at every store we check" and "near" not in b


@needs_node
def test_version_with_no_current_price_anywhere_keeps_its_state_text(fixture_doc, tax_file, tax, tmp_path):
    """Global's only rows are sold out / not payable / stale, at another memory: at the picked memory its box says what
    it said before (Jinja and JS alike), with no "Not sold with" and no nearest button (nothing to offer)."""
    labels = {"global": "Global", "china": "China"}
    want = {"gone-sold": "Sold out at every store we check", "gone-nopay": "No current price for your settings",
            "gone-stale": "No current price for your settings"}
    for name, (offs, s) in _gone_docs(fixture_doc).items():
        f = tmp_path / f"{name}.json"
        f.write_text(json.dumps({**fixture_doc, "offers": offs}))
        rows = view.rows(offs, tax, s)
        assert {r["state"] for r in rows if r["edition"] == "global"} <= {"soldout", "nopay", "stale"}, name
        js = render_js(f, tax_file, s, labels, "global", "16/1024", fixture_doc["meta"], fixture_doc["now"])["price_box"]
        for box in (macro("price_box", rows, "global", "16/1024", s, labels, True), js):
            assert text(box) == f"Global version – {want[name]}", name
            assert "near" not in box and 'aria-pressed="true"' in box
        # the same version at the memory its rows are at: unchanged
        assert want[name] in text(macro("price_box", rows, "global", "12/256", s, labels, True))


def test_cheaper_settled_box_says_how_much_less(oppo, fixture_doc, tax):
    rows, _ = oppo
    labels = {"global": "Global", "china": "China"}
    cn = macro("price_box", rows, "china", "12/256", view.DEFAULT, labels, True)
    gl = macro("price_box", rows, "global", "12/256", view.DEFAULT, labels, True)
    assert '<p class="less">€200 less</p>' in cn and "less" not in gl
    assert "less" not in macro("price_box", rows, "china", "16/1024", view.DEFAULT, labels, True)   # Global doesn't sell it
    # the cheaper side not settled (its store lists no shipping to the EU): no number
    unsettled = [{**r, "settled": False} if r["edition"] == "china" and r["storage"] == "12/256" else r for r in rows]
    assert "less" not in macro("price_box", unsettled, "china", "12/256", view.DEFAULT, labels, True)
    assert "less" not in macro("price_box", [{**r, "settled": False} if r["edition"] == "global" else r for r in rows], "china", "12/256", view.DEFAULT, labels, True)
    # "base" rows may be different memories: no number there, though both are settled and one is cheaper
    base = [{**r, "storage": "base"} for r in rows if r["storage"] == "12/256"]
    assert view.best_of(base, "china", "base")["settled"] and view.best_of(base, "global", "base")["settled"]
    assert "less" not in macro("price_box", base, "china", "base", view.DEFAULT, labels, True)
    # equal totals: neither is cheaper
    eq = [{**r, "total": 1000} if r["edition"] == "global" and r["storage"] == "12/256" else r for r in rows]
    assert "less" not in macro("price_box", eq, "china", "12/256", view.DEFAULT, labels, True)


def test_boxes_are_toggles_and_the_verdict_is_their_region(oppo):
    rows, _ = oppo
    labels = {"global": "Global", "china": "China"}
    for e in ("china", "global"):
        for on in (True, False):
            box = macro("price_box", rows, e, "12/256", view.DEFAULT, labels, on)
            assert f'aria-pressed="{"true" if on else "false"}" aria-controls="pick-panel" id="tab-{e}"' in box
            assert "role=" not in box and "aria-selected" not in box
            assert (" on" in root_of(box)) == on
    best = view.best_of(rows, "china", "12/256")
    pick = [r for r in rows if r["edition"] == "china" and r["storage"] == "12/256"]
    panel = macro("verdict", best, pick, view.DEFAULT, labels)
    assert re.match(r'<section class="verdict panel" id="pick-panel" role="region" aria-labelledby="tab-china"', panel)
    assert "Cheapest delivered" in text(panel) and "View at" in text(panel)
    empty = macro("verdict", None, [], view.DEFAULT, labels)
    assert 'role="region"' in empty and "aria-labelledby" not in empty and "No store we check" in text(empty)


@needs_node
def test_js_blocks_escape_the_memory_pick(oppo, tax_file):
    """A memory string from the page (hash, data-m) comes out escaped in the not-sold text and the nearest button."""
    src = (ROOT / "static" / "js" / "blocks.js").as_uri()
    js = (f'import {{ priceBox, memChips }} from "{src}";\n'
          'const rows = [{edition: "china", storage: "12/256", state: "ok", total: 1, settled: true, store: "S", left: "x", link: null}];\n'
          'const s = {region: "EU", area: "", pay: "card", cur: "eur"}, l = {global: "Global", china: "China"};\n'
          'console.log(JSON.stringify([priceBox(rows, "global", "<b>/1", s, l, false, true), memChips(rows, "\\"><i>", s)]));')
    r = subprocess.run(["node", "--input-type=module", "-e", js], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    for h in json.loads(r.stdout):
        assert "<i>" not in h and "<b>/1" not in h


@needs_node
def test_price_box_means_link_follows_the_brand(fixture_doc, tax_file, tax, tmp_path):
    """The China box's link to "What the China version means" is the brand's (config/google.yaml `means`): Android
    wording by default, Apple's own for an iPhone, the same in Jinja and JS."""
    f, inputs, s, e, st = _fixture_cases(fixture_doc, tmp_path)[0]
    rows = view.rows(inputs, tax, s)
    for brand, want in (("Xiaomi", "Chinese software, Google Play off at first"), ("Apple", "No Apple Intelligence for now")):
        labels = ed_labels(brand)
        py = render_py(rows, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])
        js = render_js(f, tax_file, s, labels, e, st, fixture_doc["meta"], fixture_doc["now"])
        assert_same(py, js, brand)
        assert want in text(py["price_box"]) and want in text(js["price_box"])


# --- the price trend block (spec 2026-10-31 §3): Jinja macro and JS twin, with the exact copy ---

def _trend(**kw):
    t = {"short": False, "first_day": "2026-09-01", "window_start": "2026-10-02", "since_day": "2026-10-02", "full_window": True, "now": 2736, "low": 2652,
         "low_day": "2026-11-12", "low_store": "Trading Shenzhen", "high": 2901, "high_approx": False, "recent_gap": False, "is_low": False, "change_pct": -3.0,
         "since_first": False, "change_7d": 4.0, "approx": False}
    return {**t, **kw}


def _trend_js(t, s=view.DEFAULT, hist="../history/x"):
    r = subprocess.run(["node", str(HARNESS), "--trend", json.dumps(t), "--settings", ",".join(s), "--hist", hist],
                       check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)["price_trend"]


TREND_CASES = {
    "full": (_trend(), "€2,736 · low €2,652 – high €2,901 €84 above its 30-day low (€2,652 on 12 Nov at Trading Shenzhen) "
                       "Down 3% in the last 30 days Up 4% in the last 7 days Full price history →"),
    "at the low": (_trend(now=2652, is_low=True, change_7d=1.9, change_pct=-8.2), "€2,652 · low €2,652 – high €2,901 Lowest price in 30 days "
                   "Down 8% in the last 30 days Full price history →"),
    "since first": (_trend(full_window=False, first_day="2026-10-15", since_day="2026-10-15", since_first=True, change_pct=-9.0, change_7d=None),
                    "€2,736 · low €2,652 – high €2,901 €84 above its low since 15 Oct (€2,652 on 12 Nov at Trading Shenzhen) "
                    "Down 9% since first listed (15 Oct) Full price history →"),
    "not full, at the low": (_trend(full_window=False, first_day="2026-10-15", since_day="2026-10-15", now=2652, is_low=True, since_first=True, change_pct=0.4, change_7d=-2.5),
                             "€2,652 · low €2,652 – high €2,901 Lowest price since 15 Oct About the same since first listed (15 Oct) "
                             "Down 3% in the last 7 days Full price history →"),
    "about the same": (_trend(change_pct=-0.9, change_7d=None), "€2,736 · low €2,652 – high €2,901 €84 above its 30-day low (€2,652 on 12 Nov at Trading Shenzhen) "
                       "About the same over the last 30 days Full price history →"),
    "gap, flat since": (_trend(now=2652, low=2652, high=2652, is_low=True, change_pct=0.0, change_7d=0.0, first_day="2026-08-12", since_day="2026-10-20", full_window=False),
                        "Same price since 20 Oct Full price history →"),
    "gap, at the low": (_trend(full_window=False, first_day="2026-08-12", since_day="2026-10-20", now=2652, is_low=True, change_pct=-5.0, change_7d=None),
                        "€2,652 · low €2,652 – high €2,901 Lowest price since 20 Oct Down 5% since 20 Oct Full price history →"),
    "gap, above the low": (_trend(full_window=False, first_day="2026-08-12", since_day="2026-10-20", change_pct=0.4, change_7d=None),
                           "€2,736 · low €2,652 – high €2,901 €84 above its low since 20 Oct (€2,652 on 12 Nov at Trading Shenzhen) "
                           "About the same since 20 Oct Full price history →"),
    "too short": (_trend(short=True, first_day="2026-10-28"), "Price history for this version and memory starts on 28 Oct, too short to judge yet. "
                                                              "Full price history →"),
    "same price since": (_trend(now=2652, low=2652, high=2652, is_low=True, change_pct=0.0, change_7d=0.0, first_day="2026-10-15", since_day="2026-10-15", full_window=False),
                         "Same price since 15 Oct Full price history →"),
    "same price 30 days": (_trend(now=2652, low=2652, high=2652, is_low=True, change_pct=0.0, change_7d=None, first_day="2026-09-01"),
                           "Same price for 30 days Full price history →"),
    "same price with a 7-day move": (_trend(now=2652, low=2652, high=2652, is_low=True, change_pct=-3.0, change_7d=-2.5),
                                     "Same price for 30 days Down 3% in the last 7 days Full price history →"),
    "recent gap": (_trend(short=True, recent_gap=True, first_day="2026-08-01"),
                   "Not enough recent price history for this version and memory to judge yet. Full price history →"),
    "approx high only": (_trend(high_approx=True, change_pct=None, change_7d=None),
                         "€2,736 · low €2,652 – high ≈€2,901 €84 above its 30-day low (€2,652 on 12 Nov at Trading Shenzhen) Full price history →"),
    "approx": (_trend(approx=True, high_approx=True, change_pct=None, change_7d=None), "≈€2,736 · low ≈€2,652 – high ≈€2,901 ≈€84 above its 30-day low (≈€2,652 on 12 Nov at Trading Shenzhen) Full price history →"),
}


@needs_node
@pytest.mark.parametrize("name", sorted(TREND_CASES))
def test_price_trend_parity_and_copy(name):
    t, want = TREND_CASES[name]
    py, js = macro("price_trend", t, view.DEFAULT, "../history/x"), _trend_js(t)
    assert text(py) == want
    assert text(js) == want
    assert root_of(py) == root_of(js) == "section|trend|price_trend"
    assert structure(py) == structure(js)
    assert 'href="../history/x"' in py


@needs_node
def test_price_trend_copy_from_real_numbers():
    """view.price_trend -> both renderers: flat after an earlier higher price, a pick back after 35 days, a 7-cent difference."""
    day = lambda n, t, **k: {"day": f"2026-10-{n:02d}", "total": t, "store": "s", "approx": False, **k}
    now = {"total": 900.0, "approx": False, "store": "now"}
    flat = [{"day": "2026-09-15", "total": 1000, "store": "s", "approx": False}] + [day(n, 900) for n in range(2, 31)]
    away = [{"day": "2026-09-20", "total": 1000, "store": "s", "approx": False}]
    cents = [day(n, 1000.04 if n % 2 else 999.97) for n in range(2, 31)]
    for days, row, want in ((flat, now, "Same price for 30 days Full price history →"),
                            (away, now, "Not enough recent price history for this version and memory to judge yet. Full price history →"),
                            (cents, {**now, "total": 1000.0}, "Same price for 30 days Full price history →")):
        t = view.price_trend(days, row, "2026-10-31")
        assert text(macro("price_trend", t, view.DEFAULT, "../history/x")) == want
        assert text(_trend_js(t)) == want


@needs_node
def test_price_trend_bar_marker_and_currency():
    t = _trend(now=2736, low=2652, high=2901)   # (2736-2652)/(2901-2652) = 33.7% -> 34
    for h in (macro("price_trend", t, view.DEFAULT, "../history/x"), _trend_js(t)):
        assert '<div class="tbar" aria-hidden="true"><i style="--at:34%"></i></div>' in h
    for tt, at in ((_trend(now=2652, low=2652), 0), (_trend(now=2901, low=2652), 100), (_trend(now=3000), 100), (_trend(now=2000), 0)):
        for h in (macro("price_trend", tt, view.DEFAULT, "../history/x"), _trend_js(tt)):
            assert f'--at:{at}%"' in h
    same = _trend(low=2652, high=2652, now=2652, is_low=True)
    for h in (macro("price_trend", same, view.DEFAULT, "../history/x"), _trend_js(same)):
        assert "tbar" not in h
    assert text(macro("price_trend", t, UK_PAYPAL, "../history/x")).startswith("£2,736 · low £2,652")
    assert text(_trend_js(t, UK_PAYPAL)).startswith("£2,736 · low £2,652")


@needs_node
def test_price_trend_none_is_empty_and_strings_are_escaped():
    assert macro("price_trend", None, view.DEFAULT, "../history/x").strip() == ""
    out = subprocess.run(["node", str(HARNESS), "--trend", "null"], check=False, capture_output=True, text=True, cwd=ROOT)
    assert json.loads(out.stdout)["price_trend"] == ""
    t = _trend(low_store='A<b>&"')
    py, js = macro("price_trend", t, view.DEFAULT, "../history/x"), _trend_js(t)
    assert "<b>" not in py and "<b>" not in js
    assert structure(py) == structure(js) and text(py) == text(js)
