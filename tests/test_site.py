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


def test_variants_config_uses_catalog_ids_and_storage_keys():
    import re
    import yaml
    from pathlib import Path
    ids = {p["id"] for p in yaml.safe_load(Path("config/catalog.yaml").read_text())["phones"]}
    for model, eds in yaml.safe_load(Path("config/variants.yaml").read_text()).items():
        assert model in ids
        for ed, v in eds.items():
            assert ed in ("global", "china") and v["source"].startswith("https://")
            assert all(re.fullmatch(r"\d{1,2}/\d{3,4}", str(s)) for s in v["made"])


def _row(t, price, ok=True, store="wonda", storage="12/256"):
    return {"time": t, "store": store, "model_id": "x", "edition": "china", "storage": storage, "price": price,
            "currency": "USD", "available": ok}


def test_trend_reports_a_drop_since_first_seen_and_ignores_flat_prices():
    from datetime import datetime
    now = datetime(2026, 10, 19, 18, 0)
    offer = {"store": "wonda", "edition": "china", "storage": "12/256", "price": 950.0, "available": True}
    rows = [_row("2026-10-16T08:00:00Z", 1000.0), _row("2026-10-18T08:00:00Z", 950.0)]
    t = site._trend(rows, "x", offer, now)
    assert t == {"drop": round(50 / 950, 4), "since": "2026-10-16"}    # history shorter than a week: "since 16 Oct"
    assert site._trend([_row("2026-10-16T08:00:00Z", 950.0)], "x", offer, now) is None
    assert site._trend(rows, "x", {**offer, "available": False}, now) is None


def test_stats_follow_the_cheapest_store_over_time():
    from datetime import datetime
    t1, t2, now = datetime(2026, 10, 16), datetime(2026, 10, 18), datetime(2026, 10, 20)
    series = {("a", "china"): [(t1, 1000.0), (t2, 900.0)], ("b", "china"): [(t1, 950.0)]}
    st = site._stats(series, now, "EUR")
    assert (st["now"], st["low"], st["high"], st["avg"]) == ("€900", "€900", "€950", "€925")   # 2 days at 950, 2 at 900
    assert st["low_at"] == "18 Oct" and st["since"] == "16 Oct"


def test_delivery_days_come_from_store_terms():
    from pricechecker import terms
    cfg = {"terms": {"shipping": {"EU": {"days": [2, 5]}, "UK": {"cost": 0}}}}
    assert terms.delivery(cfg, "EU") == [2, 5] and terms.delivery(cfg, "UK") is None
