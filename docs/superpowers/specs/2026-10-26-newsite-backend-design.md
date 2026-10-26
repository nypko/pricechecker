# newsite: backend and data design

Date: 2026-10-26 · Status: draft for review · Direction: D (Mix of A + C)

The redesign ("newsite") rebuilds DoorPrice's pages as direction D: China and Global prices first, A's price card and
receipt underneath, the full offer table one tap away, plus a Price drops page, price history per store, delivery
filters and full phone specs. This spec covers what has to change behind the pages. The page design itself gets its own
spec (step 3) once this one is approved.

Reference mockups: https://claude.ai/artifact/SBXAcoCFS4Mrzjyd9TUG32 (D pages; preview on the `newsite` Pages branch).

## 1. Goals

1. **One definition of totals.** Today the delivered-total maths and the ranking rule exist twice, in Python
   (`site._title_price`: titles, JSON-LD, deals.json, Telegram) and in `app.js`, and already disagree. newsite defines
   them once in `pricing.py`; the browser's copy is a small mirror that must pass the same test cases in CI (§4.1).
2. **Data that grows stays cheap.** History is one CSV that every build reads whole and every history page embeds whole.
3. **Data for D's new parts:** list price vs automatic sale, one history line per store, listing-level drops,
   delivery-filter fields, full specs and network bands per version.
4. **Code you can change one piece at a time.** `site.py` (696 lines) and `app.js` (1,164 lines) each do everything.
5. **Production untouched until "publish".** newsite builds and deploys on its own Pages branch from main's live data.

## 2. Not goals

- **Incremental builds.** Measured 2026-10-26: a full offline build takes 8.3 s and writes 343 files (22 MB, mostly
  history pages and share cards). Cloudflare Pages already uploads only changed files. Not worth the complexity now.
- **Accounts, email alerts, server code at request time.** Still a static site; Watch stays on-device; alerts stay on Telegram.
- **New stores or new regions.** Store adapters (`pricechecker/stores/`) and price collection are unchanged.

## 3. What exists today (measured 2026-10-26)

| Item | Size / shape | Problem |
|---|---|---|
| `build/index.html` | 1.2 MB (59 KB gzipped) | embeds every phone's offers so the browser can total them |
| `build/compare.html` | 696 KB | same |
| `build/phones/<id>.html` | ~210 KB each (27 KB gzipped) | embeds all offers for every region, payment and currency |
| `build/history/<id>.html` | ~250 KB each, 9 MB in total | embeds every recorded change |
| `data/history.csv` | 4,513 rows / 346 KB after 10 days | one file, read whole every build; ~165k rows a year at this rate |
| `data/latest.json` | 390 KB | fine; rewritten every run |
| `config/specs.yaml` | 4 fields per phone | no way to show full specs |

## 4. Design

### 4.1 Totals engine (`pricechecker/pricing.py`, mirrored by `static/js/pricing.js`)

One pure module defines how an offer plus settings becomes a total and an "unknowns" score:

```
cost(offer, settings, tax) -> Cost(list, promo_amt, base, adj_amt, ship, tax_est, tax_added, total, approx, pay_ok, old, duties)
unknowns(cost) -> int                 # unlisted shipping 2, tax that may still be due 1
better(a, b) -> bool                  # payment accepted, then current over old, then fewer unknowns, then lower total
```

- `settings` = region, EU country or Canadian province, payment, currency. With 27 EU VAT rates (some with a courier's
  minimum fee) and 13 provinces that is about 690 combinations per offer, so totals can't be precomputed for every
  setting: ~400 KB per phone, or ~53,000 files (Cloudflare Pages allows 20,000). *Revised 2026-10-27 while planning.*
- So the rule is defined once in `pricing.py` and mirrored line for line in `static/js/pricing.js`, a small ES module
  with no DOM access. Python uses it at build time (titles, JSON-LD, deals.json, Telegram, the default EU/card/euro
  render); the browser uses the mirror when the visitor changes settings.
- **They can't drift:** `tests/fixtures/pricing_cases.json` holds offers × settings with expected costs; pytest checks
  `pricing.py` against it and runs `node tests/js/pricing_cases.mjs` to check `pricing.js` against the same file.
- **Regression guard:** before the switch, a one-off parity run compares `pricing.py` with today's `app.js cost1()` /
  `better()` over every current offer and settings combination; each difference is fixed deliberately and listed.
  Known already: `_title_price` ignores courier fees and the sale-vs-bank-transfer rule that `app.js` applies.

### 4.2 Data files the pages read

Pages stay fully rendered HTML for the default settings (EU average VAT, card, euro), so search engines and the first
view need no JavaScript. When the visitor changes settings, the page loads one small file with the compact inputs
`pricing.js` needs (prices per currency, payment percentages, shipping per region, duties per region, sale):

```
build/data/v1/phone/<id>.<hash>.json      offer inputs, store history lines, band check
build/data/v1/home.<hash>.json            per phone and version: the best offer's inputs, for re-ranking the list
build/data/v1/tax.<hash>.json             config/import_tax.yaml as the browser needs it
```

- `v1` = data format version; a breaking change becomes `v2`.
- Hashed names, cached for a year (`_headers`).
- Budgets enforced by a test: phone page ≤ 60 KB HTML, home ≤ 120 KB, any one data file ≤ 60 KB (before gzip).

### 4.3 History in monthly files

- `data/history/2026-10.csv`, `2026-11.csv`, … with the same columns as today. A one-off migration splits
  `data/history.csv`; a test checks that joining the chunks reproduces it row for row.
- The hourly run appends to the current month only.
- Builds read the last 3 months for charts, drops and trends; history pages read everything for their own phone.
- History pages show the last 90 days of changes and link each earlier month as its own small page
  (`/history/<id>/2026-10`), instead of one 250 KB page.

### 4.4 Derived data (`pricechecker/derive.py`)

Pure functions over history plus latest offers, each with tests:

- `store_lines(id, edition)`: daily lowest price per store (any memory), EU-warehouse sub-stores folded into their parent.
- `listing_drops(window=7d)`: same store, same listing (version + memory), now vs 7 days ago, flagged when ≥ 3% and ≥ €20.
- `headline_drops()`: the phone's cheapest delivered total (EU, card) vs the last posted reference (today's Telegram rule).
- `gap(id)`: China vs Global at the same memory, settled totals only (19 of 76 phones have one today).
- `promo_split(offer)`: list price, automatic sale amount, price paid (data already in `promos.json`).

**Drops page and Telegram (needs a decision, §8):** they currently measure different things. Proposal: the Drops page
lists listing drops and marks the ones that also lowered the phone's cheapest delivered price; Telegram keeps posting
headline drops only. One module computes both, so they can't drift.

### 4.5 Full specs (`config/specs/<id>.yaml`)

One file per phone replaces `config/specs.yaml`:

```yaml
id: oneplus-16
sources:                       # one brand spec page per version we have read; nothing from third-party sites
  china: {url: https://www.oneplus.com/cn/16/specs, checked: 2026-10-26, lang: zh}
key:                           # the four shown at the top of the phone page (today's specs.yaml, migrated)
  chip: Snapdragon 8 Elite Extreme Gen 6
  screen: 6.78
  battery: "9,000 mAh"
  charging: "100 W"
groups:                        # fixed group and field names, so every phone's sheet lines up and can be compared
  display: {size: "6.78 in, flat", resolution: "2772 × 1272 (FHD+), 450 ppi", refresh: "1–165 Hz, up to 185 Hz in games", ...}
  battery: {capacity: ..., wired: "100 W SUPERVOOC / 100 W UFCS", wireless: null}   # null = not on the brand's page
  software: {system: "ColorOS 17"}
  # a value the two brand pages disagree on: {china: "...", global: "..."}  -> shown as a split cell, counted as a difference
  # a value only one page lists:            {value: "...", from: china}   -> one plain cell for both versions, not a difference
  ...
bands:
  china: {lte: [1, 2, 3, ...], nr: [1, 2, 3, ...]}
```

- **China vs Global:** when both versions' brand pages are read, a field the pages disagree on renders as a split cell
  (China half and Global half, each with its colour label on top), and the specs page offers "Show only the N
  differences". A field only one page lists is not a difference: if it is the same hardware it shows as one plain cell
  (no tag; one line under the sources explains it); if it can vary by market (what's in the box) it shows as a split
  cell with "Not listed" in the other half, and isn't counted. Example,
  Find X9 Ultra (2026-10-26): 7 real differences (memory versions, wired charging standards, colours, NFC, SIM/eSIM,
  satellite systems, colour lens), plus 5 fields only one page lists.
- **Schema:** fixed groups (display, performance, battery, cameras, video, build, connectivity, software, other) with
  fixed field names; a test validates every file. `null` renders as "Not on <brand>'s page". Missing versions render
  as "not checked yet".
- **Source rule:** the brand's own spec page for that version, never third-party aggregators. On 2026-10-26 these
  disagreed with OnePlus's own page on charging (150 W vs 100 W) and wireless charging (listed vs absent).
- **How sheets get filled:** `python -m pricechecker.specpages fetch <id>` renders the brand page locally in headless
  Chromium (many are JavaScript-built; CI never does this), saves its text to `data/spec_pages/<id>-<version>.txt`, and
  Claude transcribes it into the YAML in a reviewed commit. No automatic parsing: 15 brands, each with its own layout.
- **Watching:** a weekly job re-fetches saved brand pages over plain HTTP where that works and opens one
  "Spec pages changed" issue (like the terms watcher) when the text changes.
- **Band check:** `config/region_bands.yaml` lists each region's main bands (EU: LTE 1, 3, 7, 8, 20, 28; 5G n1, n3,
  n7, n8, n20, n28, n78) with a one-line reason for the key ones. The phone page shows, per version, "has all the main
  EU bands" or "missing LTE 20, 5G n20 (800 MHz: rural coverage and indoors)". Other regions get lists later; until
  then the check only shows for EU.
- **Pages:** `/phones/<id>/specs` (indexable, "<phone> specs"), linked from the phone page's key specs.
- **Coverage:** the 3 sample phones are done. Fill the rest newest first (§8); until a phone has a sheet,
  its page shows the four key specs and no "All specs" link.

### 4.6 Code layout

```
pricechecker/
  pricing.py        totals and ranking (4.1)
  derive.py         drops, store lines, gaps, promo split (4.4)
  specs.py          load and validate config/specs/, band check (4.5)
  specpages.py      local fetch of brand spec pages (4.5)
  history.py        monthly chunks (4.3)
  site/
    __init__.py     build(): load once, derive once, call each page module
    data_files.py   build/data/v1 writers (4.2)
    pages/          home.py, phone.py, specs.py, history.py, drops.py, compare.py, stores.py, static.py
    seo.py          titles, JSON-LD, sitemap, feeds, IndexNow list
    cards.py        share cards (moved)
static/js/          settings.js, phone.js, home.js, drops.js, compare.js, watch.js (ES modules, no bundler, hashed names)
```

Each page module takes plain data in and returns HTML out; none reads files or the network itself.

### 4.7 newsite branch, preview and publish

- Branch `newsite` holds the new code. Workflow `newsite.yml` runs on every push to `newsite` and every 3 hours:
  checks out `newsite`, copies `data/` from `main` (the live prices), builds offline with `DOORPRICE_ENV=newsite`
  (preview strip, `noindex`, robots disallow), deploys to the Pages branch `newsite`
  (https://newsite.pricechecker-87q.pages.dev). No Telegram, no IndexNow, nothing committed back.
- Until the new build exists, the workflow deploys the D mockup pages from `newsite-preview/` so they can be tried on
  real phones.
- Every URL that exists today keeps working (`/phones/<id>`, `/history/<id>`, `/compare`, `/stores/<id>`, feeds,
  sitemap). New: `/drops`, `/phones/<id>/specs`, `/history/<id>/<yyyy-mm>`.
- **Publish** = merge `newsite` into `main`. The hourly workflow then builds and deploys the new site. Rollback =
  revert the merge commit.

## 5. Testing

- Golden totals test (4.1) over every offer × every settings combination, old vs new.
- History chunk round trip; append writes only the current month.
- `derive` unit tests with small hand-made histories (drop thresholds, a store joining is not a drop, sub-store folding).
- Specs schema test over `config/specs/*.yaml`; band check tests.
- Page budget test (4.2) and a link check over `build/` (every internal link resolves).
- Existing tests keep passing; CI runs them on `newsite` pushes before deploying.

## 6. Build order (input to the implementation plan)

1. `newsite.yml` + mockup preview (done with this spec, so D can be tried now).
2. `pricing.py` + golden test; switch Python callers.
3. History chunks + migration.
4. `derive.py` (store lines, drops, gap, promo split); Telegram reads it.
5. Specs: schema, migrate `specs.yaml` key fields, 3 full sheets, band check, `specpages fetch`.
6. `build/data/v1` files + budget test.
7. `site/` package split, then the D templates and JS modules (after the page design spec, step 3).
8. Preview on newsite, fix, publish.

## 7. Risks

- **Golden test finds real disagreements** between today's Python and JS totals. That is the point; each one is fixed
  deliberately and listed in the publish notes.
- **Spec sheets take time** (77 phones, several only on Chinese pages). The page works without them (4.5 coverage).
- **Band lists change** with firmware or carrier deals; the check says "main EU bands" and tells people to confirm with
  their carrier.

## 8. Decisions (2026-10-26)

1. **Drops vs Telegram:** Telegram keeps posting headline drops (a phone's cheapest delivered price, EU/card, ≥ 3% and
   ≥ €20 below its last post). The Drops page lists listing drops and marks the ones that were also headline drops.
   Both come from `derive.py`.
2. **Telegram name:** the channel becomes @DoorPriceDrops (title already changed). The bot already posts by the channel's
   numeric id (`TELEGRAM_CHAT_ID`, set 2026-10-26), so the rename can't break posting; `config/site.yaml` `telegram:`
   changes to `DoorPriceDrops` once the new link works.
3. **Specs order:** newest phones first (catalog `announced:` descending).
