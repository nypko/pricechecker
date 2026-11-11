import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

# reads the saved prices or the real build: excluded from the hourly production run (pytest -m "not live")
live = pytest.mark.live
# page sizes of the real build: checked in the newsite/testing workflows (DOORPRICE_CHECK_BUDGETS=1), never hourly
live_budgets = pytest.mark.skipif(os.environ.get("DOORPRICE_CHECK_BUDGETS") != "1", reason="set DOORPRICE_CHECK_BUDGETS=1")


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
    assert {"d.css", "js/pricing.js"} <= set(v) and not {"app.js", "style.css"} & set(v)
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
        assert 'for="hq" class="sr-only">Search phones<' in html, f


# ---- phone page (spec §5.2) ----
ROOT = Path(__file__).resolve().parent.parent


def _phone(site_build, pid):
    return (site_build / "phones" / f"{pid}.html").read_text()


@live
def test_phone_page_sections(site_build):
    h = _phone(site_build, "oppo-find-x9-ultra")
    assert h.count('data-block="price_box"') == 2
    for blk in ("mem_chips", "verdict", "receipt", "store_list", "ledger", "buy_bar"):
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


def _title_rules(p, month):
    """The title, description and share-card text rules, written out: name and price first, then "China vs Global"."""
    L, eds, tp = p["ed_label"], p["editions"], p["title_price"]
    kind = f"{L['china']} version price" if eds == ["china"] else "price"
    frm = (f": from €{tp[0]:,.0f}" + (" delivered" if tp[1] else "")) if tp else ""
    versus = f", {L['china']} vs Global" if len(eds) > 1 else ""
    title = f"{p['name']} {kind}{frm}{versus} [{month}] – DoorPrice"
    n = p["n_stores"]
    desc = (f"{p['name']}" + ((f" from €{tp[0]:,.0f}" + (" delivered to the EU" if tp[1] else "")) if tp else "")
            + f": compare {n} store{'s' if n != 1 else ''}" + (", Global and China versions side by side" if len(eds) > 1 else "")
            + ", with payment fees, shipping and import tax worked in. Updated several times a day.")
    alt = f"{p['name']} on DoorPrice" + ((f": from €{tp[0]:,.0f}" + (" delivered to the EU" if tp[1] else "")) if tp else "")
    return title, desc, alt


@live
def test_phone_title_rules(site_build):
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
        assert got == list(_title_rules(phones[pid], month)), pid


@live
def test_china_only_phone_has_one_box_and_reason(site_build):
    h = _phone(site_build, "oneplus-16")
    assert h.count('data-block="price_box"') == 1
    assert "No Global version so far: OnePlus sells this phone in China only" in h
    assert "OnePlus 16 price: <em>China version</em>" in h


def test_iphone_china_version_copy_is_apples_not_androids(site_build):
    """An iPhone's "What the China version means" and explainer use Apple's entry in config/google.yaml: no Google Play
    wording, no Google Wallet caveat."""
    h = _phone(site_build, "apple-iphone-duo")
    assert "What the China version means" in h
    assert "The China version has no Apple Intelligence for now" in h
    assert "<dt>Apple Intelligence</dt>" in h and "Apple may limit iPhone warranty service" in h
    assert "Google" not in h[h.index('id="means-h"'):h.index("Price history by store")]


def test_china_bullets_follow_the_brand_and_the_band_check(site_build):
    """The short China-version bullets don't hedge against the same page: an iPhone's warranty line is Apple's, and a China
    version whose band check passes says it has the main EU bands; other brands keep the general warranty line."""
    means = lambda h: h[h.index('id="means-h"'):h.index("Price history by store")]
    m = means(_phone(site_build, "apple-iphone-duo"))
    assert "<b>Count on the store&#39;s warranty.</b> Apple may limit iPhone warranty service" in m
    assert "<b>Has all the main EU 4G/5G bands.</b>" in m
    assert "manufacturer's usually" not in m and "may be missing" not in m
    assert "<b>Warranty usually comes from the store.</b>" in means(_phone(site_build, "oneplus-16"))


@live
@live_budgets
def test_phone_pages_within_budget(site_build):
    big = {f.name: f.stat().st_size for f in (site_build / "phones").glob("*.html") if f.stat().st_size > 60_000}
    assert not big, big


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_memory_first_pick_rules_in_the_page_module():
    """tests/js/phone_cases.mjs: phone.js's pick rules and focus selectors, and its carrier wiring (wireCarrier): the
    network check, and the price boxes' network lines, which never show another country's, even while a newly chosen
    country's file loads."""
    r = subprocess.run(["node", str(ROOT / "tests/js/phone_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_phone_page_report_status_and_live_verdict():
    """The report form (when switched on) has the status line that #report-thanks / #report-error fill; the verdict's
    wrapper is a polite live region, so a repainted total is read out."""
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
    # the live region is the wrapper that persists across repaints, not the panel paint() replaces inside it
    assert '<div id="s-verdict" aria-live="polite"><section class="verdict panel" id="pick-panel"' in h
    assert not re.search(r'<section class="verdict panel"[^>]*aria-live', h)


def test_memory_chip_without_a_current_price_is_disabled(site_build):
    from pricechecker.site import _env
    tpl = _env().from_string('{% from "_d/blocks.html" import mem_chips %}{{ mem_chips(rows, "12/256", s) }}')
    from pricechecker.site.view import DEFAULT
    rows = [{"edition": "china", "storage": "12/256", "state": "ok", "total": 1000, "unknown": 0},
            {"edition": "china", "storage": "16/512", "state": "stale", "total": 900, "unknown": 0}]
    h = tpl.render(rows=rows, s=DEFAULT)
    assert re.search(r'data-m="16/512" aria-pressed="false" disabled>', h)
    assert not re.search(r'data-m="12/256"[^>]*disabled', h)


# ---- home page (spec §5.1) ----
def _home(site_build):
    return (site_build / "index.html").read_text()


@live
def test_home_sections(site_build):
    h = _home(site_build)
    assert "What imported flagship phones really cost, <em>delivered to your door.</em>" in h and 'class="hero intro"' in h
    assert re.search(r'<input id="hq" name="q" type="search" placeholder="Search" data-wide="Which phone\? e\.g\. “x9 ultra”"', h)
    assert re.search(r'<a class="teaser" href="drops">\s*<b>↓ \d+ price drops? this week</b>', h)
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


@live
@live_budgets
def test_home_within_budget(site_build):
    assert (site_build / "index.html").stat().st_size <= 120_000


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_home_filter_sort_and_region_cases():
    r = subprocess.run(["node", str(ROOT / "tests/js/home_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


@live
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


@live
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
        assert "class=\"marks\"" not in row(pid), pid
    assert '<ul class="pairs" id="list" data-cap="20"><' not in h and re.search(r'<ul class="pairs" id="list"[^>]*>\s*<li class="pair"', h)
    assert h.count('class="mark drop"') == len(with_drop)


# --- Task 7: specs pages ---

def test_specs_page_for_a_full_sheet(site_build):
    html_ = (site_build / "phones/oppo-find-x9-ultra/specs.html").read_text()
    assert "Show only the 7 differences" in html_
    assert 'class="split"' in html_ and "page only" not in html_
    assert 'href="../oppo-find-x9-ultra"' in html_
    assert "https://www.oppo.com/en/smartphones/series-find-x/find-x9-ultra/specs/" in html_ and "26 Oct 2026" in html_
    # same-hardware field only one page lists: one plain cell, not split; "in the box" splits with Not listed
    assert "AMOLED, Gorilla Glass Victus 2</td>" in html_ and "Not listed" in html_
    assert html_.count('class="split"') == 8   # the 7 differences + "In the box" (market-dependent, split but not counted)
    assert "static/js/specs.js" in html_


def test_specs_page_exists_exactly_where_the_phone_page_links_it(site_build):
    from pricechecker import specs
    sheets = specs.load()
    linked = 0
    for pid, sheet in sheets.items():
        page = site_build / f"phones/{pid}/specs.html"
        phone = site_build / f"phones/{pid}.html"
        if not phone.exists():
            continue
        has_link = f'href="{pid}/specs"' in phone.read_text()
        assert has_link == page.exists() == specs.has_page(sheet), pid
        linked += has_link
    assert linked and not all(specs.has_page(s) for s in sheets.values())


# ---- drops page and feed (spec §5.4) ----

def _drops(site_build):
    return (site_build / "drops.html").read_text()


@live
def test_drops_page_lists_what_the_home_page_counts(site_build):
    h, home = _drops(site_build), _home(site_build)
    n = len(re.findall(r'<li class="drop" ', h))
    m = re.search(r"<b>↓ (\d+) price drops? this week</b>", home)
    assert n == (int(m.group(1)) if m else 0)
    assert '<link rel="canonical"' in h and "feeds/drops.xml" in h and "https://t.me/DoorPriceDeals" in h
    assert h.count('data-block="store_row"') == n   # every row's current total is the store_row block
    entries = (site_build / "feeds/drops.xml").read_text().count("<entry>")
    assert entries == n


def test_price_drop_rule_is_on_the_drops_page_not_the_home_page(site_build):
    from pricechecker import derive
    rule = f"{derive.MIN_PCT}% and €{derive.MIN_EUR}"
    assert rule in text_of(_drops(site_build))
    assert "cheaper by" not in _home(site_build) and rule not in text_of(_home(site_build))


def test_home_intro_says_what_doorprice_is():
    from pricechecker.site.pages import home
    data, phones, env, ctx = _made_up([("wonda", "oppo-find-x9-ultra", "china", "12/256", 1000.0, True),
                                       ("giztop", "oppo-find-x9-ultra", "global", "12/256", 1300.0, True),
                                       ("mobilemarvel", "oneplus-16", "china", "12/256", 900.0, True)])
    h = home.render(env, data, ctx, phones)["index.html"]
    t = re.sub(r" ([.,])", r"\1", text_of(h))   # text_of puts a space where an inline tag closes: "the EU ."
    assert "What imported flagship phones really cost, delivered to your door." in t
    assert ("DoorPrice compares 3 import stores several times a day and adds shipping, payment fees and import tax "
            "for the EU. We don't sell phones.") in t
    chips = re.findall(r'<a class="chip" href="stores/(\w+)">([^<]+)<b>★([\d.]+)</b>', h)
    assert [c[1].strip() for c in chips] == ["The Mobile Marvel", "Wonda Mobile", "Giztop"]
    # a labelled group: screen readers ignore an aria-label on a div without a role
    assert '<div class="storechips" role="group" aria-label="Stores compared, with their Trustpilot score">' in h
    assert f'<time datetime="{data.latest["updated"]}" data-ago>' in h
    assert "Affiliate links never change the order" in t and 'href="about">How it works</a>' in h
    assert "China version or Global?" not in t and 'data-for' not in h.split('id="list"')[0]


def test_drops_page_is_in_the_sitemap_and_loads_its_module(site_build):
    assert 'static/js/drops.js?v=' in _drops(site_build)
    sm = (site_build / "sitemap.xml").read_text()
    assert "<loc>https://doorprice.app/drops</loc>" in sm


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_drops_js_filter_and_row_lookup():
    r = subprocess.run(["node", str(ROOT / "tests/js/drops_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def _assemble(offers, data):
    """offers.assemble without the saved promotion scan (data/promos.json, rewritten hourly): whether a store's
    promotion counts then comes from stores.yaml alone, so made-up pages don't change with the hourly data."""
    from pricechecker import promos
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(promos, "STATE", Path("/nonexistent/promos.json"))
        return offers.assemble(data)


def _synthetic(n, days_then, days_now, pct_down, eur_down):
    """The real site's data with its history swapped for `n` listings (one per phone) that went from price X to
    X - drop: returns (data, phones, env, ctx, listings) to render the drops page from."""
    import dataclasses
    from datetime import timedelta

    from pricechecker import fx, run, terms
    from pricechecker.site import _env, context, offers
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    phones = _assemble(offers, data)
    label_key = {c.get("label", k): k for k, c in data.stores_cfg.items() if k in data.live_stores}
    picks = []
    for p in phones:
        o = next((o for o in p["offers"] if o["store_label"] in label_key), None)   # any stock state or age: no fresh prices needed
        if o:
            picks.append((p, o))
        if len(picks) == n:
            break
    stamp = lambda days: (data.updated_at - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for (p, o), pd, ed in zip(picks, pct_down, eur_down, strict=True):
        was = ed / (pd / 100)
        base = {"store": label_key[o["store_label"]], "model_id": p["id"], "edition": o["edition"], "storage": o["storage"],
                "currency": "EUR", "available": True}
        rows += [{**base, "time": stamp(days_then), "price": was}, {**base, "time": stamp(days_now), "price": was - ed}]
    data = dataclasses.replace(data, rows=rows, rows_all=rows)
    return data, phones, _env(), context.page_context(data, phones), picks


def test_only_the_real_drop_is_listed_and_the_home_count_agrees():
    from pricechecker.site.pages import drops, home
    # 5% / EUR 50, 2% / EUR 20 (too small a share), 4% / EUR 15 (too small a sum)
    data, phones, env, ctx, picks = _synthetic(3, 10, 1, (5, 2, 4), (50, 20, 15))
    items = drops.this_week(data, phones)
    assert [d["slug"] for d in items] == [picks[0][0]["id"]]
    assert home.page(data, ctx, phones)["n_drops"] == len(items) == 1
    h = drops.render(env, data, ctx, phones)["drops.html"]
    assert h.count('<li class="drop" ') == 1 and "−5%" in h and "€1,000" in h and "€950" in h
    assert "No drops this week" not in h and "Posted to Telegram</span>" not in h.split("</p>", 6)[-1]
    assert "Old and new are the store's price in euros (converted at today's ECB rate)" in html.unescape(h)
    assert '<link rel="alternate" type="application/atom+xml" title="DoorPrice price drops" href="feeds/drops.xml">' in h


def test_a_drop_the_telegram_channel_posted_is_marked(monkeypatch):
    from pricechecker.site.pages import drops
    data, phones, env, ctx, picks = _synthetic(1, 10, 1, (5,), (50,))
    at = data.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {"phones": {"posted": [{"slug": picks[0][0]["id"], "at": at, "was": 1000, "eur": 950}]}}
    monkeypatch.setattr(drops, "_telegram_state", lambda: state)
    h = drops.render(env, data, ctx, phones)["drops.html"]
    li = h[h.index('<li class="drop" '):h.index("</li>\n", h.index('<li class="drop" '))]
    assert '<span class="mark tg">Posted to Telegram</span>' in li
    monkeypatch.setattr(drops, "_telegram_state", dict)
    assert 'class="mark tg">Posted to Telegram' not in drops.render(env, data, ctx, phones)["drops.html"].split('id="list"')[1]


def test_an_empty_week_shows_at_most_five_earlier_drops(monkeypatch):
    from pricechecker.site.pages import drops
    # seven drops 14 days ago: none this week
    data, phones, env, ctx, picks = _synthetic(7, 40, 14, (10,) * 7, (100,) * 7)
    assert len(picks) == 7 and drops.this_week(data, phones) == []
    h = drops.render(env, data, ctx, phones)["drops.html"]
    assert "No drops this week" in h and 'id="chips"' not in h
    assert h.count('<li class="drop" ') == 5 == len(drops.earlier(data, phones))
    # two drops that happened longer ago than the 30-day look-back are not offered
    data2, phones2, env2, ctx2, _ = _synthetic(2, 90, 70, (10, 10), (100, 100))
    h2 = drops.render(env2, data2, ctx2, phones2)["drops.html"]
    assert "No drops this week" in h2 and '<li class="drop" ' not in h2


def test_drops_feed_has_one_entry_per_listed_drop():
    from pricechecker.site import seo
    from pricechecker.site.pages import drops
    data, phones, _env, ctx, picks = _synthetic(3, 10, 1, (5, 8, 2), (50, 60, 20))
    items = drops.this_week(data, phones)
    assert len(items) == 2
    out = seo._feeds(ctx["site"], phones, data.rows_all, data.stores_cfg, data.updated_at, items)["feeds/drops.xml"]
    assert out.count("<entry>") == 2 and "down 5% to €950 (was €1,000)" in out and "&" not in out.replace("&amp;", "").replace("&lt;", "")
    assert f'<link href="https://doorprice.app/phones/{picks[0][0]["slug"]}"/>' in out


# ---- compare page (spec §5.5) ----
def test_compare_page_is_small_and_has_no_offer_data(site_build):
    raw = (site_build / "compare.html").read_bytes()
    h = raw.decode()
    assert len(raw) <= 60_000, len(raw)
    for banned in ('"money"', "offers_json", '"pay_ok"', "compare-data"):
        assert banned not in h, banned
    assert "Other countries and payment methods need JavaScript" in h   # the shell's line
    assert "The comparison needs JavaScript. Each phone's own page works without it." in h
    assert "Pick two or three phones" in h and 'data-for' in h
    assert 'href="phones/oppo-find-x9-ultra"' in h   # without JS: links to the phone pages
    assert re.search(r'data-tax="data/v1/tax\.[0-9a-f]{10}\.json"', h)
    assert "js/compare.js?v=" in h


@live
def test_compare_page_phone_list(site_build):
    import json
    h = (site_build / "compare.html").read_text()
    raw = re.search(r'<script type="application/json" id="cmp-phones">(.*?)</script>', h, re.DOTALL)[1]
    doc = json.loads(raw.replace("<\\/", "</"))
    by = {p["id"]: p for p in doc["phones"]}
    x9 = by["oppo-find-x9-ultra"]
    assert x9["name"] == "Oppo Find X9 Ultra" and x9["brand"] == "Oppo" and sorted(x9["editions"]) == ["china", "global"]
    assert re.fullmatch(r"data/v1/phone/oppo-find-x9-ultra\.[0-9a-f]{10}\.json", x9["file"])
    assert x9["k"] == {"battery": 7050, "charging": 100}
    assert len(x9["c"]) == len(doc["rows"])
    assert by["oneplus-16"]["editions"] == ["china"]
    # the specs page's rule: a field the two brand pages give differently is split, as [china, global]
    i = [r["id"] for r in doc["rows"]].index("wired")
    assert x9["c"][i] == ["100 W SUPERVOOC, 100 W UFCS; also 55 W PPS, 18 W PD", "100 W SUPERVOOC; also 55 W PPS, 18 W PD"]
    assert by["google-pixel-11-pro"]["c"][i] is None or isinstance(by["google-pixel-11-pro"]["c"][i], str)


def test_offer_data_is_gone_from_the_phone_dicts():
    from pricechecker.site import offers
    src = Path(offers.__file__).read_text()
    assert "offers_json" not in src and '"compare": compare' not in src


def _history_site(extra=None, label=None, only=None):
    """Oppo Find X9 Ultra with hand-made history rows (updated 30 Oct 2026, so the 90-day window opens on 1 Aug):
    May first sighting, June cut, July only a rounding wobble, Sept and Oct cuts, a Global 1 TB listing in Oct.
    Returns (rendered pages, store label, slug)."""
    import dataclasses
    from datetime import datetime

    from pricechecker import fx, run, terms
    from pricechecker.site import _env, context, offers
    from pricechecker.site.pages import history as hp
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    phones = _assemble(offers, data)
    key = next(k for k, c in data.stores_cfg.items() if c.get("label") == "Wonda Mobile")
    cfg = {**data.stores_cfg, key: {**data.stores_cfg[key], "label": label}} if label else data.stores_cfg
    slug = "oppo-find-x9-ultra"
    r = lambda t, price, ed="china", mem="12/256", avail=True, store=key: {
        "time": t, "store": store, "model_id": slug, "edition": ed, "storage": mem, "price": price, "currency": "EUR", "available": avail}
    rows = [r("2026-05-14T08:00:00Z", 1100.0), r("2026-06-10T09:00:00Z", 1080.0), r("2026-07-05T09:00:00Z", 1080.2),
            r("2026-09-12T09:00:00Z", 1049.0), r("2026-10-20T09:00:00Z", 1030.0), r("2026-10-02T09:00:00Z", 1500.0, "global", "16/1024"),
            *(extra(r) if extra else [])]
    if only is not None:
        rows = only(r)
    rows.sort(key=lambda x: x["time"])
    data = dataclasses.replace(data, rows=rows, rows_all=rows, stores_cfg=cfg, updated_at=datetime(2026, 10, 30, 12, 0))
    ctx = context.page_context(data, phones)
    return hp.render(_env(), data, ctx, phones), cfg[key]["label"], slug


def test_history_main_page_is_the_last_90_days_grouped_by_day_with_month_links():
    pages, label, slug = _history_site()
    h = pages[f"history/{slug}.html"]
    assert f"{label} · China 12 + 256 · €1,080 → €1,049" in h and f"{label} · China 12 + 256 · €1,049 → €1,030" in h
    assert "Global 16 + 1 TB" in h
    assert h.index("20 Oct 2026") < h.index("12 Sep 2026")                 # days newest first
    assert "€1,100 → €1,080" not in h and "first seen at €1,100" not in h   # older than 90 days: on the monthly pages
    links = set(re.findall(rf'href="\.\./history/{slug}/(\d{{4}}-\d{{2}})"', h))
    assert links == {"2026-05", "2026-06", "2026-07"}                       # earlier months with rows; none before the first row
    assert "<polyline" in h and 'src="../static/js/history.js?v=' in h


def test_history_monthly_pages_cover_every_month_with_rows():
    pages, label, slug = _history_site()
    months = {k.rsplit("/", 1)[1][:-5] for k in pages if k.startswith(f"history/{slug}/")}
    assert months == {"2026-05", "2026-06", "2026-07", "2026-09", "2026-10"}
    jun = pages[f"history/{slug}/2026-06.html"]
    assert f"{label} · China 12 + 256 · €1,100 → €1,080" in jun and "€1,049" not in jun
    assert "June 2026" in jun and 'href="../../history/' + slug + '"' in jun


def test_history_month_navigation_stays_inside_the_phones_months():
    pages, _, slug = _history_site()
    nav = lambda m: re.findall(rf'<a [^>]*rel="(prev|next)"[^>]*href="\.\./\.\./history/{slug}/(\d{{4}}-\d{{2}})"', pages[f"history/{slug}/{m}.html"])
    nav2 = lambda m: [(rel, mo) for rel, mo in nav(m)]
    assert nav2("2026-05") == [("next", "2026-06")]                        # nothing before the first row
    assert sorted(nav2("2026-06")) == [("next", "2026-07"), ("prev", "2026-05")]
    assert sorted(nav2("2026-07")) == [("next", "2026-09"), ("prev", "2026-06")]   # August has no rows: skipped
    assert nav2("2026-10") == [("prev", "2026-09")]                        # nothing after the last row


def test_history_month_with_rows_but_no_price_changes_says_so():
    pages, _, slug = _history_site()
    jul = pages[f"history/{slug}/2026-07.html"]   # 1080 -> 1080.2: the same price to the euro
    assert "No price changes this month" in jul and " → €" not in jul
    assert f"history/{slug}/2026-08.html" not in pages


def test_history_stock_changes_and_stats_and_escaping():
    extra = lambda r: [r("2026-10-25T09:00:00Z", 1030.0, avail=False)]
    pages, _, slug = _history_site(extra=extra, label="<b>Wonda</b> & Co")
    h = pages[f"history/{slug}.html"]
    assert "&lt;b&gt;Wonda&lt;/b&gt; &amp; Co · China 12 + 256 · €1,049 → €1,030" in h and "<b>Wonda</b>" not in h
    assert " · China 12 + 256 · out of stock" in h
    assert re.search(r"Lowest(?:\s*<[^>]+>)+\s*€1,030", h) and re.search(r"Highest(?:\s*<[^>]+>)+\s*€1,080", h)
    assert re.search(r"Now(?:\s*<[^>]+>)+\s*Not in stock", h)


def test_history_page_serves_beside_its_month_folder():
    pages, _, slug = _history_site()
    assert f"history/{slug}.html" in pages and f"history/{slug}/2026-10.html" in pages


def test_history_pages_have_the_share_button_and_share_module():
    pages, _, slug = _history_site()
    for k in (f"history/{slug}.html", f"history/{slug}/2026-06.html"):
        assert '<button type="button" class="share" hidden>Share</button>' in pages[k], k
    js = Path("static/js/history.js").read_text()
    assert 'from "./share.js"' in js and 'from "./share.js"' in Path("static/js/phone.js").read_text()


def test_history_same_day_price_moves_collapse_to_one_line():
    extra = lambda r: [r("2026-10-20T10:00:00Z", 1032.0), r("2026-10-20T11:00:00Z", 1029.0),     # 1049 -> 1030 -> 1032 -> 1029
                       r("2026-10-21T08:00:00Z", 1031.0), r("2026-10-21T09:00:00Z", 1029.0)]    # +2 then back: nets to nothing
    pages, label, slug = _history_site(extra=extra)
    h = pages[f"history/{slug}.html"]
    assert f"{label} · China 12 + 256 · €1,049 → €1,029" in h
    assert h.count(" → €1,0") == 2 and "21 Oct 2026" not in h        # the 20 Oct line and the 12 Sep line; 21 Oct nets out


def test_history_stock_events_do_not_merge_into_price_runs():
    extra = lambda r: [r("2026-10-22T08:00:00Z", 1029.0, avail=False), r("2026-10-22T09:00:00Z", 1020.0)]
    pages, label, slug = _history_site(extra=extra)
    h = pages[f"history/{slug}.html"]
    assert " · out of stock" in h and f"{label} · China 12 + 256 · back in stock at €1,020" in h


def test_quiet_phone_still_shows_stats_and_chart_and_unrecorded_phone_says_so():
    only = lambda r: [r("2026-05-14T08:00:00Z", 1100.0)]      # in stock since May, nothing in the last 90 days
    pages, _, slug = _history_site(only=only)
    h = pages[f"history/{slug}.html"]
    assert re.search(r"Lowest(?:\s*<[^>]+>)+\s*€1,100", h) and re.search(r"Highest(?:\s*<[^>]+>)+\s*€1,100", h)
    assert re.search(r"Now(?:\s*<[^>]+>)+\s*€1,100", h) and "<polyline" in h
    assert "No price history recorded yet" not in h and "No price changes in the last 90 days" in h
    other = next(k for k in pages if k.count("/") == 1 and slug not in k)
    assert "No price history recorded yet" in pages[other] and "hstats" not in pages[other] and "<polyline" not in pages[other]


@live
@live_budgets
def test_built_history_pages_stay_small(site_build):
    sizes = {f: f.stat().st_size for f in [*(site_build / "history").glob("*.html"), *(site_build / "history").glob("*/*.html")]}
    # a phone's 90-day page grows with its price changes (~120-150 KB projected for the busiest phones): headroom
    assert sizes and max(sizes.values()) <= 200_000, max(sizes.items(), key=lambda kv: kv[1])


# ---- Stores pages (spec §5.7) ----

def _stores_cfg():
    from pricechecker import run
    return run.load_config()[0]


def _store_html(site_build, name):
    return (site_build / f"stores/{name}.html").read_text()


def test_stores_list_chips_count_the_eu_terms(site_build):
    from pricechecker.site.pages import stores
    cfg = _stores_cfg()
    h = (site_build / "stores.html").read_text()
    names = stores.page_names(cfg)
    want = stores.delivery_counts(cfg, names)
    # counts are recomputed here from the raw stores.yaml terms, EU region, the store plus its EU-warehouse sections
    def parts(n):
        return [cfg[n]] + [c for c in cfg.values() if c.get("part_of") == n and c.get("enabled", True)]
    ship = lambda c: ((c.get("terms") or {}).get("shipping") or {}).get("EU") or {}
    tax = sum(any(ship(c).get("duties_included") is True for c in parts(n)) for n in names)
    free = sum(any(ship(c).get("cost") == 0 for c in parts(n)) for n in names)
    fast = sum(any((ship(c).get("days") or [None, 99])[1] <= 10 for c in parts(n)) for n in names)
    # "takes PayPal" needs a published fee or discount: a store that says its methods aren't published doesn't count
    pp = sum(any(((((c.get("terms") or {}).get("payment") or {}).get("paypal") or {}).get("fee_pct")) is not None for c in parts(n)) for n in names)
    assert want == {"tax": tax, "free": free, "fast": fast, "paypal": pp} and tax and pp
    for key, label in (("tax", "Import tax paid"), ("free", "Free shipping"), ("fast", "Within 10 days"), ("paypal", "Takes PayPal")):
        assert re.search(rf'<button type="button" data-f="{key}"[^>]*>{label} <span class="n">{want[key]}</span></button>', h), label
    assert "Counts are for delivery to the EU" in h
    assert 'static/js/store.js?v=' in h
    assert h.count('<li class="st" ') == len(names)


@live
def test_stores_list_row_shows_regions_shipping_tax_fees_trust_and_checked(site_build):
    h = (site_build / "stores.html").read_text()
    tsz = re.search(r'<li class="st" data-store="tradingshenzhen".*?</li>\s*(?=<li class="st"|</ul>)', h, re.DOTALL).group(0)
    for t in ("Delivers to", "EU", "Australia", "Rest of world", "tax included", "PayPal", "4% fee", "Card", "no fee",
              "4.7", "Trustpilot", "11,216 reviews", "Terms checked", "2026-10-19"):
        assert t in tsz, t
    assert 'data-f-tax="1"' in tsz and 'data-f-paypal="1"' in tsz
    # a store that bills import tax on delivery is flagged out of the tax chip but still listed
    assert "you pay tax on delivery" in h or "tax not stated" in h


def test_stores_list_is_fully_visible_without_js(site_build):
    h = (site_build / "stores.html").read_text()
    assert '<div class="chips js-only"' in h and "hidden" not in re.search(r'<ul class="st-list".*?>', h).group(0)


def test_store_page_has_full_terms_notes_and_sources(site_build):
    h = _store_html(site_build, "tradingshenzhen")
    cfg = _stores_cfg()["tradingshenzhen"]
    for r in ("EU", "UK", "US", "Canada", "Australia", "Rest of world"):
        assert f">{r}</th>" in h
    t = cfg["terms"]
    for m in ("bank_transfer", "paypal", "card"):
        assert html.escape(t["payment"][m]["note"], quote=False) in h or html.escape(t["payment"][m]["note"]) in h
    assert html.escape(t["shipping"]["EU"]["note"], quote=False) in h or html.escape(t["shipping"]["EU"]["note"]) in h
    for w in t["watch"]:
        assert f'href="{w["url"]}"' in h
    assert "transportation-regulation" in h
    # the headed EU-warehouse table
    assert "<h3>Trading Shenzhen (EU warehouse)</h3>" in h and "Free from the EU warehouse" in h
    assert "How it is worked out" in h or "methodology" in h


@live
def test_store_page_cheapest_for_matches_default_rows(site_build):
    from pricechecker import fx, run, terms
    from pricechecker.site import context, offers
    from pricechecker.site.data_files import offer_inputs
    from pricechecker.site.view import DEFAULT, best_of, rows
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    phones = offers.assemble(data)
    for store in ("tradingshenzhen", "wonda"):
        labels = {c.get("label", k) for k, c in stores.items() if k == store or c.get("part_of") == store}
        want = set()
        for p in phones:
            rs = rows([offer_inputs(o) for o in p["offers"]], data.tax_cfg, DEFAULT)
            for e in p["editions"]:
                b = best_of(rs, e)
                if b and b["store"] in labels:
                    want.add((p["slug"], e))
        h = _store_html(site_build, store)
        got = set(re.findall(r'<li class="cf" data-slug="([^"]+)" data-e="([^"]+)"', h))
        assert got == want, store
        for slug, _ in want:
            assert f'href="../phones/{slug}"' in h


@live
def test_store_page_promos_and_terms_changed(site_build):
    import json
    h = _store_html(site_build, "tradingshenzhen")
    promos = json.loads(Path("data/promos.json").read_text())["tradingshenzhen"]["current"]
    assert "Current promotions" in h
    for line in promos:
        assert html.escape(line, quote=False) in h or html.escape(line) in h, line
    assert "Terms last changed" in h


def test_terms_changed_date_is_recorded_only_on_a_wording_change():
    from datetime import UTC, datetime

    from pricechecker import terms
    t0, t1, t2 = (datetime(2026, 10, d, tzinfo=UTC) for d in (1, 2, 3))
    s = terms.snapshot(None, ["a b c d"], t0)
    assert s["checked"].startswith("2026-10-01") and "changed" not in s
    s = terms.snapshot(s, ["a b c d"], t1)
    assert s["checked"].startswith("2026-10-02") and "changed" not in s
    s = terms.snapshot(s, ["a b c e"], t2)
    assert s["changed"].startswith("2026-10-03")
    assert terms.snapshot(s, ["a b c e"], t1)["changed"].startswith("2026-10-03")


def test_store_pages_escape_store_text():
    from pricechecker import fx, run, terms
    from pricechecker.site import _env, context, offers
    from pricechecker.site.pages import stores
    cfg, catalog = run.load_config()
    cfg["wonda"] = {**cfg["wonda"], "label": "W<script>x</script>"}
    data = context.load(catalog, cfg, fx.cached(), terms.saved_status())
    phones = offers.assemble(data)
    out = stores.render(_env(), data, context.page_context(data, phones), phones)
    assert "<script>x</script>" not in out["stores.html"] + out["stores/wonda.html"]
    assert "W&lt;script&gt;x&lt;/script&gt;" in out["stores/wonda.html"]


# ---- Task 12: links, sitemap, old front end gone ----

def _href_targets(html_text):
    return re.findall(r'<a\b[^>]*?\shref="([^"]*)"', html_text)


def _resolves(site_build, page, href):
    import os
    from urllib.parse import unquote, urlsplit
    u = urlsplit(html.unescape(href))
    if u.scheme or u.netloc or not u.path:
        return True   # external (https:, mailto:, tel:, //host) or fragment/query only
    rel = unquote(u.path)
    if rel.startswith("mock/") or "/mock/" in rel:
        return True
    t = Path(os.path.normpath((site_build / rel.lstrip("/")) if rel.startswith("/") else (page.parent / rel)))
    if rel.endswith("/") or t == site_build:
        return (t / "index.html").exists()
    return t.with_name(t.name + ".html").exists() or (t / "index.html").exists() or t.is_file()


@live
def test_internal_links_resolve(site_build):
    bad = []
    for f in site_build.rglob("*.html"):
        if "mock" in f.relative_to(site_build).parts:
            continue
        for href in _href_targets(f.read_text()):
            if not _resolves(site_build, f, href):
                bad.append((str(f.relative_to(site_build)), href))
    assert not bad, bad[:20]


def test_headings_never_skip_a_level(site_build):
    """Lighthouse (accessibility) flags h1 -> h3 jumps: on phone pages the receipt heading followed the h1 directly."""
    bad = []
    for f in [site_build / "index.html", site_build / "compare.html", *sorted((site_build / "phones").glob("*.html"))]:
        prev = 0
        for lv in (int(x) for x in re.findall(r"<h([1-6])\b", f.read_text())):
            if prev and lv > prev + 1:
                bad.append((f.name, f"h{prev} -> h{lv}"))
            prev = lv
    assert not bad, bad[:10]


@live
def test_header_search_form_on_every_page_resolves_to_home(site_build):
    """One search field in every page's header; its form submits to the home page from wherever the page is served
    (Pages drops .html; /404.html is served at any path)."""
    from urllib.parse import urljoin, urlsplit
    bad = []
    for f in site_build.rglob("*.html"):
        rel = f.relative_to(site_build).as_posix()
        if rel.startswith("mock/"):
            continue
        h = f.read_text()
        served = "https://x.test/" + ("" if rel == "index.html" else rel.removesuffix(".html"))
        if rel == "404.html":
            served = "https://x.test/some/missing/page"
        forms = re.findall(r'<form class="hsearch" role="search" action="([^"]*)" method="get">', h)
        if len(forms) != 1 or 'id="hq" name="q"' not in h or urlsplit(urljoin(served, html.unescape(forms[0]))).path != "/":
            bad.append(rel)
    assert not bad, bad[:10]
    assert 'id="q"' not in (site_build / "index.html").read_text()   # the hero search box is gone


def _store_hosts():
    """Every host a store link can have: stores.yaml base_url / sitemap_url / affiliate templates, and the url and link
    of every offer in the saved data (so a store with no base_url, or an affiliate redirect, is covered too)."""
    import json
    from urllib.parse import urlsplit

    import yaml

    host = lambda u: (urlsplit(u).hostname or "").removeprefix("www.")
    cfg = yaml.safe_load((ROOT / "config/stores.yaml").read_text())["stores"]
    hosts = set()
    for c in cfg.values():
        for k in ("base_url", "sitemap_url"):
            if c.get(k):
                hosts.add(host(c[k]))
        for w in (c.get("terms") or {}).get("watch") or []:   # the store's own terms pages we link to
            hosts.add(host(w["url"]))
        tpl = c.get("affiliate_link") or ""
        if tpl.startswith("http"):
            hosts.add(host(re.sub(r"\{[a-z_]+\}", "x", tpl)))
    latest = json.loads((ROOT / "data/latest.json").read_text())
    for st in latest["stores"].values():
        for o in st.get("offers", []):
            for k in ("url", "link"):
                if o.get(k):
                    hosts.add(host(o[k]))
    hosts.discard("")
    return hosts


@live
def test_store_links_are_sponsored(site_build):
    hosts = _store_hosts()
    assert "ww.etoren.com" in hosts and "wondamobile.com" in hosts
    seen = 0
    for f in site_build.rglob("*.html"):
        for m in re.finditer(r'<a\b([^>]*)>', f.read_text()):
            attrs = m.group(1)
            h = re.search(r'\shref="(https?://[^"/]+)', attrs)
            if not h or h.group(1).split("//")[1].removeprefix("www.") not in hosts:
                continue
            seen += 1
            rel = re.search(r'\srel="([^"]*)"', attrs)
            assert rel and {"sponsored", "nofollow", "noopener"} <= set(rel.group(1).split()), (f, attrs)
    assert seen


def test_sitemap_lists_new_pages(site_build):
    sm = (site_build / "sitemap.xml").read_text()
    locs = set(re.findall(r"<loc>https://doorprice.app/([^<]*)</loc>", sm))
    assert "drops" in locs
    specs_pages = {str(p.relative_to(site_build).with_suffix("")) for p in site_build.glob("phones/*/specs.html")}
    months = {str(p.relative_to(site_build).with_suffix("")) for p in site_build.glob("history/*/*.html")}
    assert specs_pages and months
    assert specs_pages <= locs
    assert not months & locs   # monthly archives stay on the site (linked) but out of the sitemap (2026-11-10)
    assert "404" not in locs
    # <lastmod>: the phone and history pages carry their phone's last price change; about/privacy/specs carry none
    entries = dict(re.findall(r"<url><loc>https://doorprice.app/([^<]*)</loc>(?:<lastmod>([^<]+)</lastmod>)?</url>", sm))
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", v) for v in entries.values() if v)
    assert entries["about"] == "" and entries["privacy"] == "" and all(entries[p] == "" for p in specs_pages)
    assert sum(1 for k, v in entries.items() if k.startswith("phones/") and "/" not in k[7:] and v) >= 50


def test_sitemap_lastmod_is_the_last_price_change():
    from pricechecker.site import seo
    phones = [{"id": "a", "slug": "a"}, {"id": "b", "slug": "b"}, {"id": "c", "slug": "c"}]
    rows = [{"time": "2026-11-01T00:00:00Z", "store": "shop", "model_id": "a"},
            {"time": "2026-11-05T10:00:00Z", "store": "shop_eu", "model_id": "a"},   # EU warehouse: on the shop's page
            {"time": "2026-11-03T08:00:00Z", "store": "other", "model_id": "b"},
            {"time": "2026-11-09T09:00:00Z", "store": "other", "model_id": "untracked"}]   # not a phone we list: ignored
    lm = seo.lastmods(rows, phones, {"shop": {}, "shop_eu": {"part_of": "shop"}, "other": {}})
    assert lm["phones/a"] == lm["history/a"] == "2026-11-05T10:00:00Z" and lm["phones/b"] == "2026-11-03T08:00:00Z"
    assert "phones/c" not in lm   # no recorded change yet: no date rather than a made-up one
    assert lm[""] == lm["drops"] == lm["compare"] == lm["stores"] == "2026-11-05T10:00:00Z"
    assert lm["stores/shop"] == "2026-11-05T10:00:00Z" and lm["stores/other"] == "2026-11-03T08:00:00Z"
    sm = seo._seo_files({"domain_live": True, "base_url": "https://x.test"}, phones, ["shop", "other"],
                        ["phones/a/specs", "history/a/2026-11"], lm)["sitemap.xml"]
    assert "<url><loc>https://x.test/phones/a</loc><lastmod>2026-11-05T10:00:00Z</lastmod></url>" in sm
    assert "<url><loc>https://x.test/phones/c</loc></url>" in sm and "<url><loc>https://x.test/about</loc></url>" in sm
    assert "phones/a/specs</loc></url>" in sm and "history/a/2026-11" not in sm


def test_testing_build_is_still_noindex(tmp_path):
    from pricechecker.site import seo
    assert seo._seo_files({"testing": True, "domain_live": True, "base_url": "https://x"}, [], [], ["phones/a/specs"]) == \
        {"robots.txt": "User-agent: *\nDisallow: /\n"}


def test_no_old_front_end(site_build):
    assert not (site_build / "static/app.js").exists()
    assert not (site_build / "static/style.css").exists()
    assert "app.js" not in (site_build / "_headers").read_text() and "style.css" not in (site_build / "_headers").read_text()
    for f in site_build.rglob("*.html"):
        t = f.read_text()
        assert "app.js" not in t and "style.css" not in t, f


def test_methodology_explains_how_a_drop_is_counted(site_build):
    from pricechecker import derive, telegram
    t = (site_build / "methodology.html").read_text()
    assert "How a drop is counted" in t
    assert f"{derive.MIN_PCT}%" in t and f"€{derive.MIN_EUR}" in t
    assert f"{telegram.MIN_PCT * 100:g}%" in t and f"€{telegram.MIN_EUR}" in t
    assert "Telegram" in t


def test_explainer_covers_the_eu_band_check(site_build):
    p = next(site_build.glob("phones/*.html")).read_text()
    assert "EU band check" in p and "own spec page" in p


def test_privacy_says_fonts_are_self_hosted(site_build):
    t = (site_build / "privacy.html").read_text()
    assert "Google Fonts" not in t and "fonts.g" not in t
    assert "Cloudflare Web Analytics" in t


def test_store_hosts_cover_every_store_in_stores_yaml():
    from urllib.parse import urlsplit

    import yaml
    hosts = _store_hosts()
    for name, c in yaml.safe_load((ROOT / "config/stores.yaml").read_text())["stores"].items():
        url = c.get("base_url") or c.get("sitemap_url")
        if url:
            assert (urlsplit(url).hostname or "").removeprefix("www.") in hosts, name


# ---- made-up prices: what the live tests above check on the saved prices, on data that never changes (not live) ----

def _made_up(listings, rows=(), failed=()):
    """The site's config with the saved prices swapped for `listings` [(store, phone id, edition, storage, EUR price,
    available)], all checked at the saved `updated` time, and `rows` as the price history; `failed` names stores whose
    latest check failed: (data, phones, env, ctx)."""
    import dataclasses

    from pricechecker import fx, run, terms
    from pricechecker.site import _env, context, offers
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    at = data.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    host = {"wonda": "https://wondamobile.com", "giztop": "https://www.giztop.com", "mobilemarvel": "https://www.themobilemarvel.com",
            "tradingshenzhen": "https://tradingshenzhen.com", "tradingshenzhen_eu": "https://tradingshenzhen.com"}
    live_stores = {}
    for store, pid, ed, mem, eur, avail in listings:
        st = live_stores.setdefault(store, {"ok": store not in failed, "checked": at, "offers": []})
        st["offers"].append({"store": store, "model_id": pid, "edition": ed, "storage": mem, "title": f"{pid} {mem}",
                             "price": eur, "currency": "EUR", "available": avail, "url": f"{host[store]}/products/{pid}-{ed}",
                             "prices": {"EUR": eur}})
    latest = {"updated": at, "stores": live_stores}
    data = dataclasses.replace(data, latest=latest, live_stores=live_stores, rows=list(rows), rows_all=list(rows), terms_status={})
    phones = _assemble(offers, data)
    return data, phones, _env(), context.page_context(data, phones)


def test_phone_page_sections_on_made_up_prices():
    from pricechecker.site.pages import phone
    pid = "oppo-find-x9-ultra"
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True), ("giztop", pid, "china", "12/256", 1020.0, True),
                                       ("wonda", pid, "global", "12/256", 1300.0, True), ("giztop", pid, "global", "16/512", 1500.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    assert h.count('data-block="price_box"') == 2
    for blk in ("mem_chips", "verdict", "receipt", "store_list", "ledger", "buy_bar"):
        assert f'data-block="{blk}"' in h, blk
    assert "Oppo Find X9 Ultra price: <em>China vs Global</em>" in h and "Compare every offer (" in h


def test_spec_line_reads_one_value_per_part():
    from pricechecker.site.common import spec_line
    assert spec_line({"chip": "Dimensity 9600M", "screen": 6.59, "battery": "8,000 mAh / 7,150 mAh (EU)", "charging": "80 W"}) == "Dimensity 9600M · 6.59″ · up to 8,000 mAh"
    assert spec_line({"chip": "X", "battery": "7,200 mAh (China) / 7,100 mAh (Global) / 6,270 mAh (EU)"}) == "X · up to 7,200 mAh"
    assert spec_line({"screen": 6.82, "battery": "large"}) == "6.82″ · large"
    assert spec_line(None) == ""


def _top(h):
    return h[h.index("<h1"):h.index('id="duel"')]


def test_phone_top_has_product_card_and_checked_line(tmp_path, monkeypatch):
    from pricechecker.site.pages import phone
    pid = "oppo-find-x9-ultra"
    _photos(monkeypatch, tmp_path, pid)
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True), ("giztop", pid, "global", "12/256", 1300.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    top = _top(h)
    assert re.search(rf'<img src="\.\./static/phones/{pid}-m\.webp\?v=[0-9a-f]{{10}}" width="\d+" height="\d+" alt="Oppo Find X9 Ultra" loading="eager" decoding="async">', top)
    assert "Photo: Oppo" in top and "Snapdragon 8 Elite Gen 5" in top and f'href="{pid}/specs">All specs</a>' in top and 'href="#carrier">Check your network</a>' in top
    assert re.search(r"2 stores checked <time datetime=\"[^\"]+\" data-ago>", top)
    assert 'data-for="lower">delivered to the EU by card</span> · we don\'t sell phones' in top
    assert 'class="for"' not in top


def test_phone_top_wraps_kicker_h1_and_card_for_the_desktop_grid(tmp_path, monkeypatch):
    from pricechecker.site.pages import phone
    pid = "oppo-find-x9-ultra"
    _photos(monkeypatch, tmp_path, pid)
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    m = re.search(
        r'<div class="ptop">\s*<p class="kicker">.*?</p>\s*<h1>.*?</h1>\s*<div class="pcard">.*?</div>\s*</div>\s*<p class="checked">',
        h, re.DOTALL)
    assert m and "<figure" in m.group(0) and h.count('class="ptop"') == 1   # the checked line stays under the block


def test_phone_card_without_photo_or_specs_or_bands(monkeypatch):
    from pricechecker.site import common
    from pricechecker.site.pages import phone
    monkeypatch.setattr(common, "PHOTOS_DIR", Path("/nonexistent"))
    pid = "oppo-find-x9-ultra"
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True)])
    top = _top(phone.render(env, data, ctx, phones)[f"phones/{pid}.html"])
    assert 'class="pcard"' in top and "<img" not in top   # key specs only
    q = next(x for x in phones if x["id"] == pid)
    q["specs"] = []
    assert 'class="pcard"' not in _top(phone.render(env, data, ctx, phones)[f"phones/{pid}.html"])
    data.spec_sheets[pid] = {**data.spec_sheets[pid], "bands": {}}
    q["specs"] = [("Chip", "X")]
    assert "Check your network" not in _top(phone.render(env, data, ctx, phones)[f"phones/{pid}.html"])


def test_phone_card_with_a_photo_and_no_key_specs_has_no_empty_spec_list(tmp_path, monkeypatch):
    from pricechecker.site.pages import phone
    pid = "oppo-find-x9-ultra"
    _photos(monkeypatch, tmp_path, pid)
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True)])
    next(x for x in phones if x["id"] == pid)["specs"] = []
    top = _top(phone.render(env, data, ctx, phones)[f"phones/{pid}.html"])
    assert 'class="pcard"' in top and f"static/phones/{pid}-m.webp" in top   # the photo still has its card
    assert "pspecs" not in top and 'href="#carrier">Check your network</a>' in top


def test_checked_line_counts_failed_stores_and_eu_warehouse_once():
    from pricechecker.site.pages import phone
    pid = "oppo-find-x9-ultra"
    listings = [("tradingshenzhen", pid, "china", "12/256", 1000.0, True), ("tradingshenzhen_eu", pid, "global", "12/256", 1300.0, True),
                ("wonda", pid, "china", "12/256", 1010.0, True)]
    data, phones, env, ctx = _made_up(listings, failed=("wonda",))
    p = next(x for x in phones if x["id"] == pid)
    assert phone.stores_checked(p, data.stores_cfg) == (1, 2)
    assert re.search(r"1 of 2 stores checked <time", _top(phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]))
    data, phones, env, ctx = _made_up(listings)
    assert phone.stores_checked(next(x for x in phones if x["id"] == pid), data.stores_cfg) == (2, 2)


def test_photo_of_hashes_files_and_needs_both(tmp_path):
    from pricechecker.site.common import photo_of
    sheet = {"photo": {"url": "https://img.example/a.png", "credit": "Oppo Global"}}
    assert photo_of("a", sheet, "Oppo", tmp_path) is None
    (tmp_path / "a-s.webp").write_bytes(b"s")
    assert photo_of("a", sheet, "Oppo", tmp_path) is None
    (tmp_path / "a-m.webp").write_bytes(b"m")
    got = photo_of("a", sheet, "Oppo", tmp_path)
    assert got["credit"] == "Oppo Global" and re.fullmatch(r"static/phones/a-m\.webp\?v=[0-9a-f]{10}", got["m"])
    assert photo_of("a", {"photo": {"url": "https://img.example/a.png"}}, "Oppo", tmp_path)["credit"] == "Oppo"


def test_photo_of_needs_a_photo_in_the_sheet(tmp_path):
    """`photo:` taken out of a sheet (a brand asked for its photo to go) takes the photo off the site, even before
    photos.py has deleted the files."""
    from pricechecker.site.common import photo_of
    for k in "sm":
        (tmp_path / f"a-{k}.webp").write_bytes(k.encode())
    for sheet in (None, {}, {"photo": None}, {"photo": {}}, {"photo": {"url": ""}}, {"photo": {"credit": "Oppo Global"}}):
        assert photo_of("a", sheet, "Oppo", tmp_path) is None, sheet


def test_photo_cache_rule_and_about_paragraph():
    from pricechecker.site import headers
    assert "/static/phones/*\n  Cache-Control: public, max-age=2592000" in headers.CACHE
    from pricechecker.site.pages import static
    data, phones, env, ctx = _made_up([("wonda", "oppo-find-x9-ultra", "china", "12/256", 1000.0, True)])
    about = html.unescape(static.render(env, data, ctx, phones)["about.html"])
    assert "Phone photos are each brand's own product images, credited on each phone's page. A brand that would like one removed can write to" in about


def test_china_only_phone_on_made_up_prices():
    from pricechecker.site.pages import phone
    pid = "oneplus-16"
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 900.0, True), ("giztop", pid, "china", "16/512", 1000.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    assert h.count('data-block="price_box"') == 1
    assert "No Global version so far: OnePlus sells this phone in China only" in h and "OnePlus 16 price: <em>China version</em>" in h


def _memory_first(h):
    """The phone page's memory-first structure: the chips, then the boxes, then the one details panel."""
    assert 'data-block="gap_line"' not in h and 'id="s-gap"' not in h
    assert h.count('id="pick-panel"') == 1
    assert h.index('id="s-mems"') < h.index('id="duel"') < h.index('id="s-verdict"') < h.index('id="s-receipt"')


def test_phone_page_is_memory_first_on_made_up_prices():
    from pricechecker.site.pages import phone
    pid = "oppo-find-x9-ultra"
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True), ("giztop", pid, "china", "16/512", 1100.0, True),
                                       ("wonda", pid, "global", "12/256", 1300.0, True), ("giztop", pid, "global", "16/512", 1500.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    _memory_first(h)
    assert 'id="duel" role="group" aria-label="Versions"' in h and 'class="pick"' not in h
    assert h.count('data-block="mem_chips"') == 1 and h.count('class="pickbtn"') == 2 and 'role="tab' not in h
    assert 'data-mem="12/256"' in h and 'data-ed="china"' in h
    assert len(h.encode()) <= 60_000


def test_default_pick_total_is_the_title_price_on_made_up_prices():
    """The panel opens on the cheapest current row of both versions: its total is the <title> price."""
    from pricechecker.site.pages import phone
    ids = ("oppo-find-x9-ultra", "oneplus-16", "google-pixel-11")
    data, phones, env, ctx = _made_up([("wonda", ids[0], "china", "16/512", 1100.0, True), ("giztop", ids[0], "global", "12/256", 1000.0, True),
                                       ("wonda", ids[0], "global", "16/512", 1200.0, True),
                                       ("wonda", ids[1], "china", "12/256", 900.0, True), ("giztop", ids[1], "china", "16/512", 800.0, True),
                                       ("wonda", ids[2], "global", "12/256", 700.0, True), ("giztop", ids[2], "china", "12/256", 760.0, True)])
    out = phone.render(env, data, ctx, phones)
    for pid in ids:
        h = out[f"phones/{pid}.html"]
        _memory_first(h)
        title = re.search(r"<title>.*?: from €(\d[\d,]*\d|\d)", h)[1]
        panel = h[h.index('id="pick-panel"'):]
        total = re.search(r'<div class="total num">[≈]?€([\d,]+)', panel)[1]
        assert total == title, pid


def test_price_boxes_carry_the_network_line_for_the_default_settings():
    from pricechecker.site.pages import phone
    pid = "oppo-find-x10"   # bands published for both versions
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 800.0, True), ("giztop", pid, "global", "12/256", 1150.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    duel = h[h.index('id="duel"'):h.index('id="s-verdict"')]
    assert duel.count('<p class="net pick">Networks: <button type="button" data-prefs>choose your country</button></p>') == 2
    assert duel.index('class="net') > duel.index('</button>')   # after the box's select button (its price and settled mark)


def test_price_boxes_network_line_when_the_bands_are_not_published():
    from pricechecker import specs
    from pricechecker.site.pages import phone
    pid = "honor-magic-8-pro"
    assert specs.load()[pid].get("bands") is None
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 800.0, True), ("giztop", pid, "global", "12/256", 1150.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    duel = h[h.index('id="duel"'):h.index('id="s-verdict"')]
    assert duel.count('data-block="price_box"') == 2
    assert duel.count('<p class="net muted">Bands not published for this version</p>') == 2 and "data-prefs" not in duel


def test_phone_page_without_listed_memory_has_a_panel_and_no_chips():
    from pricechecker.site.pages import phone
    pid = "oneplus-16"
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "base", 900.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    assert h.count('id="pick-panel"') == 1 and 'data-block="mem_chips"' not in h and 'data-mem="base"' in h


def _home_row(h, pid):
    i = h.index(f'<li class="pair" data-block="home_row" data-id="{pid}">')
    return h[i:h.index("</li>", i)]


def _photos(monkeypatch, tmp_path, *pids):
    """Processed photo files for `pids` (only theirs) in tmp_path, and a photo entry in their spec sheets: a phone shows a
    photo when it has both (common.photo_of), whatever the real config/specs and static/phones hold."""
    from PIL import Image

    from pricechecker import photos, specs
    from pricechecker.site import common
    for pid in pids:
        for k, (w, h) in photos.SIZES.items():
            Image.new("RGBA", (w, h)).save(tmp_path / f"{pid}-{k}.webp")
    monkeypatch.setattr(common, "PHOTOS_DIR", tmp_path)
    real = specs.load
    monkeypatch.setattr(specs, "load", lambda *a, **kw: {i: {**s, "photo": {"url": f"https://img.example/{i}.png"}} if i in pids else s
                                                          for i, s in real(*a, **kw).items()})


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_more_from_brand_rows_are_home_rows_of_their_own_meta(tmp_path, monkeypatch):
    """"More from {brand}" on a phone page: each row is drawn from the phone's home meta (row_meta: its versions, photo
    and key specs), the same object data-more hands phone.js, so both versions' prices show (they read "No China
    version" and "No Global version" when the page passed the whole phone dict), a China-only phone has one "No Global
    version" cell, and a phone with a photo has it. blocks.js draws the same row from data-more."""
    from pricechecker.site import data_files
    from pricechecker.site.pages import phone
    pid, two, china = "oppo-find-x9-ultra", "oppo-find-x10", "oppo-find-x9s-pro"
    _photos(monkeypatch, tmp_path, two)
    data, phones, env, ctx = _made_up([("wonda", pid, "china", "12/256", 1000.0, True), ("giztop", pid, "global", "12/256", 1300.0, True),
                                       ("wonda", two, "china", "12/256", 800.0, True), ("giztop", two, "global", "12/256", 1150.0, True),
                                       ("wonda", china, "china", "12/256", 900.0, True)])
    h = phone.render(env, data, ctx, phones)[f"phones/{pid}.html"]
    more = h[h.index('<ul class="pairs" id="more"'):]
    more = more[:more.index("</ul>")]
    meta = {m["id"]: m for m in json.loads(re.search(r"data-more='([^']*)'", more)[1])}
    assert list(meta) == [two, "oppo-find-x10-pro-max", china]   # the brand's three newest other phones
    r2, rc = _home_row(more, two), _home_row(more, china)
    assert r2.count('<b class="num">') == 2 and "absent" not in r2 and "at Wonda Mobile" in r2 and "at Giztop" in r2
    assert rc.count('<b class="num">') == 1 and rc.count("absent") == 1 and '<span class="p none absent">No Global version</span>' in rc
    assert re.search(rf'<img class="ph" src="\.\./static/phones/{two}-s\.webp\?v=[0-9a-f]{{10}}" width="58" height="72" alt=""', r2)
    assert "<img" not in rc and '<span class="sp">' in r2
    # data-more: the meta the server drew each row from, plus the phone's data file (the build's; none here)
    assert meta[two]["eds"] == ["global", "china"] and meta[china]["eds"] == ["china"] and "ph" not in meta[china]
    assert meta[two]["ph"] in r2 and meta[two]["sp"] in html.unescape(r2)
    assert all(set(m) == {"id", "name", "announced", "sp", "eds", "file"} | ({"ph"} if i == two else set()) for i, m in meta.items())
    # phone.js paintMore: B.homeRow(meta, rows of the phone's file, s, labels, "../") draws the same row
    p2 = next(q for q in phones if q["id"] == two)
    (tmp_path / "two.json").write_text(json.dumps({"offers": [data_files.offer_inputs(o) for o in p2["offers"]]}))
    (tmp_path / "tax.json").write_text(json.dumps(data.tax_cfg))
    r = subprocess.run(["node", str(ROOT / "tests/js/render_blocks.mjs"), "--phone", str(tmp_path / "two.json"), "--tax", str(tmp_path / "tax.json"),
                        "--edition", "china", "--storage", "12/256", "--labels", json.dumps(p2["ed_label"]), "--meta", json.dumps(meta[two]),
                        "--root", "../"], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["home_row"] == r2 + "</li>"


def test_home_rows_show_photo_specs_store_and_absent_version(tmp_path, monkeypatch):
    from pricechecker.site.pages import home
    _photos(monkeypatch, tmp_path, "oneplus-16")
    data, phones, env, ctx = _made_up([("wonda", "oneplus-16", "china", "12/256", 900.0, True), ("giztop", "oneplus-16", "china", "16/512", 1000.0, True)])
    row = _home_row(home.render(env, data, ctx, phones)["index.html"], "oneplus-16")
    assert re.search(r'<img class="ph" src="static/phones/oneplus-16-s\.webp\?v=[0-9a-f]{10}" width="58" height="72" alt="" loading="lazy"', row)
    assert "at Wonda Mobile" in row and "No Global version" in row and "2 stores compared" in row
    assert '<span class="sp">' in row


def test_home_drop_mark_and_teaser_on_made_up_drops():
    """One real drop (5% / EUR 50) and one too small (2% / EUR 20): the teaser counts one, only that phone's row is marked."""
    import json

    from pricechecker.site.pages import home
    data, phones, env, ctx, picks = _synthetic(2, 10, 1, (5, 2), (50, 20))
    h = home.render(env, data, ctx, phones)["index.html"]
    assert re.search(r'<a class="teaser" href="drops">\s*<b>↓ 1 price drop this week</b>', h)
    meta = json.loads(re.search(r'id="home-meta">(.*?)</script>', h, re.DOTALL).group(1))
    assert [m["id"] for m in meta if m.get("drop")] == [picks[0][0]["id"]]
    assert _home_row(h, picks[0][0]["id"]).endswith('</a><span class="marks"><span class="mark drop">↓ this week</span></span>')
    assert "mark" not in _home_row(h, picks[1][0]["id"])
    assert h.count('class="mark drop"') == 1


def test_home_in_a_week_without_drops_has_no_teaser_and_no_marks():
    from pricechecker.site.pages import drops, home
    data, phones, env, ctx, _ = _synthetic(2, 40, 14, (10, 10), (100, 100))   # drops 14 days ago: none this week
    h = home.render(env, data, ctx, phones)["index.html"]
    assert 'class="teaser"' not in h and 'class="mark drop"' not in h and "price drops this week" not in h
    d = drops.render(env, data, ctx, phones)["drops.html"]
    assert "No drops this week" in d and h.count('data-block="home_row"') > 50


def test_settings_button_name_starts_with_its_visible_text(site_build):
    """WCAG 2.5.3: no aria-label; the visible "EU · Card · €" (which settings.js repaints) plus an sr-only suffix."""
    for f in (site_build / "index.html", next(site_build.glob("phones/*.html"))):
        h = f.read_text()
        b = re.search(r'<button class="prefs"[^>]*>.*?</button>', h, re.DOTALL).group(0)
        assert "aria-label" not in b, b
        assert b.endswith('<span data-prefs-label>EU · Card · €</span><span class="sr-only">, delivery settings, change</span></button>'), b


def test_head_preloads_the_first_view_fonts(site_build):
    h = (site_build / "index.html").read_text()
    preloads = re.findall(r'<link rel="preload" href="([^"]+)" as="font"', h)
    assert preloads == ["static/fonts/albert-sans-400.woff2", "static/fonts/schibsted-grotesk-800.woff2"]
    css = (site_build / "static/d.css").read_text()
    assert 'font-weight: 800' in css and re.search(r"h1 \{ font: 800 [^;]*var\(--serif\)", css)
    assert all((site_build / p).exists() for p in preloads) and (site_build / "static/fonts/plex-sans-400.woff2").exists()


def test_watch_note_promises_only_the_mark_and_filter(site_build):
    h = next(site_build.glob("phones/*.html")).read_text()
    assert "Watched phones get a mark and a filter on the phone list (saved on this device)." in h
    assert "since your last visit" not in h


# ---- security headers (build/_headers) ----

def _inline_scripts(h):
    """The bodies of the page's inline scripts that run (no src, not a JSON data block)."""
    return [body for attrs, body in re.findall(r"<script\b([^>]*)>(.*?)</script>", h, re.DOTALL)
            if "src=" not in attrs and not re.search(r'type="application/(ld\+)?json"', attrs)]


def test_headers_send_the_security_headers_on_every_page(site_build):
    h = (site_build / "_headers").read_text()
    block = h[h.index("/*\n"):h.index("\n/static/")]
    for line in ("Strict-Transport-Security: max-age=31536000; includeSubDomains", "X-Content-Type-Options: nosniff",
                 "Referrer-Policy: strict-origin-when-cross-origin", "X-Frame-Options: DENY",
                 "Permissions-Policy: camera=(), microphone=(), geolocation=()"):
        assert f"\n  {line}" in block, line
    csp = re.search(r"\n  Content-Security-Policy: ([^\n]+)", block).group(1)   # enforced since 2026-11-09
    assert "Report-Only" not in block
    for d in ("default-src 'self'", "style-src 'self'", "style-src-attr 'unsafe-inline'", "form-action 'self'",
              "frame-ancestors 'none'", "object-src 'none'", "https://static.cloudflareinsights.com",
              "connect-src 'self' https://cloudflareinsights.com", "upgrade-insecure-requests"):
        assert d in csp, d
    assert "unsafe-inline" not in csp.split("script-src", 1)[1].split(";", 1)[0]


def test_csp_hashes_cover_every_inline_script(site_build):
    import base64
    import hashlib
    csp = re.search(r"Content-Security-Policy: ([^\n]+)", (site_build / "_headers").read_text()).group(1)
    allowed = set(re.findall(r"'(sha256-[A-Za-z0-9+/=]+)'", csp))
    seen = set()
    for f in site_build.rglob("*.html"):
        for body in _inline_scripts(f.read_text()):
            seen.add("sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode())
    assert seen and seen <= allowed, seen - allowed   # the production build has the pages.dev redirect inline
    assert any("pages\\.dev" in b for b in _inline_scripts((site_build / "index.html").read_text()))


def test_headers_hash_follows_the_script_text():
    from pricechecker.site import headers
    a = headers.inline_script_hashes(['<script>x()</script><script type="application/ld+json">{}</script><script src="a.js"></script>'])
    b = headers.inline_script_hashes(["<script>y()</script>"])
    assert len(a) == 1 and a != b and a[0] in headers.csp(a)


def test_privacy_says_single_reports_are_public_and_watch_keeps_no_price(site_build):
    t = " ".join((site_build / "privacy.html").read_text().split())
    assert "reviewed in a public GitHub issue and saved in our public GitHub repository" in t
    assert "not single reports" not in t and "the price you last saw" not in t


# ---- price trend on the phone page (synthetic phone: no saved prices behind the trend) ----
def _trend_site(sold_out=False):
    import copy
    import dataclasses
    import json

    from pricechecker import fx, run, terms
    from pricechecker.site import _env, context, offers
    from pricechecker.site.pages import phone
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    p = copy.deepcopy(offers.assemble(data)[0])
    fixture = json.loads((ROOT / "tests/fixtures/states_phone.json").read_text())
    shop = next(o for o in fixture["offers"] if o["store_label"] == "Settled Shop")
    p["editions"] = ["china"]
    p["offers"] = [{**shop, "store": "settled", "currency": "EUR", "price": 1000.0, "available": not sold_out}]
    rows = [{"time": f"{d}T08:00:00Z", "store": "settled", "model_id": p["id"], "edition": "china", "storage": "12/256", "price": v,
             "currency": "EUR", "available": True} for d, v in [(f"2026-10-{n:02d}", 1050.0 if n < 20 else 1000.0) for n in range(1, 25)]]
    data = dataclasses.replace(data, rows=rows, rows_all=rows)
    ctx = context.page_context(data, [p])
    ctx["updated"] = "2026-10-30T12:00:00Z"
    return phone.render(_env(), data, ctx, [p])[f'phones/{p["slug"]}.html'], p


def test_phone_page_trend_follows_the_verdict_for_the_default_pick():
    h, p = _trend_site()
    assert h.index('id="s-verdict"') < h.index('id="s-trend"') < h.index('id="s-receipt"')
    block = h[h.index('id="s-trend"'):h.index('id="s-receipt"')]
    assert 'data-block="price_trend"' in block
    assert "Lowest price in 30 days" in block
    assert f'href="../history/{p["slug"]}"' in block and "Full price history" in block
    assert "Down 5% since first listed (1 Oct)" in block   # 1000 vs 1050 on the first day
    assert len(h.encode()) <= 60_000


def test_phone_page_trend_is_empty_without_a_current_price():
    h, _ = _trend_site(sold_out=True)
    assert '<div id="s-trend" data-ed="china"></div>' in h and 'data-block="price_trend"' not in h


# --- unknown (null) band lists ---

def test_unknown_nr_is_said_not_counted_on_the_phone_and_specs_pages(tmp_path, monkeypatch):
    """A synthetic Mate X7 sheet with fields and nr null, built into a temp site."""
    from copy import deepcopy

    from pricechecker import fx, run, site, terms
    from pricechecker import specs as specs_cfg
    from pricechecker.site.pages import phone as ph
    sheets = deepcopy(specs_cfg.load())
    s = sheets["huawei-mate-x7"]
    assert s["bands"]["global"]["nr"] is None
    s["groups"] = {"display": {"size": "8.0 in"}}
    s["sources"]["global"] = {"url": "https://consumer.huawei.com/en/phones/mate-x7/specs/", "checked": "2026-11-01"}
    s["bands"]["china"] = deepcopy(s["bands"]["global"])
    s["sources"]["china"] = {"url": "https://consumer.huawei.com/cn/phones/mate-x7/specs/", "checked": "2026-11-01"}
    b = ph._bands(s, "global")
    assert b["unknown"] == "5G bands not published" and b["known"] == "4G"
    monkeypatch.setattr(specs_cfg, "load", lambda *a, **k: sheets)
    out = tmp_path / "build"
    stores, catalog = run.load_config()
    monkeypatch.setattr(site, "OUT", out)
    site.build(catalog, stores, fx.cached(), terms.saved_status())
    sp = (out / "phones/huawei-mate-x7/specs.html").read_text()
    assert "not published" in sp
    assert "Has all the main EU 4G bands; 5G bands not published" in sp
    assert "Has all the main EU bands<" not in sp
    pg = (out / "phones/huawei-mate-x7.html").read_text()
    assert "5G bands not published" in pg
    assert "<b>Has the main EU 4G bands; 5G bands not published.</b>" in pg


def test_phone_bands_helpers_with_a_null_list():
    import yaml

    from pricechecker.site.pages import phone as ph
    from pricechecker.site.pages import specs as sp
    s = yaml.safe_load(open("config/specs/oppo-find-x9-ultra.yaml"))
    s["bands"]["china"]["nr"] = None
    b = ph._bands(s, "china")
    assert b["unknown"] == "5G bands not published" and not b["missing"]
    s["bands"]["china"]["lte"] = [x for x in s["bands"]["china"]["lte"] if x != 20]
    assert ph._bands(s, "china")["missing"] == ["LTE 20"]
    sb = sp._bands(s, "china")
    assert sb["nr"] == [] and sb["unk_nr"] and not sb["unk_lte"]


def test_country_for_settings():
    from pricechecker.pricing import Settings
    from pricechecker.site.pages.phone import country_for
    s = lambda region, area="": Settings(region, area, "card", "eur")
    assert country_for(s("EU", "DE")) == "DE" and country_for(s("EU")) is None
    assert country_for(s("UK")) == "GB" and country_for(s("US")) == "US" and country_for(s("AU")) == "AU"
    assert country_for(s("CA", "ON")) == "CA" and country_for(s("CA")) == "CA"
    assert country_for(s("Global")) is None


def _bands_attr(html_text):
    m = re.search(r"data-bands='([^']*)'", html_text)
    return json.loads(html.unescape(m.group(1))) if m else None


@live
def test_phone_page_carries_bands_and_carrier_files(site_build):
    from pricechecker import carriers
    pages = [p for p in (site_build / "phones").glob("*.html") if "data-bands=" in p.read_text()]
    assert pages
    for page in pages:
        text = page.read_text()
        b = _bands_attr(text)
        assert set(b) <= {"china", "global"} and all(v is None or set(v) == {"lte", "nr"} for v in b.values())
        c = json.loads(html.unescape(re.search(r"data-carriers='([^']*)'", text).group(1)))
        assert set(c) == set(carriers.COUNTRIES)
        assert all((page.parent / p).resolve().exists() for p in c.values())


def test_phone_page_bands_only_for_shown_versions_and_never_invented():
    from pricechecker.site.pages import phone
    sheet = {"bands": {"global": {"lte": [1, 3], "nr": None}}}
    assert phone.bands_attr(sheet, ["china", "global"]) == {"china": None, "global": {"lte": [1, 3], "nr": None}}
    assert phone.bands_attr(sheet, ["global"]) == {"global": {"lte": [1, 3], "nr": None}}
    assert phone.bands_attr({}, ["china"]) == {"china": None}


def test_phone_page_carrier_summary_is_none_without_a_country_and_per_version_with_one(monkeypatch):
    from pricechecker import carriers
    from pricechecker.pricing import Settings
    from pricechecker.site.pages import phone
    sheet = {"bands": {"global": {"lte": [1], "nr": None}}}
    assert phone._carrier(sheet, ["global"]) is None            # default: EU, no country
    net = {"id": "a", "name": "A", "lte": [1], "nr": None, "basis": "used", "complete": False}
    monkeypatch.setattr(phone, "DEFAULT", Settings("UK", "", "card", "gbp"))
    monkeypatch.setattr(carriers, "load", lambda: {"GB": {"country": "GB", "networks": [net]}})
    r = phone._carrier(sheet, ["china", "global"])
    assert set(r) == {"china", "global"} and r["china"]["text"].startswith("In United Kingdom: bands not published")
    assert r["global"]["counts"]["nogaps"] == 1


# --- carrier check on the phone page (synthetic site: no saved prices) ---

def _carrier_page(monkeypatch, region="EU", area="", bands="both", doc=True):
    """The phone page for a synthetic two-version phone whose sheet has bands, with `region`/`area` as the default settings
    and a synthetic Germany/Great Britain carrier file. Returns the html."""
    import copy
    import dataclasses

    from pricechecker import carriers, fx, run, terms
    from pricechecker.pricing import Settings
    from pricechecker.site import _env, context, offers
    from pricechecker.site.pages import phone
    stores, catalog = run.load_config()
    data = context.load(catalog, stores, fx.cached(), terms.saved_status())
    p = copy.deepcopy(offers.assemble(data)[0])
    shop = next(o for o in json.loads((ROOT / "tests/fixtures/states_phone.json").read_text())["offers"] if o["store_label"] == "Settled Shop")
    p["editions"] = ["china", "global"]
    p["offers"] = [{**shop, "store": "settled", "currency": "EUR", "price": 1000.0 + 50 * i, "edition": e} for i, e in enumerate(p["editions"])]
    rows = [{"time": "2026-10-24T08:00:00Z", "store": "settled", "model_id": p["id"], "edition": e, "storage": "12/256", "price": 1000.0 + 50 * i,
             "currency": "EUR", "available": True} for i, e in enumerate(p["editions"])]
    sheet = {"bands": {"china": {"lte": [1, 3, 7], "nr": [78]}, "global": {"lte": [1, 3, 7, 20], "nr": [78]}}}
    if bands == "none":
        sheet = {}
    elif bands == "china":
        sheet["bands"].pop("global")
    data = dataclasses.replace(data, rows=rows, rows_all=rows, spec_sheets={**data.spec_sheets, p["id"]: sheet})
    net = {"id": "de-a", "name": "Anet", "lte": [1, 3, 7, 20], "nr": [78], "basis": "licensed", "complete": True, "sources": [], "mvnos": ["Cheapo"]}
    cc = phone.country_for(Settings(region, area, "card", "eur"))
    monkeypatch.setattr(phone, "DEFAULT", Settings(region, area, "card", "eur"))
    monkeypatch.setattr(carriers, "load", lambda *a, **k: {cc: {"country": cc, "networks": [net]}} if cc and doc else {})
    ctx = context.page_context(data, [p])
    ctx["updated"] = "2026-10-30T12:00:00Z"
    return phone.render(_env(), data, ctx, [p])[f'phones/{p["slug"]}.html']


def _means(h):
    return h[h.index('id="means-h"'):h.index("Price history by store")]


def _section(h, a, b):
    return h[h.index(a):h.index(b, h.index(a))]


def test_phone_page_with_a_country_shows_the_summary_not_the_eu_lines(monkeypatch):
    h = _carrier_page(monkeypatch, "EU", "DE")
    bullet = _section(h, 'id="s-csum"', 'id="s-eu"')
    assert "In Germany: " in bullet and "EU networks" not in bullet and "Pick your country" not in bullet
    assert 'id="s-eu" hidden' in h and 'id="s-clink"' in h and 'id="s-clink" href="#carrier" hidden' not in h
    lines = _section(h, 'id="s-csums"', 'id="s-eulines"')
    assert "EU networks" not in lines and "China version:</b>" in lines and "Global version:</b>" in lines
    assert lines.count("In Germany: ") == 2 and "coverage risk on Anet (no band 20)" in lines     # China lacks band 20
    assert 'id="s-eulines" hidden' in h and 'id="s-csums" hidden' not in h
    c = _section(h, 'id="carrier"', "</section>")
    assert re.search(r'<section id="carrier"[^>]* hidden>', h)      # revealed by the script: dead controls without JS
    assert 'id="cc-country"' not in c and 'id="cc-net"' in c and "Choose your network" in c and 'class="cv ' not in c   # nothing faked without JS
    assert "Cheapo — on Anet" in text_of(c)
    assert h.index("<h2>Specs</h2>") < h.index('class="bandchk"') < h.index('id="carrier"')   # under Specs, after the band lines
    assert '<div class="cc-out" aria-live="polite" aria-atomic="true"></div>' in c
    assert '</span>.</b> <a id="s-clink"' in h      # the bullet's full stop is markup, not CSS
    assert "#s-csum::after" not in (ROOT / "static/d.css").read_text()
    assert len(h.encode()) <= 60_000


def text_of(h):
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", h)))


def test_phone_page_without_a_country_prompts_and_keeps_the_eu_lines(monkeypatch):
    for region, area in (("EU", ""), ("Global", "")):
        h = _carrier_page(monkeypatch, region, area)
        bullet = _section(h, 'id="s-csum"', 'id="s-eu"')
        assert 'id="s-csum" hidden></b>' in h and "Pick your country" not in bullet   # no dead link without JS
        assert re.search(r'<section id="carrier"[^>]* hidden>', h)
        assert 'id="s-eu"' in h and 'id="s-eu" hidden' not in h and 'id="s-clink" href="#carrier" hidden' in h
        assert "version on EU networks:</b>" in h and 'id="s-csums" hidden' in h and 'id="s-eulines" hidden' not in h
        c = _section(h, 'id="carrier"', "</section>")
        assert 'id="cc-country"' in c and 'id="cc-net"' not in c and "Bands only" not in c


def test_phone_page_other_countries_from_the_settings(monkeypatch):
    for region, area, name in (("UK", "", "United Kingdom"), ("CA", "ON", "Canada"), ("US", "", "United States")):
        h = _carrier_page(monkeypatch, region, area)
        assert f"In {name}: " in _section(h, 'id="s-csum"', 'id="s-eu"')
        assert 'id="cc-country"' not in _section(h, 'id="carrier"', "</section>")


def test_phone_page_without_any_bands_keeps_the_old_text(monkeypatch):
    h = _carrier_page(monkeypatch, "EU", "", bands="none")
    assert 'id="carrier"' not in h and 'id="s-csum"' not in h and "Pick your country" not in h
    assert "Some 4G/5G bands may be missing" in _means(h)
    assert 'data-bands=\'{"china": null, "global": null}\'' in h


def test_phone_page_data_attributes_are_valid_json(monkeypatch):
    for bands in ("both", "china", "none"):
        h = _carrier_page(monkeypatch, "EU", "DE", bands=bands)
        b = _bands_attr(h)
        c = json.loads(html.unescape(re.search(r"data-carriers='([^']*)'", h).group(1)))
        assert set(b) == {"china", "global"} and all(v is None or set(v) == {"lte", "nr"} for v in b.values())
        assert set(c) == set(__import__("pricechecker.carriers", fromlist=["x"]).COUNTRIES)
        assert (b["global"] is None) == (bands != "both") and (b["china"] is None) == (bands == "none")


@live
def test_no_hourly_claims(site_build):
    """Prices are checked several times a day; nothing a visitor or search engine reads says hourly (spec §8)."""
    bad = []
    for f in [*site_build.rglob("*.html"), *site_build.rglob("*.xml")]:
        t = html.unescape(re.sub(r"<script\b.*?</script>", " ", f.read_text(), flags=re.DOTALL))
        if re.search(r"(?i)\bevery hour\b|\bhourly\b", t):
            bad.append(f.relative_to(site_build).as_posix())
    assert not bad, bad[:10]


def test_telegram_intro_and_cards_say_several_times_a_day():
    import inspect

    from pricechecker import telegram
    from pricechecker.site import cards
    for mod in (telegram, cards):
        src = inspect.getsource(mod)
        assert "every hour" not in src and "several times a day" in src
