# Phone page: price trend ("Buy now or wait?")

Status: DRAFT, 2026-10-31, awaiting approval. Designed in conversation on 2026-10-31.

## 1. Problem

A visitor about to buy sees today's delivered price but cannot tell whether it is a good moment: was it cheaper last week,
is it falling, is today's price high for this phone? The site records every store price change hourly (data/history,
since 15 Oct 2026) but only shows it on the separate history page, as store prices before shipping and tax.

## 2. Goal

Under the details panel, for the picked version and memory, show where today's delivered price stands against its own
recent history: the period's low and high, a range bar with today's price on it, and the trend. Facts only.

Not goals: advice wording ("good time to buy", "wait"), forecasts, price alerts (email or Telegram; a later spec), any
change to prices, ranking, the `<title>`, the price boxes or the history page.

## 3. What it shows

A block `price_trend` directly under the details panel (`#pick-panel`), for the picked version and memory, judged on the
**cheapest delivered price of each day** across stores, for the visitor's settings (the same total the panel shows).

- **Range bar** over the window (30 days, or since the first day with a price if shorter): a horizontal bar from the
  window's low to its high with a marker at today's price, labelled "€2,736 · low €2,652 – high €2,901".
  The high gets "≈" when the high day's total is approximate. Totals are compared as displayed (whole units, half up),
  so two prices that show the same are the same. When low = high there is no bar, no position line and no trend line:
  only "Same price for 30 days" (history reaches back to the window's start) or "Same price since <date>".
- **Position line**:
  - today is the window's low → "Lowest price in 30 days" (or "Lowest price since <date>" when the window is shorter);
  - else → "€84 above its 30-day low (€2,652 on 12 Nov at Trading Shenzhen)" ("…above its low since <date>…" when
    shorter).
- **Trend line** (only with at least 7 days of history): "Down 9% since first listed (15 Oct)" when the first day is
  inside the window, else "Down 3% in the last 30 days"; plus "Up 4% in the last 7 days" when the 7-day move (against the
  latest day 7 to 14 days back) is at least 2% in either direction. Moves under 1% are "about the same".
- **Too little history**: under 7 days with a price inside the window (today included) →
  - history starts inside the window: only "Price history for this version and memory starts on 25 Oct, too short to
    judge yet." and no bar;
  - history starts before the window (the pick was away for a while): only "Not enough recent price history for this
    version and memory to judge yet." and no bar.
- **No current price** (not sold at this memory, sold out, no delivery for the settings) → the block is not shown.
- "≈" marks an approximate amount, with the same rule the price boxes use; money in the visitor's currency.
- A link "Full price history →" to the existing history page.

## 4. Data

- **Series**: for each phone, each listing's end-of-day store price per UTC day, stored as change points over the full
  history: `{edition: {storage: {store_label: {"cur": "eur", "pts": [[day, ratio] …]}}}}`. `ratio` is the listing's
  native price over its current native price; a point is written on the listing's first day and whenever the
  end-of-day ratio changes, `[day, null]` when it goes out of stock (`[day, ratio]` again when it returns). Built at
  site-build time from the full history (data.rows_all) and added to the phone's data file (the JSON phone.js already
  loads), not to the HTML. `cur` is the listing's native currency.
- **Per day**: `daily_best`/`dailyBest` expand the points by carrying each listing's last ratio forward day by day up
  to today (null: no price that day; nothing before a listing's first point).
- **Delivered per day**: the browser prices each point with the store's *current* shipping, fees and tax rules for the
  visitor's settings (pricing.js, as for current offers), then takes each day's minimum across stores. Using today's
  rules for past prices is a stated approximation (those rules rarely change); currency conversion uses today's rates.
  The amounts of a past day in any currency other than the listing's native one are estimates and flagged approximate.
- **Today** = the current best delivered price (the panel's row), so the block always agrees with the panel.

## 5. Code

- `daily_best(inputs, trend, edition, storage, tax_cfg, s, today)` and `price_trend(days, now_row, today)` in
  pricechecker/site/view.py, `dailyBest` / `priceTrend` in static/js/view.js: pure, line-for-line mirrors. `price_trend`
  returns `{short, recent_gap, first_day, window_start, full_window, now, low, low_day, low_store, high, high_approx,
  is_low, change_pct, since_first, change_7d, approx}` or None (no current price). Parity-tested (synthetic cases, not
  live).
- Block `price_trend` = Jinja macro in templates/_d/blocks.html + function in static/js/blocks.js, text+structure
  parity-tested in tests/test_blocks.py like every block.
- Server renders it for the default pick and default settings (no-JS visitors see it); phone.js repaints it with the
  panel on every pick or settings change.
- CSS in static/d.css: range bar with marker, light and dark; marker has a text equivalent (the label), the bar is
  `aria-hidden`.
- Budget: phone page HTML stays ≤ 60 KB (the series lives in the lazily loaded data file).

## 6. Testing

Synthetic history, both languages, parity:
- today is a new low (window full / window shorter than 30 days);
- above a recent low (position line names day and store);
- rising and falling trend; 7-day move under and over 2%;
- under 7 days of history in the window → only the "too short" line; a pick back after 35 days away → "Not enough
  recent price history…";
- totals compared at display precision (two stores 0.07 apart → no "€0 above" line);
- 7-day move only against a day 7 to 14 days back;
- days with everything out of stock are skipped;
- low = high → "Same price for 30 days" / "Same price since <date>", also after a different price before the window;
- no current price → no block.
Page tests: block sits right after `#pick-panel`, present without JS for the default pick, absent for a phone with no
current price; phone page within budget.

## 7. Rollout

Branch from main → testing site for the user to look at → "publish" = merge to main. No data migration.
