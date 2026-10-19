from datetime import date

from pricechecker import promos


def test_finds_promotion_lines_in_page_text():
    html = """<html><script>var sale = "ignore me";</script><div class="bar">2% summer sale at checkout - Auto Applied</div>
    <nav><a href="/">Home</a><a href="/c">Phones</a></nav><p>Bank transfers enjoy 4.75% OFF all orders</p>
    <p>Free shipping worldwide</p><a>SALE</a><a>Vouchers</a><p>Use code AUTUMN10 for 10% off accessories</p></html>"""
    found = promos.snippets(promos.text_of(html))
    assert "2% summer sale at checkout - Auto Applied" in found
    assert "Bank transfers enjoy 4.75% OFF all orders" in found
    assert "Use code AUTUMN10 for 10% off accessories" in found
    assert not any("ignore me" in s or "Free shipping" in s for s in found)
    assert "SALE" not in found and "Vouchers" not in found


def test_promotion_expires_with_banner_or_date():
    promo = {"pct": 2, "watch": "2% summer sale"}
    assert promos.promo_active(promo, "... 2% Summer Sale at checkout ...", date(2026, 10, 19)) is True
    assert promos.promo_active(promo, "Autumn deals", date(2026, 10, 19)) is False
    assert promos.promo_active(promo, None, date(2026, 10, 19)) is None          # page not read: keep last answer
    assert promos.promo_active({**promo, "until": "2026-10-31"}, "2% summer sale", date(2026, 11, 1)) is False


def test_active_uses_last_scan_and_until():
    cfg = {"terms": {"promo": {"pct": 2, "watch": "x"}}}
    assert promos.active("s", cfg, {}) is True                                   # never scanned: trust config
    assert promos.active("s", cfg, {"s": {"promo_active": False}}) is False
    assert promos.active("s", {"terms": {"promo": {"pct": 2, "until": "2000-01-01"}}}, {}) is False
    assert promos.active("s", {"terms": {}}, {}) is False


def test_coupon_hints_expire():
    cfg = {"coupons": [{"code": "H2026", "text": "up to 30%", "until": "2999-01-01", "watch": "H2026"}]}
    assert [c["code"] for c in promos.coupons("g", cfg, {})] == ["H2026"]
    assert promos.coupons("g", cfg, {"g": {"coupons": {"H2026": False}}}) == []          # gone from the page
    assert promos.coupons("g", {"coupons": [{"code": "X", "until": "2000-01-01"}]}, {}) == []   # past its date
