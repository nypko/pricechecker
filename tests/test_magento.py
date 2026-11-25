"""Giztop (Magento 2): the phone category's first page plus tracked phones' pages from the sitemap. Its robots.txt
disallows the category's further pages (/*?p=), which the reader walked until 2026-11-25."""
import json

from pricechecker import http
from pricechecker.stores import magento

LISTING = """
<a class="product-item-link" href="https://gz.example/huawei-mate-x8.html">Huawei Mate X8</a> <span data-price-amount="2499"></span>
<a class="product-item-link" href="https://gz.example/honor-700.html">Honor 700</a> <span data-price-amount="699"></span>
"""
INDEX = "<sitemapindex><sitemap><loc>https://gz.example/sitemap-1-1.xml</loc></sitemap></sitemapindex>"
URLSET = """<urlset>
<url><loc>https://gz.example/huawei-mate-x8.html</loc><lastmod>2026-11-24T10:00:00+00:00</lastmod></url>
<url><loc>https://gz.example/oppo-find-x9-ultra-global-black-16gb-1tb.html</loc><lastmod>2026-11-20T10:00:00+00:00</lastmod></url>
<url><loc>https://gz.example/oppo-find-x9-ultra-case.html</loc><lastmod>2026-11-20T10:00:00+00:00</lastmod></url>
<url><loc>https://gz.example/oppo-find-x9-ultra-hasselblad-master-set.html</loc><lastmod>2026-11-20T10:00:00+00:00</lastmod></url>
<url><loc>https://gz.example/xiaomi-15.html</loc><lastmod>2025-01-01T10:00:00+00:00</lastmod></url>
</urlset>"""


def page(name, price):
    return f'<script type="application/ld+json">{{"@type": "Product", "name": "{name}", "offers": {{"price": "{price}", "priceCurrency": "USD", "availability": "https://schema.org/InStock"}}}}</script>'


PAGES = {
    "https://gz.example/phones.html": LISTING,
    "https://gz.example/sitemap.xml": INDEX,
    "https://gz.example/sitemap-1-1.xml": URLSET,
    "https://gz.example/huawei-mate-x8.html": page("Huawei Mate X8", 2499),
    "https://gz.example/oppo-find-x9-ultra-global-black-16gb-1tb.html": page("OPPO Find X9 Ultra Global-Black-16GB - 1TB", 1599),
    "https://gz.example/oppo-find-x9-ultra-hasselblad-master-set.html": page("OPPO Find X9 Ultra Hasselblad Master Set", 1999),
}
CATALOG = [{"id": "huawei-mate-x8"}, {"id": "oppo-find-x9-ultra"}]
CFG = {"base_url": "https://gz.example", "categories": ["/phones.html"], "sitemap_url": "https://gz.example/sitemap.xml",
       "currency": "USD", "exclude_title": "used|refurbished"}


def run(monkeypatch, tmp_path, pages=PAGES):
    asked = []

    class Resp:
        def __init__(self, text):
            self.text = text

    def get(url, **kw):
        asked.append(url)
        if url not in pages:
            raise AssertionError(f"unexpected request {url}")
        return Resp(pages[url])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir(exist_ok=True)
    monkeypatch.setattr(http, "get", get)
    monkeypatch.setattr(magento, "market_rates", lambda base, url, cur="USD": {"USD": 1.0})
    return magento.fetch("giztop", CFG, CATALOG), asked


def test_reads_page_one_and_the_sitemap_never_further_listing_pages(monkeypatch, tmp_path):
    offers, asked = run(monkeypatch, tmp_path)
    assert not any("?p=" in u for u in asked)
    assert "https://gz.example/oppo-find-x9-ultra-case.html" not in asked and "https://gz.example/xiaomi-15.html" not in asked
    got = sorted((o.model_id, o.edition, o.storage, o.price) for o in offers if o.model_id in {"huawei-mate-x8", "oppo-find-x9-ultra"})
    assert got == [("huawei-mate-x8", "china", "base", 2499.0), ("oppo-find-x9-ultra", "global", "16/1024", 1599.0)]
    assert [o.model_id for o in offers if o.model_id not in {"huawei-mate-x8", "oppo-find-x9-ultra"}] == ["honor-700"]   # untracked, page 1
    saved = json.loads((tmp_path / "data/giztop_sitemap.json").read_text())
    assert set(saved["urls"]) == {"https://gz.example/huawei-mate-x8.html", "https://gz.example/oppo-find-x9-ultra-global-black-16gb-1tb.html",
                                  "https://gz.example/oppo-find-x9-ultra-hasselblad-master-set.html"}
    cache = json.loads((tmp_path / "data/giztop_pages.json").read_text())
    assert "variants" not in cache["https://gz.example/oppo-find-x9-ultra-hasselblad-master-set.html"]   # not a tracked phone


def test_second_run_uses_the_saved_sitemap_and_cached_pages(monkeypatch, tmp_path):
    run(monkeypatch, tmp_path)
    offers, asked = run(monkeypatch, tmp_path)
    assert asked == ["https://gz.example/phones.html"]   # sitemap kept for a day, pages for REFRESH, the set never re-read
    assert {o.model_id for o in offers} >= {"huawei-mate-x8", "oppo-find-x9-ultra"}


def test_a_failed_sitemap_falls_back_to_the_pages_read_before(monkeypatch, tmp_path):
    run(monkeypatch, tmp_path)
    (tmp_path / "data/giztop_sitemap.json").unlink()
    broken = {k: v for k, v in PAGES.items() if "sitemap" not in k}
    offers, asked = run(monkeypatch, tmp_path, broken)   # unexpected request -> AssertionError inside get -> warning
    assert {o.model_id for o in offers} >= {"huawei-mate-x8", "oppo-find-x9-ultra"}
