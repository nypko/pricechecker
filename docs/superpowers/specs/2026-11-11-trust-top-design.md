# Page tops that say what DoorPrice is

Status: DRAFT, 2026-11-11, awaiting approval. Designed in conversation on 2026-11-10/11 with mockups in the visual
companion (`.superpowers/brainstorm/19954-1794343935/content/`: `home-top-v2.html` option B1, `phone-top.html` option P1,
`network-check.html` option N2).

## 1. Problem

The owner: "it looks like a scam site". The first screen of the home page and of every phone page shows large prices for
€800–3,700 phones and little else:

- nothing says what DoorPrice is, so it reads like a shop, and a shop with cheap flagships is the classic fake-shop
  pattern; the facts that would reassure (not a shop, the stores compared, how it earns money) are only in the footer
  and on About;
- no phone photos; stores are a count ("4 stores"), not names;
- no sign of how fresh the prices are;
- filled pink/blue price boxes and dashed "Global –" boxes that look broken.

The site also says prices are checked "every hour", but from 27 Oct to 10 Nov the scheduled check ran 3–5 times a day
(median gap 6 h). A visible "checked … ago" would contradict that claim.

## 2. Goal

On the first screen (phone 375 × 664 px, and desktop) a first-time visitor can tell what DoorPrice is and isn't, which
stores it compares and how they are rated, how fresh the prices are and how the site earns money; on a phone page also
what the phone is (photo, key specs) and whether each version works on their country's networks.

Not goals: any change to prices, totals, ranking or the settings sheet; anything below the version boxes on a phone page
(verdict panel, receipt, store list, specs section); other page types beyond the shared header and the wording change;
making the check run hourly (decided: change the wording instead); store logos; placeholder or stock images.

## 3. Header (every page)

- The search icon becomes a search field: `<form role="search" action="{root}" method="get">` with a labelled
  `<input name="q" type="search">`. Placeholder "Search phones"; at 640 px and wider the page swaps it for
  "Which phone? e.g. “x9 ultra”".
- Phone layout: row 1 logo · search (takes the free width) · settings button; row 2 the section links (as today).
  Desktop: logo · section links · search (up to 460 px, pushed right) · settings button.
- Home page: typing filters the list live, exactly as today's hero search does (`home.js` binds to the header field;
  submitting does not reload). Other pages: Enter goes to the home page with `?q=…`, which fills the field and filters.
  `?q=` with no text focuses the field (today's icon link behaviour).
- The header keeps its hide-on-scroll-down / show-on-scroll-up behaviour and stays shown while the field has focus
  (existing `:focus-within` rule).

## 4. Home page top

Replaces today's hero (headline "China version or Global? Both prices, delivered.", the "Delivered to …" line and the
search box). Markup comes from `home_intro` in the new `templates/_d/top.html`.

- H1: "What imported flagship phones really cost, *delivered to your door.*" (second part in the lighter style, as
  today's `<em>`).
- Sentence: "DoorPrice compares **{N} import stores** several times a day and adds shipping, payment fees and import tax
  for **{place}**. We don't sell phones." N = connected stores, an EU-warehouse sub-store not counted (the About page
  rule). {place} is the destination of the visitor's settings, the same name today's "Delivered to … by …" line uses
  (country, province, "the UK", "the US", "Australia", "the EU" without a country, "your country" for Rest of the world);
  rendered "the EU" and repainted by `settings.js`.
- Store chips: one per counted store, "{label} ★{score}" (score from the store's trust data, one decimal), each linking
  to its store page; ordered by score, highest first, then name; a store without a score shows its name only. One
  scrolling row with a fade at the right edge on phones; wrapping on desktop.
- Checked line: "● Prices checked {ago} · Affiliate links never change the order · How it works", "How it works"
  linking to About. {ago} per §8.
- The price-drops card becomes one line: "↓ {n} price drops this week" with "See all →" (same link; the threshold
  sentence stays on the Drops page).
- Below: the filter chips, sort row, count and list, unchanged in behaviour.

## 5. Home rows (`home_row` block)

- Photo column: the small photo (§9) in a 58 × 72 px box; a phone without a photo has no column (the content takes the
  full width).
- Under the name and month: key specs line "{chip} · {screen}″ · {battery}" from the phone's spec sheet `key`; a value
  that lists several versions ("8,000 mAh / 7,150 mAh (EU)") shows its largest number as "up to 8,000 mAh"; a missing
  value is left out with its separator.
- Price boxes: white, thin border, coloured uppercase label (CHINA / GLOBAL, the existing `--cn`/`--gl` colours) instead
  of filled backgrounds; the price and memory as today, plus "at {store}" — the store with that version's lowest
  delivered total at the visitor's settings (the one the price comes from).
- A version the phone doesn't have: "No Global version" (or "No China version") in muted text in a dashed box, instead
  of "–". Sold-out and not-delivered states keep today's wording.
- The row ends with "{n} stores compared" (was "{n} stores"); the gap line ("China €384 less at 12 + 512") and the
  "↓ this week" mark stay.

## 6. Phone page top

Kicker and H1 unchanged. Today's "Delivered to … by …" line moves into the checked line. Markup from `product_card` and
`checked_line` in `templates/_d/top.html`.

- Product card (white, under the H1):
  - photo (§9) in a 92 × 112 px box on phones, 150 × 186 px on desktop, captioned "Photo: {brand}" (or the sheet's
    `photo.credit`);
  - key specs, one per line on phones: chip; "{screen}″ screen"; "{battery} · {charging} charging" — the full sheet
    values here (version differences included); on desktop one line "chip · screen · battery · charging";
  - links "All specs" (the existing specs page) · "Check your network" (jumps to the existing network check further
    down; left out when no version has published bands).
  - Desktop: text left, photo right of the kicker, H1 and specs (as the P1 desktop mockup).
  - No photo: the card shows the specs and links only. No photo and no key specs: no card.
- Checked line under the card: "● {n} stores checked {ago} · delivered to {place} by {payment} · we don't sell phones".
  n = stores listing this phone (any version), an EU-warehouse listing counted as part of its store; when k of them
  have `ok: false` for the latest check in `data/latest.json`, "{n−k} of {n} stores checked {ago}". The "delivered to …"
  part is repainted by `settings.js` (lower-case form of today's line).
- Memory chips and version boxes follow as today, each box with the network line (§7).

## 7. Network line (`price_box` block)

One line per version box, after "✓ delivered, tax settled", before the Chinese-software warning, for the country in the
visitor's settings. Worked out from the same data as the network check on the page (the version's band lists, the
country's carrier file, `config/bands.yaml`) by a new `carriers.box_line()` and its line-for-line twin `boxLine()` in
`static/js/carriers.js`.

Each network gets its verdict as today (`carriers._judge`, which already never counts a supplementary band as a coverage
risk). The line describes the worst group, in this order of severity: risk, 4g, minor, unknown, nogaps, full.
{where} is "in {Country}" when that group is every network of the country, else "on {network names}" (joined
"A, B and C"). {reason} is the short reason `_judge` already returns for the group's first network ("no band 20",
"no 5G band n28"), capitalised at the start of the line; {use} is that band's `use` text in `config/bands.yaml` without
its frequency prefix ("800 MHz: coverage indoors and outside towns" → "coverage indoors and outside towns").

| Case | Line | Style |
|---|---|---|
| Every network `full` | "✓ works on all {n} networks in {Country}" ("✓ works on {network}" when the country has one) | good |
| Worst is `nogaps` | "✓ no gaps found {where}" | good |
| Worst is `risk` | "{Reason} {where}: weaker {use}", e.g. "No band 20 in Bulgaria: weaker coverage indoors and outside towns" | bad |
| Worst is `4g` | "No 5G {where}" | neutral |
| Worst is `minor` | "Works {where}; {reason} ({use})", e.g. "Works in Bulgaria; no band 7 (extra speed in busy areas)" | neutral |
| Worst is `unknown` (a network's lists are missing) | "Bands not known {where}" | muted |
| Version has no published bands | "Bands not published for this version" | muted |
| No country in the settings (EU average, Rest of the world) | "Networks: choose your country" (a button opening the settings sheet) | muted |

The server renders the default settings (EU, no country), so the HTML carries the "choose your country" line and the
browser repaints it.

## 8. Freshness and wording

- {ago}: the time the latest price check finished (`updated` in `data/latest.json`), written into the page as
  `<time datetime="…" data-ago>10 Nov, 18:39 UTC</time>`; one shared browser function rewrites it: under 2 min "just
  now", under an hour "{m} min ago", under a day "{h} h ago", else "on {d Mon}". It repaints on load and when the tab
  becomes visible again. Without JavaScript the clock time stays.
- "Every hour" and "hourly" become "several times a day" (or are dropped) wherever a visitor or search engine reads
  them: the footer; About; Methodology; Stores; store and history pages; the meta descriptions of the home (base),
  phone, store and history pages; the empty-state notes ("after the next hourly check" → "after the next check"); the
  Telegram intro text (`telegram.py`); the share images (`cards.py`). Internal names (the "Hourly price check" workflow,
  code comments) stay.
- Outside the repo (owner edits by hand; replacement text supplied at publish): the Telegram channel description and the
  r/DoorPrice post body (its title can't be edited).

## 9. Photos

- Source: `config/specs/<id>.yaml` gets
  `photo: {url: <image file on the brand's site>, page: <page it appears on>, checked: <date>}`, optional
  `credit:` (default: the brand). One photo per phone, both versions. Picked by hand from the brand's own product, list
  or press pages for all 80 phones (`og:image` was usable for only 3 of 7 brands tried).
- Tool `python -m pricechecker.photos [ids…] [--force]`, run locally, never in the scheduled check: for each sheet whose
  photo URL differs from `data/photos.json` (or `--force`): download with the checker's user agent (20 s timeout, at most
  10 MB, `image/*` only); trim empty margins (the alpha bounding box, or pixels within a small tolerance of the corner
  colour when there is no alpha); pad to a 4:5 frame with a 4 % margin on a transparent background; save
  `static/phones/<id>-s.webp` (128 × 160) and `static/phones/<id>-m.webp` (368 × 460); record URL, source hash and
  output hashes in `data/photos.json`. A source under 300 px tall after trimming is refused with a message.
- Files are committed and served from doorprice.app (`img-src 'self'` unchanged); `/static/phones/*` cached 30 days,
  URLs carry `?v={hash}`.
- Pages: `<img>` with width, height and alt = the phone's name; the phone-page photo loads eagerly, home-row photos
  `loading="lazy" decoding="async"`. In dark mode the photo sits on a light tile with rounded corners.
- The About page adds: "Phone photos are each brand's own product images, credited on each phone's page. A brand that
  would like one removed can write to {contact}."
- A phone without processed files shows no photo (§5, §6); the build log lists them ("photos: 3 of 80 phones have none:
  …"), never failing the build.

## 10. Code structure

- `templates/_d/top.html` (new): `home_intro`, `product_card`, `checked_line`; `index.html` and `phone.html` call them.
- `templates/_d/shell.html`: `header` gains the search form; `settings_line` is replaced by the checked line on phone
  pages and dropped from the home page (other pages keep it).
- Blocks drawn twice (`templates/_d/blocks.html` and `static/js/blocks.js`), both halves changed together:
  `price_box` (network line), `home_row` (photo, specs line, store per box, "No … version", "stores compared").
- `pricechecker/carriers.py` + `static/js/carriers.js`: `box_line` / `boxLine`.
- `static/js/settings.js`: place-only painting (`[data-place]`) next to today's `[data-for]`, the lower-case variant,
  the placeholder swap, and the shared {ago} painter (or a small module it imports).
- `static/js/home.js`: binds to the header field.
- `pricechecker/photos.py` (new); the build attaches `{s, m, credit}` (or nothing) to each phone; `headers.py` cache
  rule; the home data files carry each phone's photo URL and specs line for rows redrawn in the browser (within the
  existing size budget).
- `static/d.css`: header search, intro, chips, product card, row photo column, neutral boxes, network line, dark-mode tile.

## 11. Testing

- Jinja-vs-JS parity (`tests/test_blocks.py`, node harness) for the changed `price_box` and `home_row` states,
  including photo/no photo, "No Global version", every network-line case.
- `box_line` Python vs JS for every phone × version × country (as the network check's 1,829-combination test), plus unit
  cases for each row of the §7 table.
- Page tests: header search form on every page type; home intro text, chip count and order; checked line with
  `datetime`; product card with photo, without photo, without specs; "Check your network" only with bands; no
  "every hour"/"hourly" in any built page's visible text or meta; `img` width/height/alt; About photo paragraph.
- `{ago}` wording at each boundary (node).
- `photos.py` on images made in the test with Pillow: transparent margins, white background, too small (refused),
  output sizes and 4:5 frame, unchanged URL skipped.
- After pushing to testing: headless Chromium with zero CSP violations and zero JS errors on every page type (the
  method used on 9–10 Nov), and PageSpeed mobile for the home page and a phone page in the owner's Chrome (today
  100 and 98); a regression there blocks publishing.

## 12. Rollout

One branch (`trust-top`), pushed to the testing site for the owner to look at, then published to main as usual.
Photos can arrive in batches after the code; phones without one simply show none.
