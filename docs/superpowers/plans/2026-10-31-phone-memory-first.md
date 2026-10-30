# Phone page memory-first Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One memory pick drives the phone page: chips first, China and Global boxes priced at that memory, the chosen version's details as a panel under its box.

**Architecture:** The pick rules (nearest memory, which version stays selected) move into the shared view model (`pricechecker/site/view.py` + `static/js/view.js`) so server and browser agree; the blocks (`templates/_d/blocks.html` + `static/js/blocks.js`, parity-tested) gain the memory-priced box, the "not sold" state and the details panel; phone and compare pages wire them.

**Tech Stack:** Python 3.12 / Jinja2 / pytest; plain ES modules tested with node 22.

**Spec:** `docs/superpowers/specs/2026-10-31-phone-memory-first-design.md` (approved 2026-10-31). README "Front end" section has the blocks rule.

## Global Constraints

- Every settings-dependent block = one Jinja macro + one blocks.js function, same structure and classes, covered by the text+structure parity test in `tests/test_blocks.py`.
- Copy: "Not sold with <memory>" (memory as `memShort`, e.g. "16 GB + 1 TB"); nearest button "Nearest: <memShort> · <price> →"; cheaper-box line "<money> less"; all other copy unchanged.
- Default pick = the first "ok" row of `rows` across both versions (equals the `<title>` price).
- Hash format `#<ram>-<rom>-<global|china>` unchanged.
- Static relative JS imports only; escape every interpolated string; store links `rel="sponsored nofollow noopener" target="_blank"`.
- New tests use synthetic data unless they must read the build (then mark `live`); `pytest -m "not live"` must stay data-independent.
- Budgets: phone page ≤ 60 KB.
- Commits end with a blank line, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01BYAVrbwcDw6qv2MkP5jXH5`.

## Review Focus

1. Chip for a memory only the other version has → the selected version switches; panel, receipt, other stores follow (Task 1 + Task 3 tests).
2. Old shared hash for a memory no store sells any more → page falls back to the default pick, no empty panel (Task 3).
3. Phone whose only offers lack a listed memory ("base") → no chips, boxes show the base row (Task 2).
4. Settings change (region/pay) so the chosen memory has no "ok" row in either version → re-pick by `pick_for_memory`, never an empty panel (Task 3).
5. Nearest for a version with no "ok" row at any memory → no nearest button; the box keeps its existing state text (sold out / not delivered) (Task 1 + Task 2).

---

### Task 1: Pick rules in the view model

**Files:**
- Modify: `pricechecker/site/view.py`, `static/js/view.js`, `tests/js/view_cases.mjs`
- Modify: `static/js/compare.js` (import `nearestMemory` instead of its own `closest`)
- Test: `tests/test_view.py`

**Interfaces:**
- Produces (Py / JS): `nearest_memory(rows, edition, storage) -> str | None` / `nearestMemory(rows, edition, storage)`: among memories where `edition` has an "ok" row (excluding "base"), the one nearest `storage` by the existing compare `closest()` distance rule (move the rule here; first listed on a tie); `None`/`null` when there is none.
- Produces: `pick_for_memory(rows, storage, preferred) -> {"ed": str, "mem": str}` / `pickForMemory(rows, storage, preferred)`: keep `preferred` if it has an "ok" row at `storage`; else the other version if it has one; else the default pick (first "ok" row overall); if no "ok" row at all, `{ed: preferred, mem: storage}`.
- Produces: `default_pick(rows) -> {"ed", "mem"} | None` / `defaultPick(rows)`: first "ok" row's edition and storage.

- [ ] **Step 1: Failing tests** in `tests/test_view.py` on synthetic rows: `nearest_memory` returns "16/512" for want "16/1024" when global has 12/512 + 16/512; returns None for an edition with only sold-out rows (Review Focus 5); `pick_for_memory` keeps preferred, switches version (Review Focus 1), falls back to default when neither has it (Review Focus 2 data case); `default_pick` equals the first ok row. JS parity: the existing view parity harness compares all three for the 5 sample phones × all their memories × both preferred editions.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_view.py -q` — Expected: FAIL (names missing).
- [ ] **Step 3: Implement** in view.py and view.js; compare.js imports `nearestMemory`'s distance helper from view.js (delete its local `closest`, keep its exported name as a re-export only if tests import it).
- [ ] **Step 4: Run** test_view + compare node test — Expected: PASS.
- [ ] **Step 5: Commit** `view: nearest memory and memory-first pick rules (Python + JS)`

### Task 2: Blocks — chips, memory-priced boxes, details panel

**Files:**
- Modify: `templates/_d/blocks.html`, `static/js/blocks.js`, `pricechecker/site/blocks.py` (helpers), `static/d.css`, `tests/js/render_blocks.mjs`
- Test: `tests/test_blocks.py`

**Interfaces:**
- Consumes: Task 1 `nearest_memory`/`nearestMemory`.
- Produces (macro / JS, same names as today unless stated):
  - `mem_chips(rows, storage, s)` / `memChips(rows, storage, s)`: union of both versions' memories with any row (not "base"), sorted as `memOptions` sorts; label `memShort`, no price; `aria-pressed` on the chosen; `data-m`. A memory with no "ok" row in either version is `disabled`.
  - `price_box(rows, edition, storage, s, labels, on=False, switch=True)` / `priceBox(rows, edition, storage, s, labels, on, sw)`: priced from `best_of(rows, edition, storage)`; when none: existing state texts if the edition has rows at that memory (sold out / not delivered / stale), else "Not sold with <memShort(storage)>" plus, when `nearest_memory` exists, `<button class="near" data-m="<mem>">Nearest: <memShort> · <money> →</button>`; when both editions have an ok row at `storage`, both settled, and this one is cheaper: `<p class="less">€X less</p>`. With `switch`: the box root has `role="tab"`, `aria-selected`, `aria-controls="pick-panel"`, `id="tab-<edition>"`.
  - `verdict(row, pick, s, labels, now=None)` / `verdict(...)`: same content, root becomes `<section class="verdict panel" id="pick-panel" role="tabpanel" aria-labelledby="tab-<edition>">`.
  - `gap_line` / `gapLine`: deleted (and from the parity NAMES list).
- CSS: chips row above boxes; selected box joins the panel (shared border, no gap); `.near` button; `.less` line; light + dark.

- [ ] **Step 1: Failing parity + state tests** in `tests/test_blocks.py`: parity (text + structure) for price box at a memory both have, at a memory only China has (Global "Not sold with 16 GB + 1 TB" + nearest button with `data-m="16/512"`), for an edition with only sold-out rows (no nearest button — Review Focus 5), the "less" line, tab attributes; chips union for oppo-like fixture; chips empty for a base-only phone and the price box shows the base row (Review Focus 3); panel root attributes; `gap_line` no longer exported.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_blocks.py -q` — Expected: FAIL.
- [ ] **Step 3: Implement** macros, blocks.js, render_blocks.mjs entries, CSS.
- [ ] **Step 4: Run** test_blocks — Expected: PASS (phone/compare page tests may fail until Tasks 3–4; run them to see, do not fix pages here).
- [ ] **Step 5: Commit** `blocks: memory chips first, memory-priced boxes with not-sold/nearest, details panel`

### Task 3: Phone page wiring

**Files:**
- Modify: `templates/phone.html`, `pricechecker/site/pages/phone.py`, `static/js/phone.js`, `tests/js/phone_cases.mjs`
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: Task 1 `default_pick`/`pick_for_memory`; Task 2 blocks.
- Produces: `phone.js` exports `pickFromHash(rows, hash) -> {ed, mem}` (parseHash then `pickForMemory`; falls back to `defaultPick` when the hash memory has no ok row in either version) and keeps `pickHash`/`parseHash`; `pickAfterSwitch` and `initialPick` are replaced by the view helpers (delete them and their cases).

- [ ] **Step 1: Failing tests**: pytest (synthetic-data site via the existing `_synthetic` helper — not live): chips block precedes the boxes, no `gap_line`, exactly one `id="pick-panel"`, default pick's total equals the title price for 3 sample synthetic phones, phone page ≤ 60 000 bytes (live budget test unchanged). Node `phone_cases.mjs`: chip tap to a memory only the other version has switches `ed` (Review Focus 1); `pickFromHash` with a memory nobody sells → default (Review Focus 2); after a settings change where the chosen memory has no ok row, re-pick via `pickForMemory` (Review Focus 4); nearest button click sets that memory for both boxes.
- [ ] **Step 2: Run** the new tests — Expected: FAIL.
- [ ] **Step 3: Implement**: template order (kicker/H1/settings line → `#s-mems` → `#duel` → `#s-verdict` panel → receipt …); phone.py passes `v.mem` from `default_pick` and drops `v.gap`; phone.js: one state `{ed, mem}`, chip / box / nearest clicks → `pickForMemory` → paint all blocks, `history.replaceState` with `pickHash`, focus restore keys include `.near`; buy bar observes the panel's `.cta`.
- [ ] **Step 4: Run** full suite with `DOORPRICE_CHECK_BUDGETS=1` — Expected: PASS except compare page tests (Task 4).
- [ ] **Step 5: Commit** `phone: memory-first page — chips, both boxes at the pick, details panel`

### Task 4: Compare page adopts not-sold / nearest

**Files:**
- Modify: `static/js/compare.js`, `templates/compare.html` (if markup references the dashed state), `static/d.css` (remove `.cm-box.near` dashed styles)
- Test: `tests/js/compare_cases.mjs`, `tests/test_pages.py`

**Interfaces:**
- Consumes: Task 2 `priceBox(rows, edition, storage, …, sw=false)`.
- Produces: `shownMemory` removed; each column calls `priceBox` at the shared memory; nearest button click sets the shared memory (hash `@ram-rom`), same as a memory chip.

- [ ] **Step 1: Failing node cases**: a phone without the shared memory renders "Not sold with …" + nearest (no dashed substitute, no `near` class on the box); clicking nearest updates the hash memory; winners ignore columns showing "Not sold".
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** full suite with `DOORPRICE_CHECK_BUDGETS=1` and `-m "not live"` — Expected: both PASS.
- [ ] **Step 5: Commit** `compare: not-sold / nearest state replaces the dashed substitute memory`

### Task 5: Screenshots and testing site

**Files:** none new (uses `tools/screenshots.sh`).

- [ ] **Step 1:** `.venv/bin/python -m pricechecker.run --build-only --offline && tools/screenshots.sh <scratch dir>`; view phone (oppo-find-x9-ultra both versions, oneplus-16 China-only, a phone with a memory only one version has) and compare at 390/1280 light/dark; fix material layout issues (CSS only, re-shoot).
- [ ] **Step 2:** Controller pushes `memory-first:testing` (`git push origin memory-first:testing --force`), waits for the "Testing site" workflow, checks https://testing.pricechecker-87q.pages.dev/phones/oppo-find-x9-ultra, hands the link to the user. Publish = merge to main on the user's "publish".
