# Price Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Under the phone page's details panel, show where today's delivered price for the picked version and memory stands against its last 30 days: range bar, position line, trend line. Facts only.

**Architecture:** The build adds a per-listing daily price series (as ratios to the listing's current price) to each phone's data file. A pure `daily_best` (Python + JS) re-prices each day with today's rules for the visitor's settings and keeps the day's cheapest delivered total; a pure `price_trend` turns those days plus the panel's current row into the numbers; a `price_trend` block (Jinja macro + blocks.js, parity-tested) renders them. Server renders the default pick; phone.js repaints with the panel.

**Tech Stack:** Python 3.12 / Jinja2 / pytest; plain ES modules tested with node 22 (venv `.venv`).

**Spec:** `docs/superpowers/specs/2026-10-31-price-trend-design.md` (approved 2026-10-31).

## Global Constraints

- Judged on the **cheapest delivered price of each day** for the visitor's settings, picked version and memory; "today" = the panel's current best row, so the block always agrees with the panel.
- Window 30 days (today inclusive); shorter history → "since <date>" wording. Series kept for 90 days.
- Copy (exact): "Lowest price in 30 days" / "Lowest price since <date>"; "€84 above its 30-day low (€2,652 on 12 Nov at Trading Shenzhen)" / "…above its low since <date> (…)"; "Down 9% since first listed (15 Oct)" / "Down 3% in the last 30 days"; moves under 1% → "About the same since first listed (15 Oct)" / "About the same over the last 30 days"; 7-day line "Up 4% in the last 7 days" only when |move| ≥ 2%; range label "€2,736 · low €2,652 – high €2,901"; low = high → "Same price since <date>"; under 7 days → only "Price history for this version and memory starts on 25 Oct, too short to judge yet."; link "Full price history →".
- No advice wording, no forecast. No block when the pick has no current price.
- "≈" on approximate amounts by the price boxes' rule; money in the visitor's currency; dates in the site's short day format (as `pricechecker/site/pages/phone.py::_day`).
- Using today's shipping/fee/tax rules and today's currency conversion for past prices is the stated approximation.
- Every block = one Jinja macro + one blocks.js function, same structure/classes, in the text+structure parity test (`tests/test_blocks.py`).
- Static relative JS imports; escape interpolated strings; phone page HTML ≤ 60 KB (series lives in the data file).
- New tests synthetic (not `live`); `pytest -m "not live"` stays data-independent.
- Commits end with a blank line, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01BYAVrbwcDw6qv2MkP5jXH5`.

## Review Focus

1. A listing that disappears from the store (no current offer) but has history → its points are dropped, never priced with another listing's money (Task 1).
2. Settings where a store doesn't deliver or the payment method isn't accepted → that store's past days don't count, exactly as today's rows exclude it (Task 2).
3. Today's price lower than every past day but a past day had a cheaper store now gone → "Lowest price in 30 days" only when today ≤ every day in the window (Task 3).
4. A pick whose memory is "base" or whose history has a gap of several days → no crash; gaps are simply missing days (Tasks 2–3).
5. Visitor switches memory/version/settings quickly → block always matches the panel's version, memory and currency (Task 4 node case).

---

### Task 1: Daily price series in the phone data file

**Files:**
- Modify: `pricechecker/derive.py` (new function), `pricechecker/site/data_files.py:54-62` (`_phone_doc`)
- Test: `tests/test_derive.py`, `tests/test_data_files.py`

**Interfaces:**
- Produces: `listing_days(rows: list[dict], model_id: str, since: str) -> dict[tuple[str, str, str], list[tuple[str, float]]]` in derive.py: `{(store, edition, storage): [(day, lowest in-stock native price that day)]}` for days ≥ `since` (ISO date); state carries forward day to day like `store_lines`; sold-out days omitted; sub-stores NOT folded (each listing is its own offer).
- Produces: phone data file key `"trend": {edition: {storage: {store_id: [[day, ratio], …]}}}` where `ratio = round(past_native / current_native, 4)` against the same store/edition/storage offer's current native `price`; listings with no current offer are left out. `since` = 90 days before the build's `updated` day.

- [ ] **Step 1: Failing tests** — `test_listing_days_carries_state_and_skips_sold_out`: rows for one listing at 1000 (day 1), sold out (day 3), 950 (day 5) → `[(d1,1000),(d2,1000),(d5,950)]` given a row on d2 for another listing; `test_listing_days_keeps_substores_separate`. `test_phone_doc_trend_ratios`: synthetic SiteData with a current offer at 900 and history 1000 → 900 gives `[[d1,1.1111],[d2,1.0]]`; a listing with history but no current offer is absent (Review Focus 1).
- [ ] **Step 2: Run** `.venv/bin/python -m pytest -q tests/test_derive.py tests/test_data_files.py` — FAIL (names missing).
- [ ] **Step 3: Implement** `listing_days` and the `trend` key (store key = the offer's `store` id).
- [ ] **Step 4: Run** the same — PASS; `.venv/bin/python -m pytest -q -m "not live"` — PASS.
- [ ] **Step 5: Commit** `data files: per-listing daily price series for the price trend`

### Task 2: `daily_best` — re-price each day (Python + JS)

**Files:**
- Modify: `pricechecker/site/view.py`, `static/js/view.js`, `tests/js/view_cases.mjs`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: Task 1 `trend` shape; existing `rows(inputs, tax_cfg, s)` / `rows(inputs, tax, s)` and `best_of` / `bestOf`.
- Produces: `daily_best(inputs: list[dict], trend: dict, edition: str, storage: str, tax_cfg: dict, s) -> list[dict]` / `dailyBest(inputs, trend, edition, storage, tax, s)`: sorted by day, one `{day, total, store, approx}` per day that has at least one priced row; for each day, each store's point becomes its current offer input with every `money` amount (`eur`, `usd`, `gbp`, `cad`, `aud`; `_approx` flags kept) multiplied by the point's ratio, then `rows(...)` and `best_of(rows, edition, storage)` decide the day's best. `storage == "base"` uses the same exact-match rule as `best_of`.

- [ ] **Step 1: Failing tests** (synthetic offers, both languages via the existing view parity harness): ratio 1.1 scales the list price by 1.1 while shipping stays the same and tax is recomputed on the scaled price; a store that doesn't deliver to the settings' region contributes no days (Review Focus 2); a payment method the store refuses → excluded; a 4-day gap yields no entries for those days (Review Focus 4); Python result == JS result.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest -q tests/test_view.py` — FAIL.
- [ ] **Step 3: Implement** both mirrors line for line.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `view: daily best delivered price from the listing series (Python + JS)`

### Task 3: `price_trend` — the numbers (Python + JS)

**Files:**
- Modify: `pricechecker/site/view.py`, `static/js/view.js`, `tests/js/view_cases.mjs`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: Task 2 day list; the panel's row (`{total, approx, store}`).
- Produces: `price_trend(days: list[dict], now_row: dict | None, today: str) -> dict | None` / `priceTrend(days, nowRow, today)`. None when `now_row` is None. Otherwise, with today's point replaced by `now_row` (today = `now_row.total`, store `now_row.store`): `{"short": bool, "first_day", "window_start", "full_window": bool, "now", "low", "low_day", "low_store", "high", "is_low": bool, "change_pct": float | None, "since_first": bool, "change_7d": float | None, "approx": bool}`.
  - window = days from `today − 29` to today; `full_window` = first day with data ≤ window start; `short` = fewer than 7 distinct days with data.
  - `is_low` = now ≤ every total in the window; `low_day`/`low_store` = the most recent day at the window low.
  - `change_pct` vs the first day in the window (`since_first` true when that is the first day ever); `change_7d` vs the latest day ≤ today − 7, None if none.
  - `approx` = now or low approximate.

- [ ] **Step 1: Failing tests** (synthetic days; Python and JS each case): new low with full window; new low with 12 days ("since" wording flag `full_window` False); 5% above a low from 9 days ago (low_day/low_store = that day/store); a past cheaper day whose store is gone still counts so `is_low` False (Review Focus 3); 6 days of data → `short`; low = high; `change_7d` None when no day ≤ today−7; `now_row` None → None.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `view: price trend numbers over a 30-day window (Python + JS)`

### Task 4: `price_trend` block and phone page wiring

**Files:**
- Modify: `templates/_d/blocks.html`, `static/js/blocks.js`, `tests/js/render_blocks.mjs`, `static/d.css`, `templates/phone.html`, `pricechecker/site/pages/phone.py`, `static/js/phone.js`, `tests/js/phone_cases.mjs`
- Test: `tests/test_blocks.py`, `tests/test_pages.py`

**Interfaces:**
- Consumes: Tasks 2–3; `trend` from the phone data file (browser) and the same series built server-side for the default pick (phone.py calls the Task 1 builder on `data.rows`).
- Produces: macro `price_trend(t, s, hist_href)` / `priceTrend…` block function `priceTrendBlock(t, s, histHref)` rendering `<section class="trend" data-block="price_trend">` with, in order: range label (or "Same price since"), a bar `<div class="tbar" aria-hidden="true">` with a marker positioned by `(now − low) / (high − low)` as an inline `style="--at:NN%"` percentage, the position line, the trend line(s), the link; `t.short` → only the "too short" sentence and the link; `t` None → empty string. Placed in `#s-trend` directly after `#s-verdict` in templates/phone.html.

- [ ] **Step 1: Failing tests**: block parity (text + structure) for full window, short window, too short, same price, approx; exact copy from Global Constraints; page tests on the synthetic site: `#s-trend` follows `#s-verdict`, present for the default pick, absent for a phone with no current price; phone page ≤ 60 000 bytes. Node: after a memory/version/settings change the repainted block uses the new pick's series and currency (Review Focus 5).
- [ ] **Step 2: Run** `.venv/bin/python -m pytest -q tests/test_blocks.py tests/test_pages.py` — FAIL.
- [ ] **Step 3: Implement** macro, JS block, CSS (bar + marker, light and dark using existing tokens; marker uses the version colour), template slot, phone.py context `trend`, phone.js repaint in the same paint step as the panel.
- [ ] **Step 4: Run** full suite with `DOORPRICE_CHECK_BUDGETS=1` and `-m "not live"` — both PASS.
- [ ] **Step 5: Commit** `phone: price trend under the details panel (range bar, low, trend)`

### Task 5: Screenshots and testing site

- [ ] **Step 1:** `.venv/bin/python -m pricechecker.run --build-only --offline`; screenshots (tools/screenshots.sh flags) of a phone with ≥ 14 days of history and of the iPhone Duo (short history) at 390/1280 light/dark; fix material layout issues (CSS only), re-shoot.
- [ ] **Step 2:** Controller pushes the branch to `testing` (fast-forward push only; force-push is blocked in this environment — if `testing` is not an ancestor of the branch, ask the user to run the force-push), waits for the "Testing site" workflow, checks the phone page, hands the link to the user. Publish = merge to main on the user's word.
