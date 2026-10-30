import html
import re
import shutil
import subprocess
from pathlib import Path

import pytest


def test_d_css_and_fonts_are_built(site_build):
    assert (site_build / "static/d.css").exists()
    assert (site_build / "static/fonts/albert-sans-400.woff2").exists()


def test_no_page_calls_google_fonts(site_build):
    for f in site_build.rglob("*.html"):
        assert "fonts.googleapis" not in f.read_text(), f


def test_headers_cache_js_modules_and_d_css(site_build):
    h = (site_build / "_headers").read_text()
    assert "/static/js/*\n  Cache-Control: public, max-age=31536000, immutable" in h
    assert "/static/d.css\n  Cache-Control: public, max-age=31536000, immutable" in h


def test_asset_hashes_cover_d_css_and_js_modules(site_build):
    from pricechecker import fx, run, terms
    from pricechecker.site import context, offers
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    v = context.page_context(data, offers.assemble(data))["asset_v"]
    assert {"app.js", "style.css", "d.css", "js/pricing.js"} <= set(v)
    assert all(len(h) == 10 for h in v.values())


def test_js_imports_carry_the_hash_of_the_imported_module(tmp_path):
    from pricechecker.site import assets
    (tmp_path / "b.js").write_text("export const b = 1;\n")
    (tmp_path / "a.js").write_text('import { b } from "./b.js";\nexport { b } from \'./b.js\';\nexport const a = b;\n')
    m = assets.versioned_modules(tmp_path)
    hb = m["b.js"][1]
    assert f'from "./b.js?v={hb}"' in m["a.js"][0] and f"from './b.js?v={hb}'" in m["a.js"][0]
    (tmp_path / "b.js").write_text("export const b = 2;\n")
    m2 = assets.versioned_modules(tmp_path)
    assert m2["b.js"][1] != hb and m2["a.js"][1] != m["a.js"][1]
    assert 'from "./b.js"' in (tmp_path / "a.js").read_text()   # sources stay unmodified


def test_built_js_matches_asset_hash(site_build):
    import hashlib

    from pricechecker import fx, run, terms
    from pricechecker.site import context, offers
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    v = context.page_context(data, offers.assemble(data))["asset_v"]
    for f in (site_build / "static/js").glob("*.js"):
        assert hashlib.sha256(f.read_bytes()).hexdigest()[:10] == v[f"js/{f.name}"]


def test_every_page_has_the_shell(site_build):
    pages = [f for f in site_build.rglob("*.html") if "mock" not in f.relative_to(site_build).parts]
    assert pages
    for f in pages:
        html = f.read_text()
        assert 'class="top' in html, f
        assert "data-prefs" in html, f
        for label in (">Phones<", ">Drops<", ">Compare<"):
            assert label in html, (f, label)
        for link in (">Stores<", ">How we work out totals<", ">About<", ">Privacy<", ">Telegram<", ">r/DoorPrice<"):
            assert link in html, (f, link)
        assert "https://t.me/DoorPriceDeals" in html and "https://www.reddit.com/r/DoorPrice/" in html, f
        assert "static/app.js" not in html and 'id="import-tax"' not in html and "phone-names" not in html, f
        assert "Other countries and payment methods need JavaScript" in html, f
        assert "Delivered = store price" in html, f
        assert 'type="module" src=' in html and "js/settings.js?v=" in html, f
        assert 'aria-label="Search phones"' in html, f


# ---- phone page (spec §5.2) ----
ROOT = Path(__file__).resolve().parent.parent


def _phone(site_build, pid):
    return (site_build / "phones" / f"{pid}.html").read_text()


def test_phone_page_sections(site_build):
    h = _phone(site_build, "oppo-find-x9-ultra")
    assert h.count('data-block="price_box"') == 2
    for blk in ("gap_line", "mem_chips", "verdict", "receipt", "store_list", "ledger", "buy_bar"):
        assert f'data-block="{blk}"' in h, blk
    for t in ("Compare every offer (", "What the China version means", "Price history by store", "More from Oppo",
              "Oppo Find X9 Ultra price: <em>China vs Global</em>", "data-for"):
        assert t in h, t
    assert re.search(r'href="oppo-find-x9-ultra/specs"[^>]*>All \d+ specs', h)
    actions = h[h.index('class="actions"'):]
    for a in (">Watch<", ">History<", ">Compare<", ">Share<"):
        assert a in actions, a
    assert 'href="../feeds/oppo-find-x9-ultra.xml"' in h and 'href="../history/oppo-find-x9-ultra"' in h
    assert "<polyline" in h and "var(--s1)" in h
    assert re.search(r'data-file="\.\./data/v1/phone/oppo-find-x9-ultra\.[0-9a-f]{10}\.json"', h)
    assert re.search(r'data-tax="\.\./data/v1/tax\.[0-9a-f]{10}\.json"', h)
    assert "js/phone.js?v=" in h
    assert 'id="offers"' not in h   # the offers come from the v1 file, not the HTML


def _old_title_rules(p, month):
    """The live title, description and share-card text rules, written out (templates/phone.html before the rewrite)."""
    L, eds, tp = p["ed_label"], p["editions"], p["title_price"]
    kind = f"price in {L['china']} vs Global" if len(eds) > 1 else (f"{L['china']} version price" if "china" in eds else "price")
    frm = (f": from €{tp[0]:,.0f}" + (" delivered" if tp[1] else "")) if tp else ""
    title = f"{p['name']} {kind}{frm} [{month}] – DoorPrice"
    n = p["n_stores"]
    desc = (f"{p['name']}" + ((f" from €{tp[0]:,.0f}" + (" delivered to the EU" if tp[1] else "")) if tp else "")
            + f": compare {n} store{'s' if n != 1 else ''}" + (", Global and China versions side by side" if len(eds) > 1 else "")
            + ", with payment fees, shipping and import tax worked in. Updated hourly.")
    alt = f"{p['name']} on DoorPrice" + ((f": from €{tp[0]:,.0f}" + (" delivered to the EU" if tp[1] else "")) if tp else "")
    return title, desc, alt


def test_phone_title_rules_unchanged(site_build):
    from pricechecker import fx, run, terms
    from pricechecker.site import context, offers
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    phones = {p["id"]: p for p in offers.assemble(data)}
    month = data.updated_at.strftime("%B %Y")
    samsung = next(i for i in phones if i.startswith("samsung-") and len(phones[i]["editions"]) > 1)
    for pid in ("oppo-find-x9-ultra", "oneplus-16", samsung):
        h = _phone(site_build, pid)
        got = [html.unescape(re.search(pat, h, re.DOTALL)[1]) for pat in
               (r"<title>(.*?)</title>", r'<meta name="description" content="(.*?)">', r'og:image:alt" content="(.*?)">')]
        assert got == list(_old_title_rules(phones[pid], month)), pid


def test_china_only_phone_has_one_box_and_reason(site_build):
    h = _phone(site_build, "oneplus-16")
    assert h.count('data-block="price_box"') == 1
    assert "No Global version so far: OnePlus sells this phone in China only" in h
    assert 'data-block="gap_line"' not in h
    assert "OnePlus 16 price: <em>China version</em>" in h


def test_phone_pages_within_budget(site_build):
    big = {f.name: f.stat().st_size for f in (site_build / "phones").glob("*.html") if f.stat().st_size > 60_000}
    assert not big, big


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_switching_version_falls_back_to_its_best_memory():
    r = subprocess.run(["node", str(ROOT / "tests/js/phone_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_phone_page_report_status_and_live_verdict():
    """The report form (when switched on) has the status line that #report-thanks / #report-error fill; the verdict's
    slot is a polite live region, so a repainted total is read out."""
    from pricechecker import fx, run, terms
    from pricechecker.site import _env, context, offers
    from pricechecker.site.pages import phone
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    phones = offers.assemble(data)
    ctx = context.page_context(data, phones)
    ctx["site"] = {**ctx["site"], "reports_live": True}
    h = phone.render(_env(), data, ctx, phones)["phones/oppo-find-x9-ultra.html"]
    report = h[h.index('class="report"'):]
    assert 'action="../api/report"' in report and 'id="rf-status"' in report and 'role="status"' in report
    assert '<div id="s-verdict" aria-live="polite">' in h


def test_memory_chip_without_a_current_price_is_disabled(site_build):
    from pricechecker.site import _env
    tpl = _env().from_string('{% from "_d/blocks.html" import mem_chips %}{{ mem_chips(rows, "china", "12/256", s) }}')
    from pricechecker.site.view import DEFAULT
    rows = [{"edition": "china", "storage": "12/256", "state": "ok", "total": 1000, "unknown": 0},
            {"edition": "china", "storage": "16/512", "state": "stale", "total": 900, "unknown": 0}]
    h = tpl.render(rows=rows, s=DEFAULT)
    assert 'data-m="16/512" aria-pressed="false" disabled>16 GB · 512 GB · –<' in h
    assert not re.search(r'data-m="12/256"[^>]*disabled', h)


# ---- home page (spec §5.1) ----
def _home(site_build):
    return (site_build / "index.html").read_text()


def test_home_sections(site_build):
    h = _home(site_build)
    assert "China version or Global? <em>Both prices, delivered.</em>" in h and "data-for" in h
    assert re.search(r'<input id="q" type="search" placeholder="Which phone\? e\.g\. “x9 ultra”"', h)
    assert re.search(r'<a class="teaser" href="drops">\s*<b>\d+ price drops? this week</b>', h)
    chips = h[h.index('id="chips"'):h.index('id="sorts"')]
    for label in (">All<", ">Both versions<", ">China<", ">Global<", "Watched (<span"):
        assert label in chips, label
    assert chips.index(">Global<") < chips.index("Watched (<span") < chips.index('data-b="oppo"')
    assert 'data-b="oppo"' in chips and 'data-b="samsung"' in chips
    sel = h[h.index('id="rom"'):]
    sel = sel[:sel.index("</select>")]
    for o in ("any storage", ">256 GB<", ">512 GB<", ">1 TB<"):
        assert o in sel, o
    sorts = h[h.index('id="sorts"'):h.index('id="count"')]
    for label in (">Newest<", ">Biggest China saving<", ">Lowest price<", ">Dropped this week<"):
        assert label in sorts, label
    n = h.count('data-block="home_row"')   # every phone is linked from the page; the first 20 show, then "Show all N"
    assert n > 50 and 'id="list" data-cap="20"' in h and f">Show all {n} phones<" in h and f"{n} phones · lowest" in h
    assert "The stores, and what they cover" in h
    assert re.search(r'<div class="no-results" id="no-results" role="status" hidden>\s*<p id="nr-text">No phones match these filters\.</p>\s*<button[^>]*>Clear filters</button>', h)
    assert re.search(r'id="home"[^>]*data-files=', h) and re.search(r'data-tax="data/v1/tax\.[0-9a-f]{10}\.json"', h)
    assert re.search(r'"EU": \["data/v1/home-EU-1\.[0-9a-f]{10}\.json"', h)
    assert "js/home.js?v=" in h and "offers_json" not in h and "data-offers" not in h
    assert 'prow-link' not in h


def test_home_within_budget(site_build):
    assert (site_build / "index.html").stat().st_size <= 120_000


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_home_filter_sort_and_region_cases():
    r = subprocess.run(["node", str(ROOT / "tests/js/home_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_home_summaries_match_the_browsers(site_build):
    """The per-phone summaries the server embeds (default settings) are what home.js works out from the EU files."""
    import json
    h = _home(site_build)
    meta = json.loads(html.unescape(re.search(r'<script type="application/json" id="home-meta">(.*?)</script>', h, re.DOTALL).group(1)))
    files = sorted((site_build / "data/v1").glob("home-EU-*.json"))
    r = subprocess.run(["node", str(ROOT / "tests/js/home_cases.mjs"), "--summaries", ",".join(map(str, files)),
                        str(next((site_build / "data/v1").glob("tax.*.json")))], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert len(meta) > 50
    for m in meta:
        assert got.get(m["id"], {}) == m.get("s", {}), m["id"]


def test_home_rows_carry_the_drop_mark(site_build):
    import json
    h = _home(site_build)
    meta = json.loads(re.search(r'id="home-meta">(.*?)</script>', h, re.DOTALL).group(1))
    with_drop = [m["id"] for m in meta if m.get("drop")]
    without = [m["id"] for m in meta if not m.get("drop")]
    assert with_drop and without

    def row(pid):
        i = h.index(f'<li class="pair" data-block="home_row" data-id="{pid}">')
        return h[i:h.index("</li>", i)]

    for pid in with_drop:
        assert row(pid).endswith('</a><span class="marks"><span class="mark drop">↓ this week</span></span>'), pid
    for pid in without:
        assert "mark" not in row(pid), pid
    assert '<ul class="pairs" id="list" data-cap="20"><' not in h and re.search(r'<ul class="pairs" id="list"[^>]*>\s*<li class="pair"', h)
    assert h.count('class="mark drop"') == len(with_drop)
