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
