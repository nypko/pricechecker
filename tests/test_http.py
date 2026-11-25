"""robots.txt rules as search engines read them (RFC 9309, Google): `*` wildcards, `$` end anchors, the longest
matching rule wins and Allow wins a tie. Python's urllib.robotparser reads `*` as a literal character, so Giztop's
`Disallow: /*?p=` never matched /phones.html?p=2 and the bot read pages it was asked not to (found 2026-11-25)."""
from pricechecker import http

GIZTOP = """User-agent: *
Disallow: /admin/
Disallow: /checkout/
Disallow: /*?p=
Disallow: /*?limit=
Disallow: /*utm_
Allow: /
"""


def test_wildcards_and_anchors():
    rules = http.robots_rules(GIZTOP)
    assert http.robots_allow(rules, "/phones.html")
    assert not http.robots_allow(rules, "/phones.html?p=2")
    assert not http.robots_allow(rules, "/phones.html?limit=36")
    assert not http.robots_allow(rules, "/x.html?utm_source=a")
    assert http.robots_allow(rules, "/xiaomi-18-pro-max.html")
    assert not http.robots_allow(rules, "/checkout/cart")
    end = http.robots_rules("User-agent: *\nDisallow: /*.json$\n")
    assert not http.robots_allow(end, "/products.json") and http.robots_allow(end, "/products.json?page=2")


def test_longest_match_wins_and_allow_wins_ties():
    rules = http.robots_rules("User-agent: *\nDisallow: /shop\nAllow: /shop/phones\nDisallow: /a\nAllow: /a\n")
    assert not http.robots_allow(rules, "/shop/cases") and http.robots_allow(rules, "/shop/phones/x")
    assert http.robots_allow(rules, "/a/b")
    assert http.robots_allow(http.robots_rules("User-agent: *\nDisallow:\n"), "/anything")   # empty Disallow = allow all
    assert http.robots_allow(http.robots_rules(""), "/anything")                              # no robots.txt = allow all


def test_our_own_group_replaces_the_star_group():
    text = "User-agent: *\nDisallow: /\n\nUser-agent: PriceCheckerBot\nUser-agent: OtherBot\nAllow: /\nDisallow: /private\n"
    rules = http.robots_rules(text)
    assert http.robots_allow(rules, "/products.json") and not http.robots_allow(rules, "/private/x")
    assert not http.robots_allow(http.robots_rules("User-agent: *\nDisallow: /\n\nUser-agent: OtherBot\nAllow: /\n"), "/x")


def test_allowed_reads_the_cached_robots_txt(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "ROBOTS_CACHE", tmp_path / "robots.json")
    monkeypatch.setattr(http, "_robots", {})
    monkeypatch.setattr(http, "_robots_text", lambda host: GIZTOP)
    assert http.allowed("https://www.giztop.com/phones.html")
    assert not http.allowed("https://www.giztop.com/phones.html?p=2")


def test_get_judges_the_url_with_its_params(monkeypatch):
    monkeypatch.setattr(http, "_robots", {"https://shop.example": http.robots_rules("User-agent: *\nDisallow: /*?*page=\n")})
    try:
        http.get("https://shop.example/products.json", params={"limit": 250, "page": 2})
        raise AssertionError("expected Blocked")
    except http.Blocked as e:
        assert "page=2" in str(e)
