from pathlib import Path

import yaml

from pricechecker import terms

STORES = yaml.safe_load((Path(__file__).parent.parent / "config/stores.yaml").read_text())["stores"]
RATES = {"EUR": 1.0, "USD": 1.16, "GBP": 0.87, "HKD": 9.05, "AUD": 1.80}


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
    assert terms.shipping(STORES["wonda"], "EU", {"price": 1129, "currency": "USD"}, RATES) == {"usd": 0, "eur": 0, "gbp": 0, "aud": 0}
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
    out = terms.shipping(cfg, "EU", offer, {"EUR": 1.0, "USD": 1.1, "GBP": 0.87, "AUD": 1.7})
    assert out["min"] == 1 and out["eur"] == 10.0
    assert terms.shipping({"terms": {"shipping": {"EU": {"cost": None}}}}, "EU", offer, {"EUR": 1.0, "USD": 1.1, "GBP": 0.87, "AUD": 1.7}) is None
