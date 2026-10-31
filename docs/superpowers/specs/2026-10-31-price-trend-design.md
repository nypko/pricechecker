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
  When low = high, the bar is replaced by "Same price since <date>".
- **Position line**:
  - today is the window's low → "Lowest price in 30 days" (or "Lowest price since <date>" when the window is shorter);
  - else → "€84 above its 30-day low (€2,652 on 12 Nov at Trading Shenzhen)" ("…above its low since <date>…" when
    shorter).
- **Trend line** (only with at least 7 days of history): "Down 9% since first listed (15 Oct)" when the first day is
  inside the window, else "Down 3% in the last 30 days"; plus "Up 4% in the last 7 days" when the 7-day move is at least
  2% in either direction. Moves under 1% are "about the same".
- **Too little history**: under 7 days with a price for this version and memory → only "Price history for this version
  and memory starts on 25 Oct, too short to judge yet." and no bar.
- **No current price** (not sold at this memory, sold out, no delivery for the settings) → the block is not shown.
- "≈" marks an approximate amount, with the same rule the price boxes use; money in the visitor's currency.
- A link "Full price history →" to the existing history page.

## 4. Data

- **Series**: for each phone, for the last 90 days, each store's lowest *store* price per UTC day, per version and
  memory, with availability: `{edition: {storage: {store: [[day, price, currency] …]}}}`, days with no in-stock listing
  left out. Built at site-build time from data/history/*.csv (already loaded for the history pages) and added to the
  phone's data file (the JSON phone.js already loads), not to the HTML.
- **Delivered per day**: the browser prices each point with the store's *current* shipping, fees and tax rules for the
  visitor's settings (pricing.js, as for current offers), then takes each day's minimum across stores. Using today's
  rules for past prices is a stated approximation (those rules rarely change); currency conversion uses today's rates.
- **Today** = the current best delivered price (the panel's row), so the block always agrees with the panel.

## 5. Code

- `price_trend(series, now_row, today, s)` in pricechecker/site/view.py and `priceTrend(...)` in static/js/view.js:
  pure, returns `{low, high, low_day, low_store, first_day, days, change_window, change_7d}` or None. Parity-tested
  (synthetic cases, not live).
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
- under 7 days of history → only the "too short" line;
- days with everything out of stock are skipped;
- low = high → "Same price since";
- no current price → no block.
Page tests: block sits right after `#pick-panel`, present without JS for the default pick, absent for a phone with no
current price; phone page within budget.

## 7. Rollout

Branch from main → testing site for the user to look at → "publish" = merge to main. No data migration.
