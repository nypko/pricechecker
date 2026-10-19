from pricechecker import site


def test_editions_combined_per_model():
    catalog = [{"id": "oppo-find-n6", "edition": "china", "name": "Oppo Find N6", "brand": "Oppo"},
               {"id": "oneplus-15", "edition": "global", "name": "Oneplus 15", "brand": "Oneplus"},
               {"id": "oppo-find-n6", "edition": "global", "name": "Oppo Find N6", "brand": "Oppo"}]
    models = site._models(catalog)
    assert [m["id"] for m in models] == ["oppo-find-n6", "oneplus-15"]
    assert models[0]["editions"] == ["global", "china"]      # Global listed first
    assert models[1]["editions"] == ["global"]


def test_chart_ticks_are_round():
    assert site._ticks(1075, 1249) == [1050, 1100, 1150, 1200, 1250]
    assert site._ticks(1099, 1700) == [1000, 1200, 1400, 1600, 1800]


def test_chart_for_a_price_that_never_changed():
    from datetime import datetime
    first, now = datetime(2026, 10, 16, 8, 51), datetime(2026, 10, 19, 17, 0)
    svg = site._chart({("wonda", "china"): [(first, 957.0)]}, {"wonda": "#123"}, now, "EUR")
    assert "<path" in svg and "€" in svg                     # a flat line from first seen up to the last check
    assert site._chart({("wonda", "china"): [(now, 957.0)]}, {"wonda": "#123"}, now) == ""   # seen only just now
