# newsite backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data and code foundations direction D needs (one totals definition, monthly history, derived data,
full specs with a band check, split site package, versioned data files) without changing what doorprice.app shows.

**Architecture:** Pure modules (`pricing`, `derive`, `specs`) feed `site/` page modules; `pricing.py` is the totals
definition and `static/js/pricing.js` its tested mirror. History moves to monthly CSVs. Everything lands on branch
`newsite`; production keeps building from `main` until publish. D's templates and JS are a separate plan written after
the page-design spec (step 3).

**Tech Stack:** Python 3.12 (Jinja2, PyYAML, pytest), plain ES modules run by Node in tests, GitHub Actions, Cloudflare Pages.

**Spec:** `docs/superpowers/specs/2026-10-26-newsite-backend-design.md` (revised §4.1/§4.2 on 2026-10-27)

## Global Constraints

- Work on branch `newsite`; never push to `main` from this plan. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; author Ivaylo Kirov <i0kirov@gmail.com>.
- Run tests with `.venv/bin/python -m pytest -q` from the repo root; all 46 existing tests keep passing.
- Drop rule, unchanged: at least 3% **and** at least €20 (`telegram.MIN_PCT = 0.03`, `MIN_EUR = 20`).
- Ranking rule, unchanged: payment accepted first, then current over old (> 48 h), then fewer unknowns (unlisted shipping 2, tax that may still be due 1; a "from €10" shipping floor is known), then lower total.
- Specs come only from brand spec pages; `null` = "Not on <brand>'s page"; a version with no source = "not checked yet".
- EU main bands: LTE 1, 3, 7, 8, 20, 28; 5G n1, n3, n7, n8, n20, n28, n78.
- No new runtime dependencies. Node is used only by tests and tools (ubuntu-latest has it).
- Data format version is `v1`; data files are named `<name>.<10-char sha256>.json`.
- The live build output (`build/` from `python -m pricechecker.run --build-only --offline`) must stay page-for-page the same until the templates plan, except where a task says otherwise.

## Review Focus

- **A currency the store doesn't sell in** (money `<cur>_approx: 1`): the total is ECB-converted and marked approximate, never NaN or missing. Test in Task 1.
- **History across a month boundary**: a run at 23:59 UTC on 31 Oct and the next at 00:17 on 1 Nov write to `2026-10.csv` and `2026-11.csv` by row time, and "last known price" still sees the October row. Test in Task 4.
- **Telegram state written before this change** (no `posted` list): drops page marking simply shows no headline drops; nothing crashes. Test in Task 5.
- **A phone whose maker sells a version we have no spec page for**: band check returns `None` for it and the sheet says "not checked yet", while the other version still shows. Test in Task 6.
- **A courier's minimum fee in a non-euro currency** (Germany, DHL €15 minimum, shown in GBP): Python and JS agree to the cent. Case in Task 1's fixture, run by Task 2.

## Not in this plan (templates plan, after the page-design spec)

D's templates and `app.js` switch-over to `pricing.js`; the Drops page, `/phones/<id>/specs` pages and monthly history
pages (`/history/<id>/<yyyy-mm>`); HTML page budgets (phone ≤ 60 KB, home ≤ 120 KB) and the internal link check; the
`newsite.yml` switch from the mockup preview to the real build. This plan only produces the data those pages read.

---

### Task 1: `pricing.py`, the totals definition

**Files:**
- Create: `pricechecker/pricing.py`
- Create: `tests/fixtures/pricing_cases.json`
- Create: `tests/test_pricing.py`

**Interfaces:**
- Consumes: the offer dicts `site.build` already makes for pages (keys `money`, `pay`, `pay_ok`, `ship`, `duties`, `promo`, `old`, `notes`), and `site._tax_config(rates)` output (`regions` dict with `EU.countries[*].fee.min_m`, `CA.provinces`).
- Produces:
  - `Settings = NamedTuple(region: str, area: str, pay: str, cur: str)` — `area` = EU country code, CA province code or `""`; `cur` lowercase (`"eur"`).
  - `TaxRule = NamedTuple(rate: float | None, name: str, fee: dict | None, ship_taxed: bool)`; `tax_rule(tax_cfg: dict, s: Settings) -> TaxRule`
  - `Cost` dataclass: `list, promo_amt, promo_pct, base, adj, adj_amt, ship (float|None), ship_min, tax_est (float|None), tax_added, total, approx, complete, pay_ok, old, duties`
  - `cost(offer: dict, s: Settings, rule: TaxRule) -> Cost`
  - `unknowns(c: Cost) -> int`, `better(a: Cost, b: Cost) -> bool`, `rank(offers: list[dict], s: Settings, rule: TaxRule) -> list[tuple[dict, Cost]]` (in-stock, non-`base` storage only, best first)
  - `left_out(c: Cost) -> str` — `""`, `"shipping"`, `"import tax"`, `"shipping and import tax"` (the `left` field deals.json and Telegram use)

- [ ] **Step 1: Write the fixture and failing tests.** `pricing_cases.json` is a list of `{"name", "offer", "settings": [region, area, pay, cur], "expect": {total, tax_added, unknowns, approx, pay_ok}}`, plus a top-level `"tax"` block copied from `_tax_config` output for EU (BG, DE), UK, CA (ON). Cases, each transcribed from `app.js cost1()`/`taxRule1()`:
  1. `card_free_ship_tax_paid`: €1,037 + €10 shipping floor (`min: true`), duties true → total 1047.00, approx true, unknowns 0.
  2. `ship_not_listed`: €1,005.95, ship null, duties null → total 1005.95, unknowns 3.
  3. `duties_false_eu_avg`: €900, ship €20, duties false, EU `""` (21%) → tax_added 193.20, total 1113.20.
  4. `de_fee_minimum_gbp`: £500 phone, ship £0, duties false, EU `DE`, `gbp` → tax 95.00 + fee max(1.90, min_m.gbp) — expect the fixture's `min_m.gbp` value.
  5. `ca_on_ship_not_taxed`: C$1,000 + C$60 shipping, duties false, CA `ON` 13% → tax_added 130.00, total 1190.00.
  6. `bank_vs_sale_no_stack`: list €1,000, promo 2% `stacks_with_bank: false`, bank −4.75% → promo 0, adj −47.50, total 952.50.
  7. `paypal_refused`: `pay_ok.paypal: false` → pay_ok false.
  8. `currency_approx`: `money.aud_approx: 1` → approx true.

  `tests/test_pricing.py`:
  ```python
  CASES = json.loads(Path("tests/fixtures/pricing_cases.json").read_text())
  @pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["name"])
  def test_case(case):
      s = pricing.Settings(*case["settings"]); c = pricing.cost(case["offer"], s, pricing.tax_rule(CASES["tax"], s))
      assert round(c.total, 2) == case["expect"]["total"]
      assert pricing.unknowns(c) == case["expect"]["unknowns"] ...   # and tax_added, approx, pay_ok when present
  def test_better_order():   # pay_ok beats price; current beats old; fewer unknowns beat €8 cheaper; then price
  ```
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_pricing.py -q` — expect `ModuleNotFoundError: pricechecker.pricing`.
- [ ] **Step 3: Implement `pricing.py`** as a line-for-line port of `app.js` `taxRule1()`, `cost1()`, `maybeTax()`, `unknowns()`, `better()` (static/app.js:95-146, 186-201). Keep their comments. No I/O.
- [ ] **Step 4: Run** the same command — expect all cases PASS.
- [ ] **Step 5: Commit** `pricing.py: the delivered-total rule as one pure module, with shared test cases`.

### Task 2: `pricing.js` mirror, checked against the same cases

**Files:**
- Create: `static/js/pricing.js` (ES module, no DOM)
- Create: `tests/js/pricing_cases.mjs`
- Modify: `tests/test_pricing.py` (one test that runs node)
- Modify: `.github/workflows/newsite.yml` (add `pytest` before deploy, like `testing.yml`)

**Interfaces:**
- Consumes: `tests/fixtures/pricing_cases.json` (Task 1).
- Produces: `export function taxRule(taxCfg, s)`, `cost(offer, s, rule)`, `unknowns(c)`, `better(a, b)`, `leftOut(c)` with `s = {region, area, pay, cur}` — same names camelCased, same fields as `Cost` camelCased (`taxAdded`, `promoAmt`, …).

- [ ] **Step 1: Write `tests/js/pricing_cases.mjs`**: imports `../../static/js/pricing.js`, runs every case, prints `FAIL <name> <field> got <x> want <y>` per mismatch and exits 1 if any, else prints `ok <n>`.
- [ ] **Step 2: Add to `tests/test_pricing.py`:**
  ```python
  @pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
  def test_js_mirror_matches_cases():
      r = subprocess.run(["node", "tests/js/pricing_cases.mjs"], capture_output=True, text=True)
      assert r.returncode == 0, r.stdout + r.stderr
  ```
  Run it — expect FAIL (module not found).
- [ ] **Step 3: Implement `static/js/pricing.js`** by moving the bodies of `taxRule1`/`cost1`/`unknowns`/`better` out of `app.js` into exported functions taking `s` and the tax config as arguments instead of closing over `state`/`TAX`. Leave `app.js` untouched in this task (the templates plan switches it over).
- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/test_pricing.py -q` — expect PASS, including the node test.
- [ ] **Step 5: Add a `- run: python -m pytest -q` step** (with `setup-python` and `pip install -r requirements.txt`) before the deploy step in `newsite.yml`.
- [ ] **Step 6: Commit** `pricing.js: browser mirror of pricing.py, held to the same cases in CI`.

### Task 3: One-off parity run against today's `app.js`, then switch Python callers

**Files:**
- Create: `tools/parity_appjs.mjs` (loads `static/app.js` source, extracts `taxRule1`, `cost1`, `maybeTax`, `unknowns`, `better` with a regex into a `vm` context that supplies `state`, `TAX`, `EU_C`, `CA_P`, `fmt`; reads offers JSON from stdin; prints costs as JSON lines)
- Create: `tools/parity.py` (for every `build/phones/*.html`, every offer in its `id="offers"` JSON, every settings combination from `_tax_config`: compare `pricing.cost` with the node output; writes a report)
- Create: `docs/superpowers/notes/2026-10-27-pricing-parity.md` (the report)
- Modify: `pricechecker/site.py` `_title_price` → thin wrapper over `pricing.rank(offers, Settings("EU", "", "card", "eur"), rule)`
- Test: `tests/test_site.py::test_title_price_prefers_known_shipping_over_a_slightly_lower_unknown` (unchanged, must still pass)

**Interfaces:**
- Consumes: Task 1 `pricing.rank`, `pricing.left_out`, `pricing.tax_rule`.
- Produces: `_title_price(offers, tax_cfg, with_offer=False)` — **signature change**: takes the tax config dict, not `tax_eu_pct`; returns `(total, complete, left)` or `(…, offer)` exactly as today.

- [ ] **Step 1:** Build offline, then run `node tools/parity_appjs.mjs` via `python tools/parity.py`. Expected: a report listing every (offer, settings) whose total differs by ≥ €0.01 between `pricing.py` and `app.js`. Target: zero differences. A difference means the port in Task 1 is wrong; fix `pricing.py` (and add the case to the fixture) until zero.
- [ ] **Step 2:** In the same report, list where today's `_title_price` differs from `pricing.rank` for EU/card/euro (expected: phones with courier-fee countries are unaffected at EU average; differences come from sale-vs-bank rules only if any). Commit the report.
- [ ] **Step 3:** Replace `_title_price`'s body with the `pricing` call; update its two callers in `site.build` and `deals.json` writing to pass `tax_cfg`. Run the full suite — expect PASS.
- [ ] **Step 4:** Build offline before and after; `diff -r` the two `build/` trees. Expected: no differences, or only the titles/JSON-LD prices the report predicted. Note them in the report.
- [ ] **Step 5: Commit** `site: page titles, deals.json and Telegram use pricing.py; parity report vs app.js`.

### Task 4: History in monthly files

**Files:**
- Modify: `pricechecker/history.py`
- Modify: `pricechecker/indexnow.py:21` (`changed_slugs` reads the last two months)
- Create: `tools/split_history.py` (one-off migration)
- Create: `tests/test_history.py`
- Data: `data/history/2026-10.csv`, `data/history/last.json`; delete `data/history.csv` in the migration commit

**Interfaces:**
- Produces:
  - `HISTORY_DIR = Path("data/history")`, `LAST = HISTORY_DIR / "last.json"` (`{"store|model|edition|storage": [price, available]}`)
  - `month_file(ts: str) -> Path` (`"2026-10-31T23:59:00Z"` → `data/history/2026-10.csv`)
  - `append(rows: list[list]) -> None` (groups rows by their own time; header on new files; updates `last.json` after the CSVs)
  - `load_history(months: int | None = None) -> list[dict]` (None = all files in order; `months=3` = the newest three files)
  - `save(...)` unchanged signature; uses `last.json` instead of reading all history.

- [ ] **Step 1: Write tests** in `tests/test_history.py` (use `monkeypatch.chdir(tmp_path)`):
  - `test_append_splits_by_row_month`: rows stamped `2026-10-31T23:59:00Z` and `2026-11-01T00:17:00Z` land in `2026-10.csv` and `2026-11.csv`; each file has one header.
  - `test_last_known_price_crosses_months`: after the October row, `save()` with the same price on 1 Nov writes no row.
  - `test_load_history_months`: three month files; `load_history(months=2)` returns only the newest two, oldest first.
  - `test_split_roundtrip`: `tools/split_history.py` on a sample `history.csv`, then `load_history()` equals the original rows in order.
- [ ] **Step 2: Run** `pytest tests/test_history.py -q` — expect FAIL.
- [ ] **Step 3: Implement** the interface above; `site.build` calls `load_history(months=3)` for charts/trends/drops and `load_history()` only for history pages' change lists. `indexnow.changed_slugs` reads `load_history(months=2)`.
- [ ] **Step 4: Run** the full suite — expect PASS.
- [ ] **Step 5: Migrate:** `python tools/split_history.py`; check row counts match `wc -l data/history.csv` minus header; `git rm data/history.csv`. Build offline and diff against Task 3's build — expected: identical except history pages, which are equal while all data is < 3 months old.
- [ ] **Step 6: Commit** `history: monthly files plus last-known prices; migrate data/history.csv`.
  Note for publish: the hourly workflow on `main` still writes `data/history.csv` until merge; the publish step reruns the migration on main's latest data.

### Task 5: `derive.py` — store lines, drops, gap, sale split

**Files:**
- Create: `pricechecker/derive.py`
- Modify: `pricechecker/telegram.py` (`changes()` also returns posted drops; state gains `"posted": [{"slug", "at", "was", "eur"}]`, last 14 days kept)
- Create: `tests/test_derive.py`

**Interfaces:**
- Consumes: `history.load_history(months=3)` rows (`time, store, model_id, edition, storage, price, currency, available`), `fx` rates, Task 1 `pricing`.
- Produces:
  - `store_lines(rows, model_id: str, edition: str, rates: dict) -> dict[str, list[tuple[str, float]]]` — `{store_id: [(yyyy-mm-dd, lowest EUR price that day), …]}`, state carried day to day, sub-stores (`x_eu`) folded into `x`, sold-out listings excluded.
  - `listing_drops(rows, rates, now: datetime, window_days: int = 7) -> list[dict]` — `{slug, store, edition, storage, then, now, pct, eur, when, real: bool}`; `real` = pct ≤ −3 and saving ≥ €20.
  - `mark_headline(drops: list[dict], telegram_state: dict, now) -> list[dict]` — adds `headline: True` where `posted` has the slug within the window.
  - `gap(offers: list[dict], rule) -> dict | None` — `{storage, china, global, diff}`: cheapest settled total per version at the same storage, the storage where China is cheapest; `None` when no storage has both.
  - `promo_split(offer: dict, cur: str) -> tuple[float, float, float]` — (list price, sale amount, price paid).

- [ ] **Step 1: Write tests** (hand-made rows, no files):
  - `test_store_joining_is_not_a_drop` (new store at a lower price → no drop).
  - `test_drop_thresholds` (−2.9% → `real` False; −3.1% but €15 → False; −3.5% and €40 → True).
  - `test_sub_store_folds_into_parent_line`.
  - `test_gap_same_storage_only` (China cheapest at 12/256 has no Global there; gap uses 12/512) and `test_gap_none_without_shared_storage`.
  - `test_mark_headline_without_posted_key` (old Telegram state → no `headline`, no error).
  - `test_promo_split` (1056.95, 2% → (1056.95, 21.14, 1035.81)).
- [ ] **Step 2: Run** `pytest tests/test_derive.py -q` — expect FAIL.
- [ ] **Step 3: Implement**; extend `telegram.changes()` to append to `posted` and prune entries older than 14 days; update `test_telegram_posts_real_drops_only` to assert `st["posted"]` after the −€40 drop.
- [ ] **Step 4: Run** the full suite — expect PASS.
- [ ] **Step 5: Commit** `derive: per-store lines, listing drops (Telegram headline drops marked), China/Global gap, sale split`.

### Task 6: Full specs per phone and the band check

**Files:**
- Create: `config/specs/<id>.yaml` for all 77 catalog ids (key specs migrated from `config/specs.yaml`; full sheets for `oppo-find-x9-ultra`, `oneplus-16`, `google-pixel-11-pro` transcribed from `~/Work/doorprice-redesign/mock/specs.js`)
- Create: `config/region_bands.yaml`
- Create: `pricechecker/specs.py`
- Create: `tools/migrate_specs.py` (one-off)
- Delete: `config/specs.yaml`
- Modify: `pricechecker/site.py` (read key specs through `specs.load()`), `tests/test_site.py::test_specs_config_uses_catalog_ids`
- Create: `tests/test_specs.py`

**Interfaces:**
- Produces:
  - File schema: `id`, `sources: {china|global: {url, checked: YYYY-MM-DD, lang?}}`, `key: {chip, screen, battery, charging}`, `groups: {display|performance|battery|cameras|video|build|connectivity|software|other: {field: value}}`, `bands: {china|global: {lte: [int], nr: [int]}}`. A value is a string, `null`, `{china: str|null, global: str|null}` (pages disagree) or `{value: str, from: china|global}` (one page lists the same hardware fact).
  - `GROUPS: tuple[str, ...]` in the order above; `FIELDS: dict[str, tuple[str, ...]]` — the allowed field names per group (from the three transcribed sheets; adding a field means adding it here).
  - `load(dir=Path("config/specs")) -> dict[str, dict]`; `validate(sheet: dict) -> list[str]` (problems, empty = valid)
  - `band_check(sheet: dict, edition: str, region: str = "EU") -> dict | None` — `{"lte": [missing], "nr": [missing], "why": {band: text}}`; `None` when that version has no `bands`.
  - `differences(sheet: dict) -> int` — fields where both halves are non-null and differ.

- [ ] **Step 1: Write tests** in `tests/test_specs.py`:
  - `test_every_catalog_phone_has_a_valid_sheet` (every id in `catalog.yaml` has a file; `validate` returns `[]`).
  - `test_oneplus16_china_misses_eu_800mhz`: `band_check(sheets["oneplus-16"], "china")` → `lte == [20]`, `nr == [20]`.
  - `test_x9_ultra_china_has_main_eu_bands`: both lists empty.
  - `test_unread_version_is_none`: `band_check(sheets["oppo-find-x9-ultra"] minus china bands, "china") is None`.
  - `test_x9_ultra_has_7_differences`.
  - `test_validate_rejects_unknown_field_and_third_party_source`: a field not in `FIELDS` and a source URL whose host isn't in `specs.BRAND_HOSTS` for the phone's brand (`{"oppo": ("oppo.com",), "oneplus": ("oneplus.com",), "google": ("google.com",), …}`, one entry per catalog brand) each produce a problem.
- [ ] **Step 2: Run** `pytest tests/test_specs.py -q` — expect FAIL.
- [ ] **Step 3: Implement** `specs.py`, `region_bands.yaml` (EU lists from Global Constraints; `why: {20: "800 MHz: rural coverage and indoors in most EU countries", 28: "700 MHz: wide-area 4G/5G in many EU countries", 78: "3.5 GHz: the main EU 5G band"}`), run `tools/migrate_specs.py` (keeps each phone's `source:` note as a YAML comment), add the three full sheets, delete `config/specs.yaml`, point `site.build` at `specs.load()`.
- [ ] **Step 4: Run** the full suite and an offline build; diff `build/` with Task 5's — expected: identical (key specs unchanged).
- [ ] **Step 5: Commit** `specs: one file per phone with full sheets from brand pages and an EU band check`.

### Task 7: Fetching brand spec pages and watching them

**Files:**
- Create: `pricechecker/specpages.py`
- Create: `.github/workflows/spec-pages.yml` (weekly, Monday 06:23 UTC, plus manual)
- Create: `data/spec_pages/` (text snapshots, committed)
- Create: `tests/test_specpages.py`

**Interfaces:**
- Consumes: Task 6 `specs.load()` (`sources` URLs).
- Produces:
  - `page_text(html: str) -> str` (scripts/styles stripped, one trimmed line per text node, empty lines dropped)
  - CLI `python -m pricechecker.specpages fetch <id> [--edition china|global]` — renders with local `chromium --headless=new --dump-dom --virtual-time-budget=15000`, writes `data/spec_pages/<id>-<edition>.txt`. Local only; exits with a clear message if `chromium` is missing.
  - CLI `python -m pricechecker.specpages watch` — for each saved snapshot, plain HTTP GET with `http.USER_AGENT`; when `page_text` of the response differs from the snapshot (ignoring lines that are only digits/whitespace), appends the phone to `.spec_report.md`. Pages that need JavaScript (response text < 500 chars) are listed as "check by hand", never failed.

- [ ] **Step 1: Write tests:** `test_page_text_strips_scripts_and_blank_lines`, `test_watch_reports_changed_text_only` (monkeypatched fetch: same text → no report; changed spec line → report names the phone; short JS shell → "check by hand").
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement**; workflow runs `watch` and opens/comments one issue titled "Spec pages changed (<date>)" exactly like the "Store terms changed" step in `hourly.yml`.
- [ ] **Step 4:** Fetch the three sample phones' pages locally (four snapshots: X9 Ultra both versions, OnePlus 16 China, Pixel 11 Pro Global); run the suite — expect PASS.
- [ ] **Step 5: Commit** `specpages: fetch brand spec pages locally, weekly watch for changes`.

### Task 8: Split `site.py` into a package

**Files:**
- Create: `pricechecker/site/__init__.py` (`build()` and re-exports of every name tests import: `_title_price`, `_tax_config`, `_models`, `_trend`, `_stats`, `_chart`, `_ticks`, `_spec_parts`, `ed_labels`, `spec`, `_ship_cell`, `_too_old`)
- Create: `pricechecker/site/context.py` (loading config/data once: catalog, stores, rates, latest, history rows, tax config, specs → one `SiteData` dataclass)
- Create: `pricechecker/site/offers.py` (the per-phone offer assembly loop now in `build()`)
- Create: `pricechecker/site/charts.py` (`_chart`, `_series`, `_charts`, `_all_stats`, `_tier_chart`, `_trend`, `_stats`, `_ticks`)
- Create: `pricechecker/site/seo.py` (`_seo_files`, `_feeds`, `_product_ld`, titles)
- Create: `pricechecker/site/pages/{home,phone,history,compare,stores,static}.py` — each `render(env, data, ctx) -> dict[path, html]`
- Create: `pricechecker/site/cards.py` (moved from `pricechecker/cards.py`; keep a shim import)
- Delete: `pricechecker/site.py`

**Interfaces:**
- Produces: `pricechecker.site.build(catalog, stores_cfg, rates_info, terms_status=None) -> None` (unchanged); page modules take plain data and return `{relative_path: html}`; only `__init__.build` writes files.

- [ ] **Step 1:** Build offline on the current code; copy `build/` to `$CLAUDE_JOB_DIR/tmp/build-before`.
- [ ] **Step 2:** Move code without changing behaviour, one module at a time, running `pytest -q` after each move.
- [ ] **Step 3:** Build offline; `diff -r build-before build` — expected: no differences.
- [ ] **Step 4:** `ruff check pricechecker tests` with a scratch-venv ruff (defaults) — expected: clean.
- [ ] **Step 5: Commit** `site: split into a package (context, offers, charts, seo, one module per page); output unchanged`.

### Task 9: Versioned data files and their budgets

**Files:**
- Create: `pricechecker/site/data_files.py`
- Modify: `pricechecker/site/__init__.py` (call it; add `/data/v1/*` with a one-year immutable cache rule to `_headers`)
- Create: `tests/test_data_files.py`

**Interfaces:**
- Consumes: Task 1 `pricing` (field names), Task 5 `derive.store_lines`, Task 6 `specs.band_check`, Task 8 `SiteData`.
- Produces:
  - `offer_inputs(o: dict) -> dict` — exactly what `pricing.js cost()` reads: `money` (5 currencies + `_approx` flags), `pay`, `pay_ok`, `ship` (per region, per currency, `min`), `duties`, `promo` (`pct`, `stacks_with_bank`, `label`), `old`, plus display fields `store_label`, `edition`, `storage`, `link`, `days`, `trust`.
  - `write(data: SiteData, out: Path) -> dict[str, str]` — writes `data/v1/phone/<id>.<hash>.json` (`{"v": 1, "offers": [...], "lines": {edition: {store_label: [[date, eur], ...]}}, "bands": {edition: band_check or null}}`), `data/v1/home.<hash>.json` (`{"v": 1, "phones": [{id, editions: {edition: offer_inputs of its best EU/card offer}}]}`), `data/v1/tax.<hash>.json`; returns `{logical name: published path}` for templates.
- [ ] **Step 1: Write tests:** `test_hash_names_change_with_content`, `test_phone_file_has_no_notes_text` (notes stay in HTML), `test_budgets` (after an offline build: every file under `build/data/v1/` ≤ 60,000 bytes), `test_offer_inputs_feed_pricing_js` (dump one phone's file, run it through `node tests/js/pricing_cases.mjs --offers <file>` mode; totals equal `pricing.cost` for EU/card/eur).
- [ ] **Step 2: Run** — expect FAIL.
- [ ] **Step 3: Implement**; add the `--offers` mode to `tests/js/pricing_cases.mjs`.
- [ ] **Step 4: Run** the full suite and an offline build — expect PASS; existing pages unchanged (new files only).
- [ ] **Step 5: Commit** `site: versioned data files for the browser (phone, home, tax) with size budgets`.

### Task 10: Close out

**Files:**
- Modify: `docs/superpowers/specs/2026-10-26-newsite-backend-design.md` (§6 build order: mark 1–6 done with commit hashes)
- Modify: `README.md` (history layout, specs files, specpages CLI, pricing mirror rule)

- [ ] **Step 1:** Full suite, offline build, `node tests/js/pricing_cases.mjs` — all pass.
- [ ] **Step 2:** Push `newsite`; confirm the `newsite preview` workflow (now with tests) succeeds.
- [ ] **Step 3: Commit** `docs: newsite backend done; README for history, specs and pricing`.
