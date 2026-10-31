# Phone page: memory first

Status: APPROVED 2026-10-31. Follow-up to the D redesign (live since 31 Oct, main 1a98a4b).
Design agreed in conversation on 2026-10-31; the user picked "both boxes at the chosen memory".

## 1. Problem

The phone page shows two prices that answer different questions. The two price boxes on top always show each
version's cheapest memory; the verdict card below shows the memory the visitor picked. After tapping "16 GB + 1 TB" the
boxes still say €1,047 (12 + 256) while the verdict says €1,287, and three "View at…" buttons compete on one screen.

## 2. Goal

One pick drives the whole page: the visitor chooses a memory, sees China and Global at that same memory side by side,
and the chosen version's details sit directly under its box. One big store button per pick.

Not goals: changing prices, ranking, stores, data files, the home page, or any page other than phone and compare.

## 3. Page order (phone page)

1. Kicker, H1, settings line (unchanged).
2. **Memory chips**: every memory either version is sold with, sizes only ("12 GB + 256 GB"), no prices.
3. **Two price boxes**, China and Global, both priced at the chosen memory.
4. **Details panel** attached to the selected box (replaces the separate verdict card).
5. Receipt, other stores (+ delivery filters, ledger), China explainer, history, specs, more from brand: unchanged,
   all following the pick.

The same-memory gap line is removed: with both boxes at one memory the gap is visible. The cheaper box carries
"€384 less" under its price instead (only when both totals are settled, same rule as today's gap).

## 4. Behaviour

- **Default pick**: the cheapest current offer overall (its memory and version), so the first screen and the `<title>`
  "from €X" stay true.
- **Chip tap**: both boxes reprice at that memory. The selected version stays selected if it is sold with that memory
  (has an "ok" row); otherwise the other version becomes selected.
- **Box tap**: that version becomes selected; panel, receipt, other stores and ledger follow.
- **Version not sold with the memory**: its box shows "Not sold with <memory>" (by any store we check, at a current
  price) and a "Nearest: <memory> · <price> →" button that switches the whole page to that memory. Nearest = the
  existing `closest()` distance rule. Sold-out-only, no-delivery and stale-only cases keep their existing state texts
  inside the box.
- **Phone with one version**: one box (as today) plus the existing reason line; chips list that version's memories.
- **Details panel**: today's verdict content (version + memory pills, total, store, delivery days, why this one,
  badges, one "View at <store>" button, checked time, affiliate line), laid out as a panel visually attached to the
  selected box: toggle buttons (`aria-pressed`, `aria-controls`) in a labelled group, panel `role="region"` labelled by the picked button.
- **Store links**: each box keeps a small "View at <store>" link (both stores reachable from the first screen); the
  panel has the one big button. The buy bar follows the panel's button (pinned when the boxes scroll away, hidden while
  the panel button is visible) — unchanged rule, new anchor.
- **Shareable link** `#<ram>-<rom>-<global|china>` keeps its format and now sets memory and version for both boxes.
- **No JS**: the server renders the default pick; chips and boxes are plain links/buttons that do nothing without JS
  (as today), other memories reachable through the ledger.

## 5. Compare page

Compare already prices every phone at one shared memory. It adopts the same "Not sold with <memory> · Nearest …"
state from the shared price box instead of today's dashed "closest memory" substitute. Visible change: a phone without
the chosen memory no longer shows a substitute price silently — it says so and offers the nearest.

## 6. Code changes

Blocks (each = Jinja macro in templates/_d/blocks.html + function in static/js/blocks.js, parity-tested):
- `mem_chips(rows, storage, s)`: union of both versions' memories (no edition argument), sizes only, `aria-pressed`.
- `price_box(rows, edition, storage, s, labels, on, switch)`: priced at `storage`; new "not sold" state with the
  nearest button (`data-m` of the nearest memory); "€X less" line when it is the cheaper settled box.
- `verdict` → details panel markup (region), same content; `gap_line` removed.
- `buy_bar` unchanged.

Page wiring: templates/phone.html order; static/js/phone.js pick state (memory first), `pickAfterSwitch` replaced by
`pickForMemory(rows, storage, preferredEdition)` and `nearest(rows, edition, storage)` (pure, exported, node-tested);
static/js/compare.js uses the new price box state; static/d.css panel/tab styles. pages/phone.py default pick =
the first "ok" row of `view.rows` across both versions (the same ranking the `<title>` price uses; a test pins
them equal), and passes its `storage` to the blocks.

## 7. Testing

- Block parity (text + structure) for: price box at a memory, not-sold with nearest, "€X less", tab attributes,
  details panel, chips union.
- Node: `pickForMemory` (stay / switch version / both missing), `nearest`, hash round-trip still sets both boxes.
- Page tests: chips above boxes, no gap line, one panel, `<title>` price unchanged for 3 sample phones, budgets.
- Compare: node case for not-sold + nearest replacing the dashed substitute.
- Screenshots 390/1280 light/dark of phone (both versions, China-only, a memory only one version has) and compare.
- Hourly test split respected: new tests on synthetic data are not `live`.

## 8. Rollout

Branch `memory-first` from main → testing site (`git push origin memory-first:testing --force`) for the user to look
at → "publish" = merge to main (normal deploy; no data migration, so the newsite runbook is not needed).
