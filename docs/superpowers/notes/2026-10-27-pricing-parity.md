# pricing.py vs today's app.js: parity run (2026-10-27)

> Historical: `tools/parity.py` and `tools/parity_appjs.mjs` were removed with `static/app.js` (Task 12 of the newsite work); `tests/fixtures/pricing_cases.json` and `static/js/pricing.js` now carry this check.

One-off check before the site's Python callers moved onto `pricechecker/pricing.py` (plan Task 3).

How: `.venv/bin/python -m pricechecker.run --build-only --offline`, then `.venv/bin/python tools/parity.py`.
`tools/parity_appjs.mjs` lifts `taxRule1`, `cost1`, `maybeTax`, `unknowns` and `better` out of `static/app.js`
by name (brace matching) and runs them in a `node:vm` context; one node process takes every job over stdin.

## Totals and flags: 0 differences

| | |
|---|---|
| Phone pages (`id="offers"`, every offer incl. out of stock and old) | 76 (the 77th page has no offers) |
| Index rows (`data-offers`, the lean in-stock form) | 76 |
| Settings combinations | 690 |
| Offer x settings checked | 1,216,470 |
| Differences | **0** |

Settings: every region in the page's `import-tax` config — EU average + each of 27 countries, Canada's own rate + each
of its 13 province keys, UK / US / AU / Global with no area — x card / paypal / bank x eur / usd / gbp / cad / aud.
Compared per offer: total (a cent apart counts), unknowns, payment accepted, old, approx, complete, tax added, tax
estimate, shipping, promo percent and payment adjustment.

The comparator was checked by mutation: adding €0.01 to pricing.py's UK bank totals reports 8,815 differences.

Provinces are iterated as the real config has them. `config/import_tax.yaml` has an unquoted `ON:`, which YAML reads
as boolean True, so there is no "ON" province; the page's JSON (and so app.js) has a `"true"` key with Ontario's rate.
The run uses that `"true"` key, like the browser does. Known live bug, left alone here.

### Resolved before the switch: `stacks_with_bank` may be missing

`pricing.py` read `pr["stacks_with_bank"]`, but the index's lean offers carry it only when the store config sets it
(`site.build`'s `lean`). app.js's `!pr.stacks_with_bank` treats a missing key as "doesn't combine". Today every promo
has the key, so the real offers didn't hit it; fixture case `bank_vs_sale_stacks_unset` now pins it (KeyError before
the fix, €952.50 after). `pricing.py` reads `pr.get("stacks_with_bank")`; `static/js/pricing.js` already matched.

## Page title price: old `_title_price` vs `pricing.rank` vs the page (EU / card / EUR / EU average)

"The page" = the offer app.js's `better()` puts first among the phone page's in-stock offers that deliver to the EU
(what `renderPhone` marks best over the grid cells).

| | Phones where it differs |
|---|---|
| old `_title_price` vs the page | none |
| plain `pricing.rank` vs the page | 1: `xiaomi-17-ultra-leica-edition` |
| new `_title_price` vs old (total to the cent, left-out words, offer) | none |

`xiaomi-17-ultra-leica-edition`: Trading Shenzhen sells it with no RAM/storage listed (`storage: "base"`) at €1,137 +
€10 shipping, import tax included = €1,147 delivered. The page has a "not listed" grid row and app.js ranks it first;
the old title did too. Plain `pricing.rank` skips `base` offers (as the plan specifies for the new index), so it would
have put The Mobile Marvel 16/512 at €1,318.35 in the title. Resolution: `pricing.rank(..., with_base=True)` (opt-in,
default unchanged) and `_title_price` uses it, so the title keeps matching the page.

`_title_price` also still never lets an old price or a store refusing card lead the title (it returns None when only
those are left), as `_too_old`'s docstring promises; `pricing.rank` orders them last, so this only matters when
nothing else is in stock. No phone is in that state today.

Title / JSON-LD / deals.json changes allowed by the ruling (old title disagreed with the page): **none** — the old
title agreed with the page on every phone.

## Build before vs after the switch

`diff -r` of the offline build before the change and after it: **no differences** (all 77 phone pages, titles, share
cards, `deals.json`, index). The build is deterministic (two builds before the change were also identical).
