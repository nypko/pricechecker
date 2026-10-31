# Carrier check: will this phone work on my network?

Status: DRAFT, 2026-10-31, awaiting approval. Designed in conversation on 2026-10-31.

## 1. Problem

The biggest risk with a China-version phone is that it misses a band the buyer's network relies on. Today the site
checks a phone against one fixed list of "main EU bands" (config/region_bands.yaml), shows that same EU result to UK, US,
Canadian and Australian visitors, and can only do it for 4 of 77 phones, because the others' bands are not recorded.

## 2. Goal

For every phone and version, tell the visitor how it does on each mobile network in their country, in plain words, from
sourced data: works fully, minor gaps, coverage risk, 4G only, or unknown.

Not goals: VoLTE / Wi-Fi calling / carrier approval lists (stated as not checked), coverage maps, plans or prices of
carriers, every virtual carrier.

## 3. Scope

- **Countries**: every country the settings offer: the 27 EU member states, UK, US, Canada, Australia (31). The "Global"
  region picks a country from this list.
- **Carriers**: every mobile network operator with its own radio network in those countries (about 110), plus a pointer
  list of the best-known virtual carriers per country ("Lebara: on Vodafone"), which use their host network's bands.
- **Phones**: all catalog phones, both versions where the catalog or offers have them.

## 4. Data

### 4.1 Band table — `config/bands.yaml`
Every LTE and NR band any listed network or phone uses: number, frequency (MHz), class `low` (< 1 GHz), `mid`
(1–2.7 GHz), `high` (3–7 GHz), `mmwave` (> 24 GHz), and a short plain-words purpose ("800 MHz: coverage indoors and
outside towns"). The verdict's severity comes from this table only, never per carrier.

### 4.2 Carriers — `config/carriers/<CC>.yaml` (ISO country code)
```yaml
country: DE
checked: 2026-11-03
networks:
  - id: telekom-de
    name: Telekom
    lte: [1, 3, 7, 8, 20, 28, 32]
    nr: [1, 3, 28, 78]
    sources:
      - {url: https://…, kind: regulator, checked: 2026-11-03}
      - {url: https://…, kind: carrier, checked: 2026-11-03}
    mvnos: [congstar, fraenk]
```
- A band is listed only when a source says the network **uses** it (deployed), not merely holds a licence. Preferred
  sources: the national regulator's spectrum/licence data and the network's own network or coverage pages; secondary
  lists (Wikipedia, band databases) only to cross-check, never as the sole source.
- Unknown is left out, not guessed. A network whose bands cannot be sourced is listed with `lte: null` and shows as
  "unknown".

### 4.3 Phone bands — `bands: {china, global}` in `config/specs/<id>.yaml`
Already supported by pricechecker/specs.py; today 4 sheets have it. Fill it for every phone and version from the
brand's own spec pages (the China version from the brand's China site), with `sources.<version>` and checked date, as
the sheets already do. A version whose maker publishes no band list stays without `bands` → "unknown".

### 4.4 Validation (tests, data-independent of prices)
Every band in carriers and sheets exists in bands.yaml; every network has at least one source with url, kind and
checked date; network ids unique; mvnos are strings; a `checked` older than 12 months is reported in the build log
(warning, not failure).

## 5. Verdict

`carrier_verdict(phone_bands, network)` in Python and JS (pure, parity-tested), for one version on one network:

| Verdict | Rule | Text example |
|---|---|---|
| Unknown | phone version or network bands not recorded | "Bands not published for this version" |
| Coverage risk | misses any of the network's `low` bands | "Coverage risk: no band 20 (800 MHz: coverage indoors and outside towns)" |
| 4G only | has every network LTE band but none of its NR bands | "4G works; no 5G on this network" |
| Minor gaps | misses only `mid`/`high`/`mmwave` bands | "Works; no band 7 (2600 MHz: extra speed in busy areas)" |
| Works fully | has every LTE and NR band the network uses | "Works fully on 4G and 5G" |

First matching row wins (top to bottom). "4G only" applies only to a network that runs at least one NR band. "Minor
gaps" lists every missing band, 5G ones included (e.g. a phone missing band 7 and all of the network's NR bands: "Works;
no band 7 (…); no 5G on this network"). Every result carries the line: "Bands only: calls over 4G (VoLTE) and Wi-Fi
calling depend on the network supporting the phone, which we can't check."

Country summary: count of networks per verdict for one version, e.g. "In Germany: works fully on 2 of 3 networks;
coverage risk on O2 (no band 20)".

## 6. On the page

- **Bands bullet** in "What the China version means": the country summary for the China version in the visitor's
  country. Replaces the fixed "Has all the main EU 4G/5G bands" / "Missing EU bands" text. EU with no country picked and
  Global → "Pick your country to check its networks" (link to the picker) plus the current EU main-band line.
- **Specs section, "Check your carrier"**: country (from settings; a select for Global or no country), then a carrier
  select listing networks and, under each, its virtual carriers ("congstar — on Telekom"). Result: one verdict line per
  version, side by side. The choice is kept in localStorage (`pc-carrier`), per-device only.
- The current "<version> version on EU networks" lines under Specs become the country summary per version.
- **No JS**: the server renders the summaries for the default settings; the picker needs JS.
- **Data loading**: carriers as one small JSON per country built into the site's data folder, fetched when the summary
  or picker needs it; phone bands embedded in the phone page's data attributes (a few hundred bytes).
- Blocks follow the site rule: a Jinja macro + a blocks.js function with the same structure, parity-tested.
- Phone page stays ≤ 60 KB.

## 7. Phases

Each phase is reviewed and can ship on its own.

1. **Band table, carrier dataset (31 countries), validator.** Research in batches by country group (e.g. 4–5 countries
   per batch), each batch reviewed for sourcing before the next. Ships nothing visible.
2. **Phone bands** for all catalog phones and versions, in batches by brand, reviewed for sourcing. Visible effect: the
   existing EU band check appears for many more phones.
3. **Verdict and page UI** (sections 5–6), replacing region_bands.yaml for the summary lines.

## 8. Testing

- Validator over all data files (phase 1 and 2).
- Verdict: synthetic phone/network cases for every row of the table, row order, unknown on either side; Python = JS.
- Country summary counts and wording; EU-no-country and Global fallbacks.
- Page tests: bullet and Specs lines follow the default settings country; picker markup present; budget.

## 9. Upkeep

Networks change bands (3G switch-offs re-used for 4G/5G, new 5G bands). Each network's `checked` date shows its age;
the build log lists networks checked more than 12 months ago so they can be re-checked.

## 10. Rollout

Phases 1–2: data commits, reviewed, to main (no visible risk). Phase 3: branch → testing site for the user → "publish"
= merge to main.
