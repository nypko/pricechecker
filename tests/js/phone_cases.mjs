// static/js/phone.js's pure helper: node phone_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { pickFromHash, pickHash, parseHash, focusSelector } from "../../static/js/phone.js";
import { memChips } from "../../static/js/blocks.js";
import { pickForMemory, nearestMemory } from "../../static/js/view.js";

const r = (edition, storage, state = "ok") => ({ edition, storage, state });
const rows = [r("china", "12/256"), r("global", "12/512"), r("china", "16/512"), r("global", "12/256", "soldout"),
              r("global", "16/1024"), r("china", "8/128", "stale"), r("global", "8/128", "soldout")];

// a chip tap: the selected version stays when it has a current price at the memory, else the other one is selected
assert.deepEqual(pickForMemory(rows, "16/512", "china"), { ed: "china", mem: "16/512" });
assert.deepEqual(pickForMemory(rows, "12/512", "china"), { ed: "global", mem: "12/512" });   // only Global has it: the version switches
assert.deepEqual(pickForMemory(rows, "12/256", "global"), { ed: "china", mem: "12/256" });   // Global's is sold out
// a memory nobody sells (or only sold out / stale): the default pick, the first ok row
assert.deepEqual(pickForMemory(rows, "8/128", "global"), { ed: "china", mem: "12/256" });
// after a settings change the chosen memory has no ok row any more: the same re-pick
const after = [r("china", "12/256", "nopay"), r("global", "12/512"), r("china", "16/512", "stale")];
assert.deepEqual(pickForMemory(after, "12/256", "china"), { ed: "global", mem: "12/512" });
// the nearest button: that memory for both boxes, on the box whose button it is
assert.equal(nearestMemory(rows, "global", "16/512"), "12/512");
assert.deepEqual(pickForMemory(rows, nearestMemory(rows, "global", "16/512"), "global"), { ed: "global", mem: "12/512" });

// a shared link's pick: memory and version for both boxes; a memory nobody sells is the default pick
assert.deepEqual(pickFromHash(rows, "#16-512-china"), { ed: "china", mem: "16/512" });
assert.deepEqual(pickFromHash(rows, "#12-512-china"), { ed: "global", mem: "12/512" });
assert.deepEqual(pickFromHash(rows, "#8-128-global"), { ed: "china", mem: "12/256" });
assert.deepEqual(pickFromHash(rows, "#99-9999-global"), { ed: "china", mem: "12/256" });
assert.equal(pickFromHash(rows, "#report-thanks"), null);
assert.equal(pickFromHash(rows, ""), null);

// the live site's shareable pick: #<ram>-<rom>-<version>
assert.equal(pickHash("china", "16/512"), "#16-512-china");
assert.equal(pickHash("global", "12/1024"), "#12-1024-global");
assert.equal(pickHash("china", "base"), "");
assert.equal(pickHash("china", null), "");
assert.equal(pickHash("asia", "12/256"), "");
assert.deepEqual(parseHash("#16-512-china"), { ed: "china", mem: "16/512" });
assert.deepEqual(parseHash("#12-1024-global"), { ed: "global", mem: "12/1024" });
for (const bad of ["", null, undefined, "#", "#16-512", "#16-512-asia", "#a-512-china", "16-512-china", "#16-512-china-x", "#report-thanks", "#16/512-china"]) {
  assert.equal(parseHash(bad), null, String(bad));
}
assert.deepEqual(parseHash(pickHash("global", "12/256")), { ed: "global", mem: "12/256" });

// a memory neither version has a current price for is a disabled chip (a tap on it can't be undone by the page); a phone
// with only "base" rows has no chips
const s = { region: "EU", area: "", pay: "card", cur: "eur" };
const chips = memChips([{ ...r("china", "12/256"), total: 1000, unknown: 0 }, r("china", "8/128", "stale"), r("global", "8/128", "soldout")], "12/256", s);
assert.match(chips, /data-m="8\/128" aria-pressed="false" disabled>/);
assert.doesNotMatch(chips, /data-m="12\/256"[^>]*disabled/);
assert.equal(memChips([r("china", "base")], "base", s), "");

// keyboard focus: the same control is found again after a repaint
const el = (tag, attrs, cls, boxId, own, side) => ({ tagName: tag, classList: cls ? [cls] : [], hasAttribute: (a) => a in attrs, getAttribute: (a) => attrs[a],
  parentElement: { closest: () => (boxId ? { id: boxId } : null) }, id: own || "",
  closest: () => (side ? { getAttribute: () => side } : null) });
assert.equal(focusSelector(el("BUTTON", { "data-e": "global" }, "pickbtn", "duel", "tab-global")), '#duel button.pickbtn[data-e="global"]');   // the select button has an id of its own
// a nearest button is gone after the repaint: the chip for its memory, else its box's select button
assert.equal(focusSelector(el("BUTTON", { "data-m": "12/512" }, "near", "duel", "", "global")), '#s-mems button[data-m="12/512"], #duel .side[data-e="global"] button.pickbtn');
assert.equal(focusSelector(el("BUTTON", { "data-m": "12/256" }, null, "s-mems")), '#s-mems button[data-m="12/256"]');
assert.equal(focusSelector(el("BUTTON", { "data-s": "total" }, null, "s-ledger")), '#s-ledger button[data-s="total"]');
assert.equal(focusSelector(el("A", { "data-e": "china" }, "go", "duel")), null);
assert.equal(focusSelector(el("BUTTON", {}, "watch", "phone")), null);
assert.equal(focusSelector(null), null);

// the price trend block follows the pick and the settings: after a memory, version or currency change it is built from
// that pick's series and currency (the paint step calls trendHtml with the pick and settings it just painted)
{
  const { trendHtml } = await import("../../static/js/phone.js");
  const { rows: viewRows } = await import("../../static/js/view.js");
  const tax = { EU: { rate_pct: 0 } };
  const offer = (label, ed, st, eur) => ({ store_label: label, edition: ed, storage: st, available: true, money: { eur, gbp: eur * 0.8 },
    pay: { card: 0 }, ship: { EU: { eur: 0, gbp: 0 } }, duties: { EU: true }, checked: "2026-10-30T11:00:00Z" });
  const days = Array.from({ length: 30 }, (_, i) => `2026-10-${String(i + 1).padStart(2, "0")}`);
  const flat = (ratio) => days.map((d) => [d, ratio]), fall = days.map((d) => [d, d === "2026-10-30" ? 1 : 1.2]);
  const doc = {
    offers: [offer("Shop", "china", "12/256", 1000), offer("Shop", "global", "12/256", 1200), offer("Shop", "china", "16/512", 1500)],
    trend: { china: { "12/256": { Shop: fall }, "16/512": { Shop: flat(1) } }, global: { "12/256": { Shop: flat(1) } } },
  };
  const eur = { region: "EU", area: "", pay: "card", cur: "eur" }, gbp = { ...eur, cur: "gbp" };
  const html = (s, ed, mem) => trendHtml(doc, tax, viewRows(doc.offers, tax, s), s, { ed, mem }, "2026-10-30T12:00:00Z", "../history/x");
  const text = (h) => h.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  const a = html(eur, "china", "12/256");
  assert.match(text(a), /€1,000 · low €1,000 – high €1,200 Lowest price in 30 days Down 17% since first listed \(1 Oct\)/);
  assert.match(text(html(eur, "global", "12/256")), /Same price since 1 Oct/);                      // the other version's series
  assert.match(text(html(eur, "china", "16/512")), /Same price since 1 Oct/);                      // the other memory's series
  assert.match(text(html(gbp, "china", "12/256")), /£800 · low £800 – high £960/);                 // the visitor's currency
  assert.equal(html(eur, "global", "16/512"), "");                                                 // no current price at the pick: empty
  assert.equal(trendHtml(doc, tax, viewRows(doc.offers, tax, eur), eur, { ed: "china", mem: "12/256" }, null, "../history/x").includes("price_trend"), true);
}

console.log("phone cases: ok");
