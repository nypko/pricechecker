# newsite: page design (direction D)

Status: DRAFT, 2026-10-30, awaiting approval. Step 3 of the redesign. Builds on the approved backend spec
(`2026-10-26-newsite-backend-design.md`, done on `newsite`) and the D mockups in `newsite-preview/`
(https://newsite.pricechecker-87q.pages.dev). Approved in conversation section by section on 2026-10-30.

## 1. Goals

- Every page of the site in direction D ("Mix (A + C)"): the China and Global prices side by side, the verdict and
  receipt, PCPartPicker-style sale lines and store history, Pazaruvaj-style delivery filters.
- Keep every live feature (§3.2, §4) and every live URL.
- One definition per thing: the totals rule lives in `pricing.py` / `pricing.js` (done); each block's markup that changes
  with settings lives in one Jinja macro and one JS function, held equal by a test.
- Pages stay within the budgets: phone ≤ 60 KB HTML, home ≤ 120 KB, any one data file ≤ 60 KB (before gzip).

## 2. Not goals

- Email alerts, accounts, per-user anything beyond this device's saved settings and watch list.
- A store click counter (dismissed by the user on 2026-10-21).
- New stores (Pixel stores beyond Gomibo wait for a store that sells them).
- The live Ontario bug (`config/import_tax.yaml` `ON:` read as `True`): a separate fix on main, awaiting the user.
- A JS framework or bundler. Tried as a throwaway spike on 2026-10-30 (Astro 7 + Preact islands,
  `~/Work/doorprice-astro-sample`): 78 pages in 0.7 s and 13.6 KB gzip JS, but island props are written into the
  HTML (41 KB for the Oppo Find X9 Ultra's offers, plus 4.7 KB tax on every page), pushing phone pages to 80 KB.
  The user chose plain templates + ES modules.

## 3. Architecture

### 3.1 Server: Python + Jinja

- Every page is full HTML for the default settings (EU, card, euro, country guessed only in the browser), so search
  engines and visitors without JavaScript get real prices.
- `templates/` is rewritten in D. `base.html` keeps today's head unchanged in substance: canonical URL, JSON-LD
  (WebSite on home, BreadcrumbList elsewhere), share-card `og:image`, the pages.dev redirect, testing `noindex`, the
  web manifest and icons.
- Shared parts are Jinja macros in `templates/_d/`: price box, verdict, receipt, store row, memory chips, history lines
  (SVG drawn at build), spec cell, state rows (§4.2).

### 3.2 Browser: plain ES modules, no bundler

`static/app.js` (1,160 lines) is deleted. In its place, in `static/js/`:

| Module | Job |
|---|---|
| `pricing.js` | exists: delivered-total rule, mirror of `pricing.py` |
| `settings.js` | saved settings, the settings sheet, country/province, timezone guess, `pc-watch` watch list, a `dp:settings` change event |
| `blocks.js` | the only JS markup for the blocks that change with settings: price box, gap line, memory chips, verdict, receipt, store row, buy bar, home row |
| `home.js` `phone.js` `compare.js` `drops.js` `history.js` `store.js` | one per page: wiring, filters, sorting; no markup of their own beyond what `blocks.js` returns |

- Loaded with `<script type="module">`; file names hashed by the build as today (`asset_v`), cached a year.
- On load, a page module reads the saved settings. If they equal the defaults, it changes nothing in the prices. If not,
  it loads only what it needs from `build/data/v1/` (phone file, the region's home parts, tax) and re-renders the
  settings-dependent blocks through `blocks.js`.
- Nothing large is embedded in HTML; offer inputs always come from the `v1` files.

### 3.3 The duplication rule

Each settings-dependent block exists exactly twice: a Jinja macro in `templates/_d/` and a function in `blocks.js`,
with the same element structure and class names. The parity test (§6) renders sample pages, runs `blocks.js` in node
with the default settings over the same data, and compares the text of each block. Changing one side without the other
fails CI.

### 3.4 Fonts and assets

- D's fonts (Schibsted Grotesk 500–800, Albert Sans 400–700) are self-hosted as woff2 subsets in `static/fonts/` with
  their OFL licence, preloaded like Plex today. No Google Fonts requests; IBM Plex Sans stays only where the logo needs it.
- CSS: one `static/d.css` built from the mock's `c.css` + `d.css` + `sheet.css` + `switch.css`, with tokens for colour
  (China red, Global blue, ink verdict, history series `--s1..--s6`) defined in light and dark.

## 4. Shared shell and states

### 4.1 Shell

- **Header** on every page: Door D logo, nav **Phones · Drops · Compare**, and the settings button showing the
  current choice (e.g. "BG · Card · €"). Sticky; hides on scroll down, returns on scroll up.
- **Settings sheet**: ship to (EU / UK / US / Canada / Australia); EU country (sets import VAT and courier fees) or
  Canadian province; pay with (card / PayPal / bank transfer); currency. "Saved on this device." First visit guesses the
  country from the timezone, as today.
- Under each page's H1, one line says what totals are for ("Delivered to Bulgaria by card") with a Change link.
- **Footer**: the delivered-price definition, affiliate disclosure ("it never changes the order"), links to Stores,
  How we work out totals, About, Privacy, Telegram, r/DoorPrice.
- No-JS: pages show EU / card / euro prices and a line "Other countries and payment methods need JavaScript".

### 4.2 States

Defined once (one macro + one `blocks.js` function each) and used wherever a price appears:

| State | Look and rank |
|---|---|
| Settled total | plain price, "✓ delivered, tax settled" |
| Unsettled total | "≈" when estimated; tail "+ shipping" / "+ tax?" / "+ shipping, tax?"; ranked after settled ones (current rule: unlisted shipping weighs 2, possible tax 1) |
| Sale applied | its own receipt line ("Summer sale, 2% off at checkout") and a "2% sale" tag on the row |
| Stale (store silent > 48 h) | greyed row "price from N days ago", ranked last, never a headline, title or JSON-LD price |
| Sold out | under "Sold out at", last price shown, no store button |
| Not delivered to the region | row "Doesn't deliver to the UK", no price |
| Payment not accepted | row "Doesn't take PayPal", ranked after accepted ones |
| One version only | one price box plus the reason: not sold outside China / no store we check lists it |
| No offers | page stays; says so; links history and similar phones |

Kept from live: dark mode, Watch (device-only list, "Watched (n)" filter on home), Share button (`navigator.share`, else
copy link), RSS links, 404 page.

## 5. Pages

URLs: all live paths keep working (`/`, `/phones/<id>`, `/history/<id>`, `/compare`, `/stores`, `/stores/<id>`,
`/about`, `/methodology`, `/privacy`, 404). New: `/drops`, `/phones/<id>/specs`, `/history/<id>/<YYYY-MM>`. All new
pages go in `sitemap.xml`; testing builds stay `noindex`.

### 5.1 Home `/`

1. H1 "China version or Global? *Both prices, delivered.*", the settings line, a search box ("Which phone? e.g.
   'x9 ultra'"). Search: whole words, any order; typing switches to All; a no-results message.
2. A link to the Drops page: "N price drops this week" (hidden when N = 0).
3. Chips: **All · Both versions · China · Global · Watched (n)**, then brands, then storage (any / 256 GB / 512 GB /
   1 TB: prices become each phone's cheapest at that storage, phones without it hide). Sorts: **Newest** (default) ·
   Biggest China saving · Lowest price · Dropped this week.
4. Phone rows: name, launch month, red China price and blue Global price (or the one-version reason), and
   "China €X less at 12 + 256" only when `derive.gap` has a settled same-memory gap. First 20 rows, then "Show all N".
5. "The stores, and what they cover": the store terms table in D.

### 5.2 Phone `/phones/<id>`

As approved on 2026-10-26 in the mock:

1. Kicker (All phones · brand · announced month), H1 "<Phone> price: *China vs Global*" (or "China version" /
   plain), the settings line. `<title>` rules unchanged ("<name> price in China vs Global" / "China version price").
2. **Two price boxes**: version → memory ("12 GB RAM · 256 GB storage") → price → store → "✓ delivered, tax settled" or
   what is not included → "View at <store>". The China box links "Chinese software, Google Play off at first" to the
   explainer. Tapping a box switches the page to that version. Below: the same-memory gap line or "No memory has a
   settled delivered price for both versions yet".
3. Memory chips with each one's price; **verdict** (ink card: version + memory pills, total, store, delivery days,
   "why this one", badges for sale / reviews / tax paid / warranty / returns, button, checked time, affiliate note);
   **receipt** (cost bar + store price, sale, payment fee, shipping, import tax, "You pay at the door").
4. **Other stores** for this version + memory, with delivery filter chips and counts (Import tax paid by store · Free
   shipping · Arrives within 10 days; a chip with 0 is disabled). "Compare every offer (N)" opens the ledger: store ·
   version · memory, store price, sale, payment, shipping, tax, total, rank; sortable.
5. What the China version means (Google Play, warranty, bands + explainer link); price history by store (one line per
   store for the chosen version, links to History and RSS); key specs + EU band check per version + "All N specs";
   More from <brand> (3 phones).
6. **Buy bar**, pinned at the bottom once the price boxes scroll away, hidden while the verdict's button is visible:
   line 1 price + "China · 12 GB + 256 GB", line 2 store, button "View deal". Never two buy buttons in view.
7. Actions row: Watch · History · Compare · Share.

### 5.3 Specs `/phones/<id>/specs`

As the mock `d-specs.html`: full spec sheet from `config/specs/<id>.yaml`. A field splits into China / Global cells
with coloured labels only when both brand pages give a value and they differ; a field only one page lists is one plain
cell with no tag, plus one note under the sources. Market-dependent fields (in the box) split with "Not listed" and are
not counted as differences. "Show only the N differences" toggle; EU band check per version; sources with dates; link
back to prices.

### 5.4 Drops `/drops`

- Listing drops over 7 days from `derive.listing_drops` (same store, version and memory, ≥ 3% and ≥ €20). Row: phone,
  version + memory, store, old → new store price, % down, current delivered total for the visitor's settings, button.
- "Posted to Telegram" mark on drops that also lowered the phone's cheapest delivered price (`derive.headline_drops`,
  Telegram's rule); Telegram link at the top.
- Chips: All · China · Global · brands. Empty week: "No drops this week" and the 5 latest older drops.
- RSS feed `/feeds/drops.xml` with the same list.

### 5.5 Compare `/compare#a,b,c`

- Up to 3 phones; the choice lives in the URL hash so it can be shared (as today).
- Each column: the red China / blue Global price pair at one memory chosen for all columns; a phone without that
  memory uses its closest (dashed, as today). Prices link to their stores.
- Below: key specs from `config/specs`, with the specs page's split cells and "Show only the differences". Green ✓
  winners: lowest delivered price, biggest battery, fastest wired charging.
- Without JS: the picker prompt and links to phone pages.

### 5.6 History `/history/<id>` and `/history/<id>/<YYYY-MM>`

- One line per store (`derive.store_lines`), version switch, stats row (lowest, highest, now).
- Change list: last 90 days grouped by day ("Wonda Mobile · China 12 + 256 · €1,080 → €1,049"), then links to each
  earlier month and the phone's RSS.
- Monthly page: the same for that month only, previous / next month links.

### 5.7 Stores `/stores` and `/stores/<id>`

- List: delivery chips with counts (Import tax paid · Free shipping · Within 10 days · Takes PayPal). Row: regions
  served, shipping, tax handling, payment fees, trust (reviews, warranty, returns), terms checked date.
- Store page: full terms with notes and sources, the EU-warehouse table (headed, as now), phones it is cheapest for,
  current promotions, "terms last changed" from the terms watcher.

### 5.8 Text pages

About, How we work out totals (`/methodology`), Privacy, 404, China-version explainer: content kept, D type and
colour. Methodology gains "How a drop is counted"; the explainer covers the EU band check. Privacy changes only where
facts change (fonts now self-hosted).

## 6. Testing

- **Parity**: build pages for 5 sample phones (both versions; China-only; Global-only; with a sale; with a stale
  store), run `blocks.js` in node with the default settings on the same `v1` data, compare each block's text with the
  server HTML. Runs in CI next to the existing `pricing.js` node test.
- **Budgets**: the existing budget tests become required on `newsite` (phone ≤ 60 KB, home ≤ 120 KB, data ≤ 60 KB).
- **States**: a fixture with one offer per state in §4.2; tests check each state's marker text and rank.
- **Links**: every internal link in the build resolves to a file; every store link carries
  `rel="sponsored nofollow noopener"`.
- **Screenshots** (review aid, not CI): a headless chromium script captures home, phone, specs, drops, compare,
  history, store and 404 at 390 px and 1280 px, light and dark, into the scratch area; reviewed with an Impeccable
  critique before each preview hand-off.

## 7. Rollout

- Work happens on `newsite`; each step is pushed to the newsite preview for the user to look at.
- Hourly job unchanged beyond what is already on `newsite`.
- Publish follows `docs/superpowers/notes/2026-10-27-publish-newsite.md`.
- Build order (input to the templates plan): fonts + `d.css` + shell + settings → `blocks.js` + macros + parity test →
  phone → home → specs → drops → compare → history → stores → text pages + 404 → screenshots, critique, budgets.

## 8. Risks

- **Parity drift** between macros and `blocks.js`: held by the parity test; kept small by limiting `blocks.js` to
  settings-dependent blocks.
- **Home re-pricing cost**: the region's home parts are several files; loaded only when settings differ from the
  defaults, in parallel, and cached a year by hash.
- **Font weight**: two families; subset to Latin and limit to the weights used.
