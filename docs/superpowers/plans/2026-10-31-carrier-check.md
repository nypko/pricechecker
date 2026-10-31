# Carrier Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For every phone and version, say how it does on each mobile network in the visitor's country (31 countries), from sourced band data: works fully, minor gaps, coverage risk, 4G only, or unknown.

**Architecture:** Three phases. (1) A band table and one sourced carrier file per country, with a validator. (2) Sourced band lists for every catalog phone and version in the existing spec sheets. (3) A pure verdict (Python + JS, parity-tested), per-country carrier data files, and two page surfaces: the "What the China version means" bands bullet (country summary) and a "Check your carrier" picker under Specs, replacing the fixed EU band check.

**Tech Stack:** Python 3.12 / PyYAML / Jinja2 / pytest; plain ES modules tested with node 22 (venv `.venv`).

**Spec:** `docs/superpowers/specs/2026-10-31-carrier-check-design.md` (approved 2026-10-31).

## Global Constraints

- Countries: the 27 EU member states, GB, US, CA, AU (31), ISO codes; the "Global" region picks one of these.
- Carriers: every mobile network operator with its own radio network in each country, plus a pointer list of the best-known virtual carriers per network (`mvnos`).
- Sourcing: a band is listed only when a source says the network **uses** it (deployed, not merely licensed). Preferred sources: national regulator spectrum/licence data, the network's own network/coverage pages; secondary lists (Wikipedia, band databases) only to cross-check, never the sole source. Unknown → `lte: null` / `nr: null`, never guessed. Same rule for phone bands: the brand's own pages (China version from the brand's China site).
- Every source entry: `{url, kind: regulator|carrier|brand|other, checked: YYYY-MM-DD}`.
- Band classes (from `config/bands.yaml` only): `low` < 1 GHz, `mid` 1–2.7 GHz, `high` 3–7 GHz, `mmwave` > 24 GHz.
- Verdict rows, first match wins: Unknown → Coverage risk (misses any network `low` band) → 4G only (network runs ≥ 1 NR band; phone has every network LTE band and none of its NR bands) → Minor gaps (misses only mid/high/mmwave; lists every missing band, 5G ones included) → Works fully.
- Copy (exact): "Bands not published for this version"; "Coverage risk: no band 20 (800 MHz: coverage indoors and outside towns)"; "4G works; no 5G on this network"; "Works; no band 7 (2600 MHz: extra speed in busy areas)"; "Works fully on 4G and 5G"; caveat "Bands only: calls over 4G (VoLTE) and Wi-Fi calling depend on the network supporting the phone, which we can't check."; summary "In Germany: works fully on 2 of 3 networks; coverage risk on O2 (no band 20)"; no country → "Pick your country to check its networks".
- localStorage key `pc-carrier` (per device); wrap every storage access in try/catch.
- Every block = Jinja macro + blocks.js function, same structure/classes, parity-tested; static relative JS imports; escape interpolated strings; phone page ≤ 60 KB.
- New tests synthetic or config-only (not `live`); `pytest -m "not live"` stays price-data-independent.
- Commits end with a blank line, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01BYAVrbwcDw6qv2MkP5jXH5`.

## Review Focus

1. A network whose bands are unknown (`lte: null`) → "unknown" for that network, never "works fully"; the country summary counts it separately (Task 9).
2. A phone version with bands but the network runs no 5G → never "4G only" (Task 9).
3. Visitor region CA with a province, or EU with no country, or Global → summary uses CA / prompts for a country; never shows another country's networks (Task 11).
4. A saved `pc-carrier` for a network removed from the data, or from another country → ignored, picker falls back to the first network (Task 11).
5. Research batches citing only Wikipedia → rejected by review; validator flags a network whose only source `kind` is `other` (Task 1).

---

## Phase 1 — band table, carriers, validator

### Task 1: Band table, carrier loader and validator

**Files:**
- Create: `config/bands.yaml`, `config/carriers/README.md` (format + sourcing rule, short), `pricechecker/carriers.py`
- Modify: `pricechecker/specs.py` (validate phone bands against the band table)
- Test: `tests/test_carriers.py`, `tests/test_specs.py`

**Interfaces:**
- Produces `config/bands.yaml`: `lte: {<n>: {mhz: <int>, class: low|mid|high|mmwave, use: "<plain words>"}}`, `nr: {…}` covering at least LTE 1, 2, 3, 4, 5, 7, 8, 12, 13, 14, 17, 18, 19, 20, 25, 26, 28, 29, 30, 32, 34, 38, 39, 40, 41, 42, 43, 46, 48, 53, 66, 71, 106 and NR 1, 2, 3, 5, 7, 8, 12, 14, 20, 25, 26, 28, 29, 30, 38, 40, 41, 48, 53, 66, 70, 71, 75, 76, 77, 78, 79, 257, 258, 260, 261 (mhz = the band's nominal downlink frequency; `use` e.g. 20 → "800 MHz: coverage indoors and outside towns", 7 → "2600 MHz: extra speed in busy areas", n78 → "3.5 GHz: the main 5G band").
- Produces `pricechecker/carriers.py`: `COUNTRIES: tuple[str, ...]` (31 codes), `load(dir=Path("config/carriers")) -> dict[str, dict]` (country → file), `band_table() -> dict`, `band_class(kind: "lte"|"nr", n: int) -> str`, `validate(doc: dict, table: dict) -> list[str]` (errors), `stale(doc: dict, today: date, months: int = 12) -> list[str]` (network ids).
- Validate rules: `country` in COUNTRIES and equals file name; network `id` unique across all files; `name` non-empty; `lte`/`nr` a list of known bands or null; ≥ 1 source with url (https), kind, checked; a network whose sources are all `kind: other` is an error (Review Focus 5); `mvnos` list of strings.

- [ ] **Step 1: Failing tests** — valid sample file passes; each rule above fails with a message naming the network; `stale` lists a network checked 13 months ago; specs.validate rejects a phone band missing from the table.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest -q tests/test_carriers.py tests/test_specs.py` — FAIL.
- [ ] **Step 3: Implement** the table, loader, validator; add a non-live test `test_all_carrier_files_valid` over `config/carriers/*.yaml` (passes with zero files) and log `stale` networks in the build (pricechecker/site/__init__.py, one log line per network).
- [ ] **Step 4: Run** — PASS; `-m "not live"` — PASS.
- [ ] **Step 5: Commit** `carriers: band table, carrier file format and validator`

### Tasks 2–7: Carrier research, one batch of countries each

Same steps for every batch; only the country list differs:

| Task | Countries |
|---|---|
| 2 | DE, AT, NL, BE, LU |
| 3 | FR, IT, ES, PT, MT |
| 4 | PL, CZ, SK, HU, SI, HR |
| 5 | BG, RO, GR, CY |
| 6 | SE, DK, FI, EE, LV, LT, IE |
| 7 | GB, US, CA, AU |

**Files:** Create `config/carriers/<CC>.yaml` per country in the batch.

- [ ] **Step 1:** For each country list every operator with its own radio network (regulator's operator list as the source of truth for who exists).
- [ ] **Step 2:** For each network record deployed LTE and NR bands with sources per the Global Constraints sourcing rule, and its best-known virtual carriers (`mvnos`, a handful at most, each verified to run on that network).
- [ ] **Step 3: Run** `.venv/bin/python -m pytest -q tests/test_carriers.py` — PASS (validator over all files).
- [ ] **Step 4:** Write a batch report (`.superpowers/carriers-<task>.md`): per network, bands and the sentence from each source that supports them; anything left null and why.
- [ ] **Step 5: Commit** `carriers: <CC, CC, …> networks and bands (sourced)`

## Phase 2 — phone bands

### Tasks 8a–8e: Phone band lists, one batch of brands each

| Task | Brands (catalog phones) |
|---|---|
| 8a | Huawei (17) |
| 8b | Xiaomi, Redmi (14) |
| 8c | Vivo, iQOO (12) |
| 8d | Honor, Oppo, OnePlus, Realme (20) |
| 8e | Google, Samsung, Motorola, Sony, Apple (15) |

**Files:** Modify `config/specs/<id>.yaml` for each phone in the batch.

- [ ] **Step 1:** For each phone and each version it is sold in (catalog editions plus editions present in offers), read the brand's own spec page for that version (China version: the brand's China site) and fill `bands.<version>` with `lte` / `nr` lists and `sources.<version>` with url and checked date. No published list → leave `bands.<version>` out.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest -q tests/test_specs.py tests/test_carriers.py` — PASS.
- [ ] **Step 3:** Batch report (`.superpowers/phone-bands-<task>.md`): per phone/version, source URL, and the versions left without bands and why.
- [ ] **Step 4: Commit** `specs: <brands> band lists (sourced)`

## Phase 3 — verdict and page

### Task 9: Verdict and country summary (Python + JS)

**Files:**
- Modify: `pricechecker/carriers.py`; Create: `static/js/carriers.js`, `tests/js/carrier_cases.mjs`
- Test: `tests/test_carriers.py`

**Interfaces:**
- Consumes: Task 1 band table.
- Produces: `verdict(phone: dict | None, network: dict, table: dict) -> dict` / `verdict(phone, network, table)`: `{"kind": "unknown"|"risk"|"4g"|"minor"|"full", "missing": [{"kind": "lte"|"nr", "n": int, "mhz": int, "use": str}], "text": str}` per the Global Constraints rows and copy; `phone` = `{lte: [...], nr: [...]}` or None.
- Produces: `summary(phone, country_doc, table, country_name) -> dict` / same in JS: `{"counts": {kind: n}, "text": str}`; text format per Global Constraints ("In Germany: works fully on 2 of 3 networks; coverage risk on O2 (no band 20)"; every non-full network named with its first reason; unknown networks counted as "bands unknown on <name>").
- Country names: one map `COUNTRY_NAMES` in carriers.py, emitted into the carrier data files (Task 10) so JS doesn't hold a second copy.

- [ ] **Step 1: Failing tests** for every verdict row and the row order; unknown network → unknown (Review Focus 1); network without NR → never "4g" (Review Focus 2); minor-gaps text lists missing NR too; summary wording for all-full, mixed, all-unknown; Python == JS via `node tests/js/carrier_cases.mjs` from pytest.
- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** both.
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `carriers: verdict and country summary (Python + JS)`

### Task 10: Carrier data files and phone bands on the page

**Files:**
- Modify: `pricechecker/site/data_files.py`, `pricechecker/site/pages/phone.py` (`_bands`, page context), `templates/phone.html` (data attributes)
- Test: `tests/test_data_files.py`, `tests/test_pages.py`

**Interfaces:**
- Produces: data files `carriers/<CC>` (one per country, same hashed `_put` scheme; logical names in the returned map) holding `{"v": 1, "country", "name", "networks": [{id, name, lte, nr, mvnos}], "bands": <the band table subset used>}`.
- Produces: phone page root data attributes `data-bands='{"china": {...}|null, "global": ...}'` and `data-carriers` = `{CC: path}` map; phone.py context `v.carrier` = summary per version for the default settings' country (EU with `area` "" → None).

- [ ] **Step 1: Failing tests**: data file per country with the fields above; phone page carries `data-bands` with the sheet's bands; no `data-bands` entry invented for a version without bands; page size within budget.
- [ ] **Step 2: Run** — FAIL.  **Step 3: Implement.**  **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `site: carrier data files and phone bands on the phone page`

### Task 11: Bands bullet, Specs carrier picker, wiring

**Files:**
- Modify: `templates/_d/blocks.html`, `static/js/blocks.js`, `tests/js/render_blocks.mjs`, `templates/phone.html`, `static/js/phone.js`, `static/d.css`; Delete the use of `config/region_bands.yaml` from the phone page (keep the file only if another page still reads it — check `specs.band_check` callers)
- Test: `tests/test_blocks.py`, `tests/test_pages.py`, `tests/js/phone_cases.mjs`

**Interfaces:**
- Consumes: Tasks 9–10.
- Produces: block `carrier_summary(sum, s)` (the bands bullet text; no country → "Pick your country to check its networks" with a link to `#carrier`) and block `carrier_check(country_doc, bands, picked, labels, s)` (`<section id="carrier" data-block="carrier_check">`: country select shown only for Global / EU without country, carrier select listing networks with `optgroup`-free options "Telekom" and indented MVNO options "congstar — on Telekom" mapping to the host network, one verdict line per version side by side, the caveat line).
- The Specs section's "<version> version on EU networks" lines become the country summary per version (same `carrier_summary` text, one line per version).
- Country from settings: EU → `area`; UK → GB; CA (any province) → CA; US → US; AU → AU; Global or EU without area → the picker's own country select (Review Focus 3).
- `pc-carrier` stores `{country, network}`; a saved network not in the loaded country file is ignored (Review Focus 4).

- [ ] **Step 1: Failing tests**: block parity for both blocks (all verdict kinds, no country, Global); page tests: bullet replaced (no "EU networks" text), `#carrier` present under Specs, default settings render the summary server-side; node cases for Review Focus 3 and 4.
- [ ] **Step 2: Run** — FAIL.  **Step 3: Implement** blocks, CSS (light/dark), phone.js (load `data-carriers[CC]` on demand, repaint on settings change, persist `pc-carrier`).
- [ ] **Step 4: Run** full suite with `DOORPRICE_CHECK_BUDGETS=1` and `-m "not live"` — PASS.
- [ ] **Step 5: Commit** `phone: carrier check — country summary in the bands bullet, carrier picker under Specs`

### Task 12: Screenshots and testing site

- [ ] **Step 1:** Build offline; screenshots at 390/1280 light/dark of: a phone with a coverage risk in one country, the iPhone Duo (works fully), a phone with unknown bands, settings EU-without-country and Global; fix material layout issues (CSS only), re-shoot.
- [ ] **Step 2:** Controller pushes to `testing` (fast-forward only; force-push is blocked — ask the user if needed), checks the page, hands the link to the user. Publish = merge to main on the user's word.
