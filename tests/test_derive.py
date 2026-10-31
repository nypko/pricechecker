from datetime import UTC, datetime

from pricechecker import derive
from pricechecker.pricing import Settings, tax_rule

RATES = {"EUR": 1.0, "USD": 1.1}
NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)


def row(time, price, store="s", model="m", edition="china", storage="12/256", cur="EUR", avail=True):
    return {"time": time, "store": store, "model_id": model, "edition": edition, "storage": storage,
            "price": price, "currency": cur, "available": avail}


def test_store_joining_is_not_a_drop():
    rows = [row("2026-10-01T00:00:00Z", 1000, store="a"), row("2026-10-26T00:00:00Z", 800, store="b")]
    assert derive.listing_drops(rows, RATES, NOW) == []


def test_drop_thresholds():
    def one(now_price):
        rows = [row("2026-10-01T00:00:00Z", 1000), row("2026-10-26T00:00:00Z", now_price)]
        (d,) = derive.listing_drops(rows, RATES, NOW)
        return d
    assert one(971)["real"] is False                      # -2.9%
    small = derive.listing_drops([row("2026-10-01T00:00:00Z", 400), row("2026-10-26T00:00:00Z", 385)], RATES, NOW)[0]
    assert small["real"] is False and small["pct"] < -3   # -3.75% but EUR 15
    d = one(965)                                          # -3.5%, EUR 35 -> real; 40 below
    assert d["real"] is True and d["then"] == 1000 and d["now"] == 965 and d["eur"] == 35
    assert d["slug"] == "m" and d["store"] == "s" and d["when"] == "2026-10-26"
    assert one(960)["pct"] == -4.0


def test_drop_ignores_sold_out_and_old_changes():
    rows = [row("2026-10-01T00:00:00Z", 1000), row("2026-10-26T00:00:00Z", 900, avail=False)]
    assert derive.listing_drops(rows, RATES, NOW) == []
    rows = [row("2026-09-01T00:00:00Z", 1000), row("2026-09-10T00:00:00Z", 900)]   # it fell a month ago, held since
    assert derive.listing_drops(rows, RATES, NOW) == []


def test_drop_converts_to_eur():
    rows = [row("2026-10-01T00:00:00Z", 1100, cur="USD"), row("2026-10-26T00:00:00Z", 1000, cur="USD")]
    (d,) = derive.listing_drops(rows, RATES, NOW)
    assert d["then"] == 1000 and d["now"] == 909.09


def test_sub_store_folds_into_parent_line():
    rows = [row("2026-10-01T00:00:00Z", 1000, store="x"), row("2026-10-01T00:00:00Z", 950, store="x_eu"),
            row("2026-10-02T00:00:00Z", 950, store="x_eu", avail=False)]
    lines = derive.store_lines(rows, "m", "china", RATES)
    assert list(lines) == ["x"]
    assert lines["x"] == [("2026-10-01", 950.0), ("2026-10-02", 1000.0)]   # EU copy sold out: only the parent's price left


def test_store_lines_carry_state_and_skip_sold_out_and_other_phones():
    rows = [row("2026-10-01T00:00:00Z", 100, store="a"), row("2026-10-03T00:00:00Z", 90, store="b"),
            row("2026-10-03T00:00:00Z", 5, store="a", model="other"), row("2026-10-04T00:00:00Z", 1, store="a", avail=False)]
    lines = derive.store_lines(rows, "m", "china", RATES)
    assert lines["a"] == [("2026-10-01", 100.0), ("2026-10-03", 100.0)]
    assert lines["b"] == [("2026-10-03", 90.0), ("2026-10-04", 90.0)]


def offer(edition, storage, total, **kw):
    # ship and duties known, EUR, no payment fee: total == money.eur
    return {"edition": edition, "storage": storage, "available": True, "money": {"eur": total}, "pay": {"card": 0},
            "ship": {"EU": {"eur": 0}}, "duties": {"EU": True}, **kw}


RULE = tax_rule({"EU": {"rate_pct": 21}}, Settings("EU", "", "card", "eur"))


def test_gap_same_storage_only():
    offers = [offer("china", "12/256", 800), offer("china", "12/512", 900), offer("global", "12/512", 1200),
              offer("global", "12/512", 1300), offer("global", "16/512", 1000)]
    assert derive.gap(offers, RULE) == {"storage": "12/512", "china": 900, "global": 1200, "diff": 300}


def test_gap_none_without_shared_storage():
    assert derive.gap([offer("china", "12/256", 800), offer("global", "12/512", 1200)], RULE) is None
    assert derive.gap([], RULE) is None


def test_gap_uses_settled_totals_only():
    open_ship = offer("china", "12/512", 500, ship={"EU": None})
    open_ship["ship"] = {}
    assert derive.gap([open_ship, offer("global", "12/512", 1200)], RULE) is None
    assert derive.gap([offer("china", "12/512", 500, available=False), offer("global", "12/512", 1200)], RULE) is None


def test_mark_headline_without_posted_key():
    drops = [{"slug": "a"}]
    out = derive.mark_headline(drops, {"a": {"ref": 1, "left": ""}}, NOW)   # an old state has no "posted"
    assert out == [{"slug": "a"}]


def test_mark_headline_within_window():
    st = {"posted": [{"slug": "a", "at": "2026-10-25T00:00:00Z", "was": 1040, "eur": 1000},
                     {"slug": "b", "at": "2026-10-01T00:00:00Z", "was": 1, "eur": 1}]}
    out = derive.mark_headline([{"slug": "a"}, {"slug": "b"}, {"slug": "c"}], st, NOW)
    assert [d.get("headline", False) for d in out] == [True, False, False]
    assert derive.mark_headline([{"slug": "a"}], {"phones": st}, NOW)[0]["headline"] is True   # the whole saved file works too


def test_promo_split():
    o = {"money": {"eur": 1056.95}, "promo": {"pct": 2}}
    assert derive.promo_split(o, "eur") == (1056.95, 21.14, 1035.81)
    assert derive.promo_split({"money": {"eur": 500}}, "eur") == (500, 0, 500)


# --- the Drops page's lists (spec §5.4) ---

def _three_cases():
    """One 5% / EUR 50 drop, one 2% drop, one 4% but EUR 15 drop - all within the week."""
    return [row("2026-10-01T00:00:00Z", 1000, model="big"), row("2026-10-26T00:00:00Z", 950, model="big"),
            row("2026-10-01T00:00:00Z", 2000, model="two"), row("2026-10-26T00:00:00Z", 1960, model="two"),
            row("2026-10-01T00:00:00Z", 375, model="cheap"), row("2026-10-26T00:00:00Z", 360, model="cheap")]


def test_week_drops_lists_only_real_drops():
    out = derive.week_drops(_three_cases(), RATES, NOW)
    assert [d["slug"] for d in out] == ["big"]
    assert out[0]["pct"] == -5.0 and out[0]["eur"] == 50 and "headline" not in out[0]


def test_week_drops_marks_the_telegram_headline():
    state = {"phones": {"posted": [{"slug": "big", "at": "2026-10-26T08:00:00Z", "was": 1000, "eur": 950}]}}
    (d,) = derive.week_drops(_three_cases(), RATES, NOW, state)
    assert d["headline"] is True
    (d,) = derive.week_drops(_three_cases(), RATES, NOW, {})   # no state: nothing marked
    assert "headline" not in d


def test_older_drops_are_real_drops_outside_this_week_latest_first():
    rows = [row("2026-09-20T00:00:00Z", 1000, model="a"), row("2026-10-05T00:00:00Z", 900, model="a"),
            row("2026-09-20T00:00:00Z", 800, model="b"), row("2026-10-15T00:00:00Z", 700, model="b"),
            row("2026-09-20T00:00:00Z", 600, model="c"), row("2026-10-25T00:00:00Z", 500, model="c")]   # c: this week
    assert [d["slug"] for d in derive.week_drops(rows, RATES, NOW)] == ["c"]
    assert [d["slug"] for d in derive.older_drops(rows, RATES, NOW)] == ["b", "a"]   # not c; the later change first
    assert derive.older_drops(rows[:2], RATES, datetime(2026, 12, 20, tzinfo=UTC)) == []   # past the 30-day look-back



def test_listing_days_are_change_points_of_the_end_of_day_state():
    rows = [row("2026-10-01T09:00:00Z", 1000), row("2026-10-01T18:00:00Z", 990),   # the last row of the day wins
            row("2026-10-02T00:00:00Z", 5, store="b"),
            row("2026-10-03T00:00:00Z", 990),                                      # unchanged: no point
            row("2026-10-04T00:00:00Z", 1, avail=False), row("2026-10-06T00:00:00Z", 990),
            row("2026-10-07T00:00:00Z", 950)]
    days = derive.listing_days(rows, "m")
    assert days[("s", "china", "12/256")] == [("2026-10-01", 990), ("2026-10-04", None), ("2026-10-06", 990), ("2026-10-07", 950)]
    assert days[("b", "china", "12/256")] == [("2026-10-02", 5)]


def test_listing_days_cover_all_rows_and_substores_stay_separate():
    rows = [row("2025-01-01T00:00:00Z", 1000), row("2025-01-01T00:00:00Z", 900, store="s_eu"),
            row("2026-10-02T00:00:00Z", 1, store="b"), row("2026-10-03T00:00:00Z", 7, avail=False, store="never")]
    days = derive.listing_days(rows, "m")
    assert days[("s", "china", "12/256")] == [("2025-01-01", 1000)]       # a stable listing from last year is there
    assert days[("s_eu", "china", "12/256")] == [("2025-01-01", 900)]     # not folded into s
    assert ("never", "china", "12/256") not in days                       # sold out from the start: nothing yet
