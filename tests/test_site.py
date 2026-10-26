from datetime import UTC

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
    from pathlib import Path

    import yaml
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


def test_specs_config_uses_catalog_ids():
    from pathlib import Path

    import yaml
    ids = {p["id"] for p in yaml.safe_load(Path("config/catalog.yaml").read_text())["phones"]}
    specs = yaml.safe_load(Path("config/specs.yaml").read_text())["phones"]
    assert set(specs) <= ids, set(specs) - ids
    assert site._specs({"chip": "X", "screen": "8.12 inside", "battery": "5,600 mAh"}) == [("Chip", "X"), ("Screen", "8.12″ inside"), ("Battery", "5,600 mAh")]


def test_buyer_report_parsing():
    from pricechecker.buyer_reports import parse
    assert parse("Ordered from Giztop, arrived in Germany after 9 days with DHL. Had to pay €187 import VAT.") == \
        {"country": "DE", "courier": "DHL", "days": 9, "tax": True, "amount": 187.0, "currency": "EUR"}
    assert parse("Tradingshenzhen Global Priority to France took 3 weeks, no customs at all.") == \
        {"country": "FR", "courier": "Global Priority", "days": 21, "tax": False}
    assert parse("giztop is great, love the phone") == {}


def test_buyer_summary_groups_by_store_and_region(tmp_path, monkeypatch):
    from datetime import datetime

    from pricechecker import buyer_reports
    f = tmp_path / "r.yaml"
    f.write_text("reports:\n"
                 "- {id: a, store: giztop, date: 2026-09-01, country: DE, days: 9, tax: true}\n"
                 "- {id: b, store: giztop, date: 2026-09-10, country: FR, days: 21, tax: false}\n"
                 "- {id: c, store: giztop, date: 2026-09-12, country: IT, days: 12}\n"
                 "- {id: d, store: giztop, date: 2024-01-01, country: DE, days: 40, tax: true}\n")   # older than a year: left out
    monkeypatch.setattr(buyer_reports, "APPROVED", f)
    s = buyer_reports.summary(datetime(2026, 10, 19, tzinfo=UTC))
    assert s == {"giztop": {"EU": {"n": 3, "dmin": 9, "dmax": 21, "dmed": 12, "nd": 3, "tk": 2, "tx": 1}}}


def test_ed_labels_asia_for_samsung_and_sony():
    from pricechecker.site import ed_labels
    assert ed_labels("Samsung")["china"] == "Asia" and ed_labels("Sony")["china"] == "Asia"
    assert ed_labels("Xiaomi") == {"global": "Global", "china": "China"}


def test_spec_parts_splits_editions():
    assert site._spec_parts("7,200 mAh (China) / 7,100 mAh (Global)") == [("7,200 mAh", "China"), ("7,100 mAh", "Global")]
    assert site._spec_parts("7.95″ inside") == [("7.95″", "inner screen")]
    assert site._spec_parts("Snapdragon 8 Elite Gen 5 or Exynos 2600 (by market)") == [("Snapdragon 8 Elite Gen 5 or Exynos 2600 (by market)", "")]


def test_average_dad_titles_parse():
    from pricechecker.normalize import edition_of, model_id, storage_of
    assert (model_id("OPPO Find X10 Pro Max (Global)"), edition_of("OPPO Find X10 Pro Max (Global)")) == ("oppo-find-x10-pro-max", "global")
    assert (model_id("OnePlus 16"), edition_of("OnePlus 16"), storage_of("Black / 12GB/256GB")) == ("oneplus-16", "china", "12/256")
    import re
    from pathlib import Path

    import yaml
    cfg = yaml.safe_load(Path("config/stores.yaml").read_text())["stores"]["averagedad"]
    assert re.search(cfg["exclude_title"], "OPPO Find X10 Pro Max Photo Kit", re.IGNORECASE)


def test_tax_config_covers_all_eu_countries():
    from pathlib import Path

    import yaml
    eu = yaml.safe_load(Path("config/import_tax.yaml").read_text())["regions"]["EU"]["countries"]
    assert len(eu) == 27 and all(17 <= c["vat"] <= 27 for c in eu.values())


def test_indexnow_only_real_changes(tmp_path, monkeypatch):
    import json

    from pricechecker import history, indexnow
    monkeypatch.chdir(tmp_path)
    T0, T1 = "2026-10-26T10:00:00Z", "2026-10-27T10:00:00Z"
    history.append([[T0, "a", "phone-a", "china", "12/256", 1000, "USD", 1], [T0, "a", "phone-b", "china", "12/256", 1000, "USD", 1],
                    [T0, "a", "phone-c", "china", "12/256", 1000, "USD", 1],
                    [T1, "a", "phone-a", "china", "12/256", 990, "USD", 1], [T1, "a", "phone-b", "china", "12/256", 999, "USD", 1],
                    [T1, "a", "phone-c", "china", "12/256", 1000, "USD", 0], [T1, "a", "phone-d", "china", "12/256", 800, "USD", 1]])
    l = tmp_path / "l.json"
    l.write_text(json.dumps({"updated": T1}))
    assert indexnow.changed_slugs(l) == ["phone-a", "phone-c", "phone-d"]   # phone-b moved 0.1%: skipped
    u = indexnow.urls({"base_url": "https://x.app"}, ["phone-a", "gone"], {"phone-a"})
    assert u == ["https://x.app/", "https://x.app/compare", "https://x.app/phones/phone-a", "https://x.app/history/phone-a"]


def test_ship_cell_starting_price():
    from pricechecker import site
    rates = {"EUR": 1.0, "USD": 1.08, "GBP": 0.86, "AUD": 1.65}
    c = site._ship_cell({"currency": "EUR", "terms": {"shipping": {"EU": {"cost": None, "cost_min": 10, "currency": "EUR", "days": [12, 19]}}}}, "EU", rates)
    assert (c["cost"], c["days"]) == ("from €10", "12–19 working days")
    assert site._ship_cell({"terms": {"shipping": {"UK": {"cost": 0}}}}, "UK", rates)["cost"] == "free"


def test_sold_out_store_leaves_the_chart_and_stats():
    from datetime import datetime
    site.LABELS.setdefault("wonda", "Wonda")
    site.LABELS.setdefault("giztop", "Giztop")
    model = {"id": "x", "editions": ["china"], "brand": "Oppo"}
    rates = {"USD": 1.0}
    rows = [_row("2026-10-16T00:00:00Z", 900.0), _row("2026-10-16T00:00:00Z", 1000.0, store="giztop"),
            _row("2026-10-18T00:00:00Z", 900.0, ok=False)]
    s = site._series(rows, model, rates)
    assert s[("wonda", "china")][-1][1] is None   # sold out from 18 Oct
    st = site._stats(s, datetime(2026, 10, 20), "USD")
    assert st["now"] == "$1,000" and st["low"] == "$900"
    svg = site._chart(s, {"wonda": "#111", "giztop": "#222"}, datetime(2026, 10, 20), "USD")
    assert "data-steps=\"" in svg and ":;" not in svg.split("Wonda")[0][-5:]
    rows.append(_row("2026-10-19T00:00:00Z", 1000.0, ok=False, store="giztop"))
    assert site._stats(site._series(rows, model, rates), datetime(2026, 10, 20), "USD") is None   # nothing in stock


def test_store_prices_older_than_two_days_are_old():
    from datetime import datetime
    now = datetime(2026, 10, 20, 12)
    assert site._too_old("2026-10-18T11:00:00Z", now) and not site._too_old("2026-10-19T12:00:00Z", now)
    assert not site._too_old(None, now)


def test_title_price_prefers_known_shipping_over_a_slightly_lower_unknown():
    money = lambda v: {"eur": v}
    mk = lambda v, ship, duties: {"available": True, "money": money(v), "pay": {"card": 0}, "pay_ok": {"card": True},
                                  "ship": {"EU": ship}, "duties": {"EU": duties}}
    giztop = mk(1137, None, None)              # shipping not listed, tax not stated
    wonda = mk(1145, {"eur": 0}, None)         # free shipping, tax not stated
    assert site._title_price([giztop, wonda], {"EU": {"rate_pct": 21}}) == (1145, False, "import tax")
    assert site._title_price([giztop, wonda, {**mk(900, {"eur": 0}, True), "old": True}], {"EU": {"rate_pct": 21}}) == (1145, False, "import tax")


def test_title_price_counts_an_offer_without_listed_ram_storage_as_the_phone_page_does():
    # the page grid has a "not listed" row for it and app.js ranks it like any other (xiaomi-17-ultra-leica-edition)
    mk = lambda v, storage: {"available": True, "storage": storage, "money": {"eur": v}, "pay": {"card": 0},
                             "pay_ok": {"card": True}, "ship": {"EU": {"eur": 10}}, "duties": {"EU": True}}
    base, listed = mk(1137, "base"), mk(1292.95, "16/512")
    assert site._title_price([listed, base], {"EU": {"rate_pct": 21}}, with_offer=True) == (1147, True, "", base)


def test_title_price_never_led_by_an_old_price_or_a_store_refusing_card():
    mk = lambda v, **kw: {"available": True, "storage": "12/256", "money": {"eur": v}, "pay": {"card": 0}, "pay_ok": {"card": True},
                          "ship": {"EU": {"eur": 0}}, "duties": {"EU": True}, **kw}
    tax = {"EU": {"rate_pct": 21}}
    assert site._title_price([mk(900, old=True), mk(800, pay_ok={"card": False})], tax) is None
    assert site._title_price([mk(900, old=True), mk(1000)], tax) == (1000, True, "")


def test_telegram_posts_real_drops_only():
    from pricechecker import telegram
    d = lambda slug, eur, left="": {"slug": slug, "name": slug, "eur": eur, "left": left, "store": "S", "edition": "China",
                                    "storage": "12/256", "n_stores": 2}
    drops, new, st = telegram.changes([d("a", 1000)], {})
    assert not drops and not new and st["a"]["ref"] == 1000                      # first run: record only
    drops, new, st = telegram.changes([d("a", 990), d("b", 500)], st)
    assert not drops and [x["slug"] for x in new] == ["b"] and st["a"]["ref"] == 1000   # 1% dip: not news
    drops, _, st = telegram.changes([d("a", 1040), d("b", 500)], st)
    assert st["a"]["ref"] == 1040                                                 # rises raise the reference
    drops, _, st = telegram.changes([d("a", 1000), d("b", 500)], st)
    assert [x["was"] for x in drops] == [1040] and st["a"]["ref"] == 1000         # −€40, −3.8%: posted
    assert [(p["slug"], p["was"], p["eur"]) for p in st["posted"]] == [("a", 1040, 1000)] and st["posted"][0]["at"]
    from datetime import UTC, datetime
    later = datetime(2099, 1, 1, tzinfo=UTC)                                      # 14 days on, the record is pruned
    assert "posted" not in telegram.changes([d("a", 1000), d("b", 500)], st, later)[2]
    drops, _, st = telegram.changes([d("a", 900, "import tax"), d("b", 500)], st)
    assert not drops and st["a"] == {"ref": 900, "left": "import tax"}            # total covers something else: reset
    assert "€1,000" in telegram.drop_message({**d("a", 1000), "was": 1040}, "https://x") and "−€40" in telegram.drop_message({**d("a", 1000), "was": 1040}, "https://x")
