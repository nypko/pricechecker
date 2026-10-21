from pathlib import Path

import yaml

from pricechecker import terms

STORES = yaml.safe_load((Path(__file__).parent.parent / "config/stores.yaml").read_text())["stores"]
RATES = {"EUR": 1.0, "USD": 1.16, "GBP": 0.87, "HKD": 9.05, "AUD": 1.80, "CAD": 1.60}


def test_payment_adjustments():
    assert terms.payment_pct(STORES["wonda"], "bank") == -4.5
    assert terms.payment_pct(STORES["mobilemarvel"], "bank") == -4.75
    assert terms.payment_pct(STORES["wonda"], "paypal") == 0
    assert terms.payment_pct(STORES["tradingshenzhen"], "paypal") == 4      # ~4% PayPal surcharge (payment-regulations page)
    assert terms.duties_included(STORES["tradingshenzhen"], "AU") is True   # store covers customs/GST everywhere
    assert terms.payment_pct(STORES["amazon"], "card") is None              # no terms at all


def test_shipping_uses_store_rate_when_available():
    offer = {"price": 13800.0, "currency": "HKD", "prices": {"HKD": 13800.0, "USD": 1773.0, "EUR": 1600.0}}
    s = terms.shipping(STORES["mobilemarvel"], "UK", offer, RATES)
    assert s["usd"] == round(300 * 1773.0 / 13800.0, 2)        # Mobile Marvel's own HKD->USD rate
    assert s["gbp"] == round(300 / 9.05 * 0.87, 2)             # no own GBP price -> ECB
    assert terms.shipping(STORES["wonda"], "EU", {"price": 1129, "currency": "USD"}, RATES) == {"usd": 0, "eur": 0, "gbp": 0, "cad": 0, "aud": 0}
    assert terms.shipping(STORES["giztop"], "EU", {"price": 949, "currency": "USD"}, RATES) is None


def test_payment_minimum_order():
    assert terms.min_order_usd(STORES["giztop"], "bank") == 1500
    assert not terms.payment_available(STORES["giztop"], "bank", 949)      # Giztop wires only over $1,500
    assert terms.payment_available(STORES["giztop"], "bank", 1600)
    assert terms.payment_available(STORES["giztop"], "card", 949)
    assert terms.payment_available(STORES["wonda"], "bank", 100)


def test_australia_shipping():
    offer = {"price": 13800.0, "currency": "HKD", "prices": {"USD": 1773.0}}
    assert terms.shipping(STORES["mobilemarvel"], "AU", offer, RATES)["usd"] == round(300 * 1773.0 / 13800.0, 2)
    assert terms.shipping(STORES["wonda"], "AU", {"price": 1129, "currency": "USD"}, RATES)["usd"] == 0
    assert terms.shipping(STORES["giztop"], "AU", {"price": 949, "currency": "USD"}, RATES) is None


def test_duties_included():
    assert terms.duties_included(STORES["mobilemarvel"], "AU") is True
    assert terms.duties_included(STORES["giztop"], "EU") is None   # IOSS covers parcels up to EUR 150 only; buyers report charges
    assert terms.duties_included(STORES["giztop"], "AU") is False
    assert terms.duties_included(STORES["wonda"], "EU") is None         # not stated


def test_minimum_shipping_is_marked():
    from pricechecker import terms
    cfg = {"terms": {"shipping": {"EU": {"cost": None, "cost_min": 10, "currency": "EUR"}}}}
    offer = {"currency": "EUR", "price": 1000.0}
    out = terms.shipping(cfg, "EU", offer, {"EUR": 1.0, "USD": 1.1, "GBP": 0.87, "AUD": 1.7, "CAD": 1.6})
    assert out["min"] == 1 and out["eur"] == 10.0
    assert terms.shipping({"terms": {"shipping": {"EU": {"cost": None}}}}, "EU", offer, {"EUR": 1.0, "USD": 1.1, "GBP": 0.87, "AUD": 1.7, "CAD": 1.6}) is None


def test_canada_terms_and_tax_config():
    import yaml
    from pathlib import Path
    tax = yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"]["CA"]
    assert tax["ship_taxed"] is False and tax["provinces"]["QC"]["rate"] == 14.975 and tax["provinces"]["AB"]["rate"] == 5
    assert terms.duties_included(STORES["mobilemarvel"], "CA") is True     # "fully landed" for Canada
    assert terms.duties_included(STORES["giztop"], "CA") is False
    assert terms.shipping(STORES["wonda"], "CA", {"price": 1129, "currency": "USD"}, RATES)["cad"] == 0


def test_terms_page_wording_and_diff():
    html = ("<header><a>Cart 3 items in your basket now</a></header><main><h1>Customs</h1>"
            "<p>Canada: few duties and taxes, we usually declare a lower value.</p><p>EU: IOSS covers it.</p></main>")
    lines = terms.policy_lines(html)
    assert lines == ["Canada: few duties and taxes, we usually declare a lower value.", "EU: IOSS covers it."]   # header and "Customs" out
    new = terms.policy_lines(html.replace("few duties", "duties and GST"))
    assert terms.page_diff(lines, new) == ["-Canada: few duties and taxes, we usually declare a lower value.",
                                           "+Canada: duties and GST and taxes, we usually declare a lower value."]


def test_store_that_does_not_deliver():
    cfg = {"terms": {"shipping": {"EU": {"cost": 0, "currency": "EUR"}, "US": {"ships": False}}}}
    offer = {"price": 1000.0, "currency": "EUR", "prices": {"EUR": 1000.0}}
    assert terms.shipping(cfg, "US", offer, RATES) is False      # the page leaves the offer out for the US
    assert terms.shipping(cfg, "EU", offer, RATES)["eur"] == 0
    assert terms.shipping(cfg, "AU", offer, RATES) is None       # not listed: still shown, as "shipping not listed"
