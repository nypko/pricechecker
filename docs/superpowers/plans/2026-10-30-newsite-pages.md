# newsite pages (direction D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild every page of DoorPrice in direction D on branch `newsite`, with `static/app.js` replaced by small ES modules and each settings-dependent block defined once in Jinja and once in JS, held equal by a test.

**Architecture:** Python/Jinja renders full HTML for the default settings from a shared view model (`pricechecker/site/view.py`) built on `pricing.py`. The browser mirrors that view model (`static/js/view.js`, on `pricing.js`) and re-renders the same blocks through `static/js/blocks.js` only when the visitor's settings differ from the defaults, loading offer inputs from `build/data/v1/`. A node harness renders each block from the same data and a pytest compares its text with the server HTML.

**Tech Stack:** Python 3.12, Jinja2, pytest; plain ES modules (node 22 for tests); headless chromium for screenshots; Cloudflare Pages branch `newsite`.

**Spec:** `docs/superpowers/specs/2026-10-30-newsite-pages-design.md` (approved 2026-10-30). Mockups: `newsite-preview/d-*.html` (the visual reference for every D block; port their CSS and markup, not their data code).

## Global Constraints

- Default settings: `Settings("EU", "", "card", "eur")`. Server HTML always shows these; JS changes nothing when the saved settings equal them.
- Budgets (before gzip): phone page ≤ 60 KB HTML, home ≤ 120 KB, any one data file ≤ 60 KB. Nothing large embedded in HTML: `offers_json`, `all_json`, `compare` cells and the inline `import-tax` JSON are removed from templates.
- Store links: `rel="sponsored nofollow noopener"`, `target="_blank"`.
- Copy rules: "≈" for estimated totals; tails exactly "+ shipping", "+ tax?", "+ shipping, tax?"; "✓ delivered, tax settled"; "View at <store>"; buy bar button "View deal"; affiliate line "Affiliate link: we may earn a commission; it never changes the order."
- Drops rule: same store + version + memory, ≥ 3% and ≥ €20 over 7 days (`derive.listing_drops`); Telegram mark = `derive.mark_headline`.
- Settings keep the live localStorage keys (`pc-region`, `pc-country`, `pc-prov`, `pc-pay`, `pc-cur`, watch list `pc-watch`) so returning visitors keep their choice. Regions: EU, UK, US, CA, AU and Global ("Elsewhere", kept from live).
- Live URLs keep working: `/`, `/phones/<id>`, `/history/<id>`, `/compare`, `/stores`, `/stores/<id>`, `/about`, `/methodology`, `/privacy`, 404. New: `/drops`, `/phones/<id>/specs`, `/history/<id>/<YYYY-MM>`.
- No Google Fonts or other third-party requests from pages (Cloudflare Web Analytics auto-inject excepted).
- Colours: China red, Global blue, verdict ink (never blue), history series `--s1..--s6`; all tokens defined for light and dark.
- `<title>` rules unchanged from live (`seo` and the phone title rules from 2026-10-25).
- Lint: ruff defaults clean (scratch venv ruff, as before). Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Saved settings from the live site** (e.g. `pc-region=CA`, `pc-prov=ON`, `pc-cur=cad`): the new pages must read them and show Canadian totals, not reset to EU. Test in Task 3.
2. **A phone whose cheapest offer is stale or sold out**: never the headline, price box, verdict or buy bar; the next current offer leads, and with none the box says why. Test in Task 4 (state fixture).
3. **Region with no delivering store** (Gomibo-only Pixel with ship-to US): price box shows "Doesn't deliver to the US", no total, no button; the home row shows "–". Test in Task 4 and Task 6.
4. **Memory chosen on one version that the other lacks** (switching China → Global on the phone page or a shared compare memory): falls back to that version's best memory instead of an empty verdict. Tests in Task 5 and Task 9.
5. **History month with no changes / phone added this month**: monthly page list is empty but renders ("No price changes this month"), and no link to a month before the phone's first row. Test in Task 10.

---

### Task 1: D assets, build fixture and the newsite preview of the real build

**Files:**
- Create: `static/fonts/schibsted-grotesk-{500,600,700,800}.woff2`, `static/fonts/albert-sans-{400,500,600,700}.woff2` (Latin subset, from `@fontsource/schibsted-grotesk` and `@fontsource/albert-sans` on jsDelivr, pinned versions noted in `static/fonts/README`), append their OFL notice to `static/fonts/OFL.txt`
- Create: `static/d.css` (from `newsite-preview/{switch,sheet,c,d}.css`, `@font-face` for the files above, tokens on `:root` + `@media (prefers-color-scheme: dark)`)
- Create: `tests/conftest.py`
- Modify: `pricechecker/site/context.py:96` (asset hashes), `pricechecker/site/__init__.py:107-114` (`_headers`)
- Modify: `.github/workflows/newsite.yml` (deploy the build, not `newsite-preview/`)
- Test: `tests/test_pages.py`

**Interfaces:**
- Produces: session fixture `site_build(tmp_path_factory) -> Path` in `tests/conftest.py`: monkeypatches `pricechecker.site.OUT` to a temp dir, runs `site.build(catalog, stores, fx.cached(), terms.saved_status())` offline once per session, returns the build dir. Later tasks read pages from it.
- Produces: `ctx["asset_v"]` keyed by path relative to `static/`, covering `d.css` and every `js/*.js`; templates link `{{ root }}static/js/<name>.js?v={{ asset_v['js/<name>.js'] }}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_pages.py`

```python
def test_d_css_and_fonts_are_built(site_build):
    assert (site_build / "static/d.css").exists()
    assert (site_build / "static/fonts/albert-sans-400.woff2").exists()

def test_no_page_calls_google_fonts(site_build):
    for f in site_build.rglob("*.html"):
        assert "fonts.googleapis" not in f.read_text(), f

def test_headers_cache_js_modules_and_d_css(site_build):
    h = (site_build / "_headers").read_text()
    assert "/static/js/*\n  Cache-Control: public, max-age=31536000, immutable" in h
    assert "/static/d.css\n  Cache-Control: public, max-age=31536000, immutable" in h
```

- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_pages.py -q` — Expected: FAIL (no `site_build` fixture / no `d.css`).
- [ ] **Step 3: Add fonts, `static/d.css`, the fixture, the hash map over `d.css` + `js/*.js` (keep `app.js`/`style.css` entries until Task 12 deletes them), and the `_headers` lines.** `_headers` gets `/static/js/*` and `/static/d.css` immutable lines next to the existing ones.
- [ ] **Step 4: Change `newsite.yml`** to run `DOORPRICE_ENV=testing python -m pricechecker.run --build-only --offline`, copy `newsite-preview/` to `build/mock/`, and deploy `build` (same project, `--branch=newsite`). Header comment updated to say it deploys the real build.
- [ ] **Step 5: Run** the tests and the full suite — Expected: PASS, previous 100 tests still pass.
- [ ] **Step 6: Commit** `git commit -m "newsite: D fonts and stylesheet, shared site build fixture, preview deploys the real build"`

### Task 2: View model in Python and JS

**Files:**
- Create: `pricechecker/site/view.py`, `static/js/view.js`, `tests/js/view_cases.mjs`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes: `pricing.tax_rule/cost/better/unknowns/left_out`, `pricing.js` equivalents; offer inputs = `data_files.offer_inputs(o)`.
- Produces (Python): `DEFAULT = Settings("EU", "", "card", "eur")`; `rows(inputs: list[dict], tax_cfg: dict, s: Settings) -> list[dict]`; `best_of(rows: list[dict], edition: str, storage: str | None = None) -> dict | None`; `gap(rows: list[dict]) -> dict | None` (`{storage, china, global, diff}`, same rule as `derive.gap` but over rows and any settings).
- Produces (JS, same names camelCase): `DEFAULT`, `rows(inputs, tax, s)`, `bestOf(rows, edition, storage)`, `gap(rows)`.
- Row fields (identical keys both sides, camelCase): `store`, `edition`, `storage`, `link`, `days` (`[min,max]` for `s.region` or null), `trust`, `promoLabel`, `list`, `promoAmt`, `promoPct`, `base`, `adj`, `adjAmt`, `ship`, `shipMin`, `taxEst`, `taxAdded`, `duties`, `total`, `approx`, `unknown`, `left`, `tail`, `settled`, `payOk`, `old`, `available`, `delivers`, `state`.
- `state` is one of `"ok" | "nopay" | "stale" | "nodelivery" | "soldout"`; `rows()` returns `ok` and `nopay`/`stale` offers ranked by `better`, then `nodelivery`, then `soldout`; `"base"` storage excluded. `best_of` only ever returns `state == "ok"` rows (`None` otherwise). `tail` uses the exact strings from Global Constraints.

- [ ] **Step 1: Write the failing tests** in `tests/test_view.py`: (a) `rows()` over every phone's inputs at `DEFAULT` gives the same first-row total as `seo._title_price` where that is not None; (b) a stale cheaper offer ranks after a current dearer one and `best_of` skips it; (c) an offer with `ship.US is False` has `state == "nodelivery"` under region US; (d) `gap()` equals `derive.gap` at `DEFAULT` for every phone; (e) `test_js_view_matches_python`: for 5 sample phones × settings `[("EU","","card","eur"), ("EU","DE","paypal","eur"), ("UK","","bank","gbp"), ("CA","ON","card","cad"), ("US","","card","usd")]`, runs `node tests/js/view_cases.mjs --phone <v1 file> --tax <tax file> --settings <csv>` and asserts the JSON rows equal Python's (`total` to 0.01, every other key exact).
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_view.py -q` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement `view.py` and `view.js`** with the interfaces above; `view_cases.mjs` prints `JSON.stringify(rows(...))`.
- [ ] **Step 4: Run** the tests — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "newsite: shared view model (rows, best_of, gap) in Python and JS"`

### Task 3: Shell and settings

**Files:**
- Create: `templates/_d/shell.html` (macros `header(root)`, `footer(root, site)`, `settings_line()`), `static/js/settings.js`, `tests/js/settings_cases.mjs`
- Modify: `templates/base.html` (D shell, `d.css`, `<script type="module">` per page via `{% block module %}`; keep head SEO blocks unchanged)
- Test: `tests/test_pages.py`, `tests/test_settings_js.py`

**Interfaces:**
- Produces (JS) in `settings.js`: `load(storage = localStorage) -> {region, area, pay, cur}` (reads live `pc-*` keys, falls back to `guess()`; `area` = country for EU, province for CA); `save(s)` (writes keys, dispatches `window` event `dp:settings` with `detail = s`); `isDefault(s) -> bool`; `guess(tz, lang) -> partial settings` (port of `app.js` `guess()` incl. `TZ_COUNTRY`/`TZ_PROV`); `watched() -> Set<id>`, `toggleWatch(id) -> bool`; `openSheet()`; `label(s) -> "BG · Card · €"`; `forLine(s, tax) -> "Delivered to Bulgaria by card"`.
- Produces (HTML): header `<header class="top">` with nav links Phones (`/`), Drops (`drops`), Compare (`compare`) and `<button class="prefs" data-prefs>`; under each H1 `<p class="for" data-for>`; footer with links Stores, How we work out totals, About, Privacy, Telegram, r/DoorPrice (from `site.yaml`).

- [ ] **Step 1: Write failing tests.** `tests/test_pages.py::test_every_page_has_the_shell` (every built `.html` except `mock/` has `class="top"`, the three nav links, `data-prefs`, the six footer links, and no `app.js`). `tests/test_settings_js.py` runs `node tests/js/settings_cases.mjs`, which asserts: a fake storage `{"pc-region":"CA","pc-prov":"ON","pc-cur":"cad"}` loads as `{region:"CA", area:"ON", pay:"card", cur:"cad"}`; `guess("Europe/Sofia","bg")` → EU/BG/eur; `guess("Europe/London","")` → UK/gbp; `isDefault({region:"EU",area:"",pay:"card",cur:"eur"})` true; `label` of BG/card/eur is `"BG · Card · €"`.
- [ ] **Step 2: Run** both — Expected: FAIL.
- [ ] **Step 3: Implement** `settings.js` (sheet markup ported from `newsite-preview/common.js` `sheet()`, real country/province lists from the tax file, "Elsewhere" = Global), the shell macros and `base.html`. Header hides on scroll down, shows on scroll up (CSS class toggled by a passive scroll listener in `settings.js`). No-JS line in footer: "Other countries and payment methods need JavaScript".
- [ ] **Step 4: Run** — Expected: PASS (pages still use old bodies; that is fine until their task).
- [ ] **Step 5: Commit** `git commit -m "newsite: D shell (header, settings sheet, footer) and settings module"`

### Task 4: Shared blocks, states and the parity harness

**Files:**
- Create: `templates/_d/blocks.html`, `static/js/blocks.js`, `tests/js/render_blocks.mjs`, `tests/fixtures/states_phone.json`
- Test: `tests/test_blocks.py`

**Interfaces:**
- Consumes: Task 2 rows; Task 3 `settings.js` (`forLine`).
- Produces: one Jinja macro and one JS function per block, same name, same root element and class, each taking `(row(s), s, labels)`:
  `price_box(rows, edition)` → `div.side.cn|.gl`; `gap_line(gap, both)` → `div.gapline`; `mem_chips(rows, edition, storage)` → `div.mems`; `verdict(row, rows_same_pick)` → `section.verdict`; `receipt(row, s)` → `section.receipt`; `store_row(row, s)` → `li` (`.stale` / `.soldout` / `.nodelivery` / `.nopay` modifier); `buy_bar(row)` → `div.buybar`; `home_row(phone, rows)` → `li.pair`.
  JS names are camelCase (`priceBox`, `gapLine`, `memChips`, `verdict`, `receipt`, `storeRow`, `buyBar`, `homeRow`) and return HTML strings. Each root carries `data-block="<snake name>"` so the parity test can find it.
- Produces: `render_blocks.mjs --phone <v1 file> --tax <tax file> --edition <e> --storage <st>` prints `{"<snake name>": "<html>"}` for the default settings.

- [ ] **Step 1: Write the state fixture**: one phone with offers in each state of spec §4.2: settled; unsettled (no shipping); sale 2% "Summer sale"; stale (`old: true`) and cheapest; sold out; `ship.UK: false`; `pay_ok.paypal: false`; plus a China-only variant.
- [ ] **Step 2: Write failing tests** in `tests/test_blocks.py`: `test_blocks_parity` renders each macro via Jinja and each function via `render_blocks.mjs` for the fixture and 5 real phones (one each: both versions, China-only, Global-only, with a sale, with a stale store) and asserts `text(server) == text(js)` per block, where `text()` collapses whitespace of the HTML's text content; `test_state_markers` asserts on the fixture: stale row contains "price from" and is last among priced rows, sold-out row under "Sold out at" with no `<a class="go"`, UK `store_row` reads "Doesn't deliver to the UK", PayPal row reads "Doesn't take PayPal", sale receipt line reads "Summer sale, 2% off at checkout", unsettled tail "+ shipping", and the verdict never uses the stale row.
- [ ] **Step 3: Run** `.venv/bin/python -m pytest tests/test_blocks.py -q` — Expected: FAIL.
- [ ] **Step 4: Implement** the macros and functions, markup and classes from `newsite-preview/d-phone.html` / `d-home.html` (price box, verdict, receipt incl. cost bar, store row, buy bar, home row). Text the spec fixes is copied exactly.
- [ ] **Step 5: Run** — Expected: PASS.
- [ ] **Step 6: Commit** `git commit -m "newsite: D blocks in Jinja and JS with parity and state tests"`

### Task 5: Phone page

**Files:**
- Modify: `templates/phone.html` (rewrite), `pricechecker/site/pages/phone.py`, `pricechecker/site/offers.py` (stop building `offers_json`, `all_json`, `compare` cells; add `rows`, `gap`, `lines`, `bands`, `spec_count`, `data_file`)
- Create: `static/js/phone.js`, `templates/_d/history_svg.html` (macro `store_lines(lines)`, server SVG, one polyline per store, series colours `--s1..--s6`)
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: Tasks 2–4; `data_files.write` return value (`{"phone/<id>": "data/v1/phone/<id>.<hash>.json", ...}`) passed into the phone context as `p["data_file"]` and the tax file as `ctx["tax_file"]`.
- Produces: `phone.js` exports nothing; on load: if `!isDefault(load())`, fetches `p.data_file` + tax file, re-renders every `[data-block]` with `blocks.js`; handles version tap, memory chips, delivery filter chips with counts (tax paid / free shipping / ≤ 10 days; 0 = disabled), ledger sort, buy-bar visibility (IntersectionObserver as in the mock), Watch, Share.

- [ ] **Step 1: Write failing tests**: `test_phone_page_sections` (Oppo Find X9 Ultra page has two `data-block="price_box"`, `gap_line`, `mem_chips`, `verdict`, `receipt`, "Compare every offer (", "What the China version means", "Price history by store", "All ", "specs", "More from Oppo", `data-block="buy_bar"`, actions Watch/History/Compare/Share); `test_phone_title_rules_unchanged` (titles equal the live rules for 3 sample phones); `test_china_only_phone_has_one_box_and_reason` (OnePlus 16: one `price_box`, reason text present); `test_phone_pages_within_budget` (every `phones/*.html` ≤ 60 000 bytes); `test_switching_version_falls_back_to_its_best_memory` (node: `tests/js/phone_cases.mjs` calls the exported pure helper `pickAfterSwitch(rows, edition, storage)` from `phone.js` → returns that edition's best storage when the storage is missing).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** template, page context and `phone.js` (export `pickAfterSwitch` for the test; module still runs its wiring when loaded in a page).
- [ ] **Step 4: Run** — Expected: PASS. Then `python -m pricechecker.run --build-only --offline && python -m pricechecker.serve 8099` and check a phone page in the browser at 390 px with settings EU and CA/ON.
- [ ] **Step 5: Commit** `git commit -m "newsite: D phone page"`

### Task 6: Home page

**Files:**
- Modify: `templates/index.html` (rewrite), `pricechecker/site/pages/home.py`
- Create: `static/js/home.js`
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: `home_row` block; home part files `data/v1/home-<region>-<n>.<hash>.json` (list passed as `ctx["home_files"][region]`); `derive.listing_drops` count for the drops link.
- Produces: `home.js` exports pure `filterRows(phones, {chip, brand, storage, q, watched}) -> ids` and `sortRows(phones, sort) -> ids` (sort ∈ `new|save|cheap|drop`) for node tests.

- [ ] **Step 1: Write failing tests**: `test_home_sections` (H1 "China version or Global?", search input, drops link when count > 0, chips All · Both versions · China · Global · Watched, brand chips, storage select with any/256 GB/512 GB/1 TB, sorts Newest · Biggest China saving · Lowest price · Dropped this week, 20 visible rows then "Show all", "The stores, and what they cover"); `test_home_within_budget` (≤ 120 000 bytes); node `tests/js/home_cases.mjs`: search "x9 ultra" and "ultra x9" both match Oppo Find X9 Ultra only among Oppo phones; storage 1 TB hides phones without it; `cheap` sort orders by row total; a Gomibo-only Pixel row under region US renders "–" for Global.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** template, context, `home.js` (re-pricing loads the region's parts in parallel only when `!isDefault`).
- [ ] **Step 4: Run** — Expected: PASS; check in the browser at 390 px.
- [ ] **Step 5: Commit** `git commit -m "newsite: D home page"`

### Task 7: Specs page

**Files:**
- Create: `templates/specs.html`, `pricechecker/site/pages/specs.py` (adds `phones/<id>/specs.html` for phones with a sheet), `static/js/specs.js` (differences toggle only)
- Modify: `pricechecker/site/__init__.py` (`PAGES`)
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: `specs.load()`, `specs.band_check(sheet, edition)`, `specs.differences(sheet)`; mock `newsite-preview/d-specs.html` + `specs.js` for markup and the split-cell rule.

- [ ] **Step 1: Write failing tests**: Find X9 Ultra specs page exists, shows "Show only the 7 differences", has split cells `class="split"` only where both pages give different values, no text "page only", has sources with dates and a link back to `../oppo-find-x9-ultra`; phones without a sheet get no specs page and their phone page has no "All N specs" link.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "newsite: specs pages"`

### Task 8: Drops page and feed

**Files:**
- Create: `templates/drops.html`, `pricechecker/site/pages/drops.py`, `static/js/drops.js`
- Modify: `pricechecker/site/__init__.py` (`PAGES`), `pricechecker/site/seo.py` (`_feeds` adds `feeds/drops.xml`, sitemap adds `drops`)
- Test: `tests/test_pages.py`, `tests/test_derive.py`

**Interfaces:**
- Consumes: `derive.listing_drops(rows, rates, now)`, `derive.mark_headline(drops, telegram_state, now)` (telegram state from `data/telegram.json`), `view.rows` for the current delivered total.
- Produces: `drops.js` re-prices the "now delivered" column through `view.js` when `!isDefault`; chips filter All · China · Global · brands.

- [ ] **Step 1: Write failing tests**: with a synthetic history (one 5% / €50 drop, one 2% drop, one 4% / €15 drop) only the first is listed; a drop that `mark_headline` marks shows "Posted to Telegram"; an empty week shows "No drops this week" and at most 5 older drops; `feeds/drops.xml` has one `<item>` per listed drop.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "newsite: drops page and feed"`

### Task 9: Compare page

**Files:**
- Modify: `templates/compare.html` (rewrite), `pricechecker/site/pages/compare.py`
- Create: `static/js/compare.js`
- Test: `tests/test_pages.py`, `tests/js/compare_cases.mjs`

**Interfaces:**
- Consumes: phone data files (one per chosen phone), `view.rows`, `price_box`, spec sheets (key specs + split rule from Task 7), the phone list (names + ids only) in the page.
- Produces: `compare.js` exports pure `closest(storages, want) -> storage` (same distance rule as `app.js` `distance()`) and `winners(columns) -> {price, battery, charging}` for node tests; URL hash `#a,b,c@<ram>-<rom>` as live.

- [ ] **Step 1: Write failing tests**: node: `closest(["12/256","16/512"], "16/1024") === "16/512"`; `winners` picks lowest settled total, biggest battery, fastest wired charging; pytest: compare page ≤ 60 000 bytes and contains no offer data (no `"money"` in HTML), has the no-JS line.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** (columns render red/blue price pair per phone at the shared memory, dashed when `closest` substituted; specs table with "Show only the differences").
- [ ] **Step 4: Run** — Expected: PASS; check in browser with `#oppo-find-x9-ultra,oneplus-16,google-pixel-11-pro`.
- [ ] **Step 5: Commit** `git commit -m "newsite: D compare page"`

### Task 10: History pages and monthly pages

**Files:**
- Modify: `templates/history.html` (rewrite), `pricechecker/site/pages/history.py` (adds `history/<id>/<YYYY-MM>.html` for each month the phone has rows, last 90 days on the main page)
- Create: `static/js/history.js` (version switch only)
- Test: `tests/test_pages.py`, `tests/test_history.py`

**Interfaces:**
- Consumes: `derive.store_lines`, monthly history files `data/history/YYYY-MM.csv` (reader from the backend plan), `store_lines` macro (Task 5).

- [ ] **Step 1: Write failing tests**: main history page lists only changes from the last 90 days, grouped by day, line format "Wonda Mobile · China 12 + 256 · €1,080 → €1,049"; one link per earlier month; monthly page for a month with no changes says "No price changes this month"; no month link earlier than the phone's first row; monthly pages link previous/next month.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "newsite: D history pages with monthly pages"`

### Task 11: Stores pages

**Files:**
- Modify: `templates/stores.html`, `templates/store.html` (rewrite), `pricechecker/site/pages/stores.py`
- Create: `static/js/store.js` (delivery chips with counts)
- Test: `tests/test_pages.py`

- [ ] **Step 1: Write failing tests**: stores list has chips Import tax paid · Free shipping · Within 10 days · Takes PayPal with counts matching `stores.yaml` terms; each store row shows regions, shipping, tax, payment fees, trust, checked date; Trading Shenzhen page has the headed EU-warehouse table, "cheapest for" list, current promos (from `promos.json`) and "terms last changed" (from `data/terms_pages.json`).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "newsite: D stores pages"`

### Task 12: Text pages, 404, links, sitemap; delete the old front end

**Files:**
- Modify: `templates/about.html`, `methodology.html` (add "How a drop is counted"), `privacy.html` (fonts self-hosted), `404.html`, `_explain.html` (add the EU band check), `pricechecker/site/seo.py` (sitemap: drops, specs pages, monthly history pages)
- Delete: `static/app.js`, `static/style.css`, `templates/_price.html`, `templates/_stats.html` and any other template no page includes; their `asset_v` and `_headers` entries
- Test: `tests/test_pages.py`

- [ ] **Step 1: Write failing tests**: `test_internal_links_resolve` (every `href` in every built page that is relative or starts with `/` resolves to a built file, trying `<path>.html`, `<path>/index.html` and `<path>`, ignoring `#` fragments and `mock/`); `test_store_links_are_sponsored` (every `<a>` whose href is a store domain from `stores.yaml` has `rel="sponsored nofollow noopener"`); `test_sitemap_lists_new_pages`; `test_no_old_front_end` (no `app.js`/`style.css` in the build).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement**; delete the old files.
- [ ] **Step 4: Run** the full suite with `DOORPRICE_CHECK_BUDGETS=1` — Expected: PASS.
- [ ] **Step 5: Commit** `git commit -m "newsite: D text pages, link and sitemap checks; remove app.js and style.css"`

### Task 13: Screenshots, critique, preview and close-out

**Files:**
- Create: `tools/screenshots.sh` (serves `build/` with `pricechecker.serve`, captures home, phone (Oppo Find X9 Ultra), specs, drops, compare, history, a store and 404 at 390×2400 and 1280×1600, light and dark via `--force-dark-mode`, into a given output dir)
- Modify: `README.md` (front-end section: modules, blocks rule, parity test), `docs/superpowers/notes/2026-10-27-publish-newsite.md` (step noting `newsite-preview/` is copied to `build/mock/` only on newsite and is not published)

- [ ] **Step 1: Build and capture**: `python -m pricechecker.run --build-only --offline && tools/screenshots.sh <scratch dir>`; expected 32 PNGs.
- [ ] **Step 2: Review** the screenshots against the mocks and run an Impeccable critique on the templates; fix material findings (each fix with its own test where it changes behaviour), re-run the suite.
- [ ] **Step 3: Push** `newsite`; wait for the newsite workflow; check https://newsite.pricechecker-87q.pages.dev: `/phones/oppo-find-x9-ultra` still serves the phone page while `/phones/oppo-find-x9-ultra/specs` serves specs; `/history/<id>/<month>` works; testing banner + `noindex` present.
- [ ] **Step 4: Commit** `git commit -m "newsite: screenshot tool, README and runbook notes"` and hand the preview link to the user.
