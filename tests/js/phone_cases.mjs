// static/js/phone.js's pure helper: node phone_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { pickAfterSwitch, pickHash, parseHash, focusSelector } from "../../static/js/phone.js";
import { memChips } from "../../static/js/blocks.js";

const r = (edition, storage, state = "ok") => ({ edition, storage, state });
const rows = [r("china", "12/256"), r("global", "12/512"), r("china", "16/512"), r("global", "12/256", "soldout"),
              r("global", "16/1024"), r("china", "16/1024", "stale")];

// the memory the page shows exists in the other version: kept
assert.equal(pickAfterSwitch(rows, "china", "16/512"), "16/512");
// it doesn't (or only sold out / stale there): that version's best memory (its first ok row)
assert.equal(pickAfterSwitch(rows, "global", "16/512"), "12/512");
assert.equal(pickAfterSwitch(rows, "global", "12/256"), "12/512");
assert.equal(pickAfterSwitch(rows, "china", "16/1024"), "12/256");
// a version with no current price at all: its first listed memory, else what was shown
assert.equal(pickAfterSwitch([r("china", "12/256"), r("global", "16/512", "soldout")], "global", "12/256"), "16/512");
assert.equal(pickAfterSwitch([r("china", "12/256")], "global", "12/256"), "12/256");

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

// a memory with no current price in the version is a disabled chip (a tap on it can't be undone by the page)
const s = { region: "EU", area: "", pay: "card", cur: "eur" };
const chips = memChips([{ ...r("china", "12/256"), total: 1000, unknown: 0 }, { ...r("china", "16/512", "stale"), total: 900, unknown: 0 }], "china", "12/256", s);
assert.match(chips, /data-m="16\/512" aria-pressed="false" disabled>16 GB · 512 GB · –</);
assert.doesNotMatch(chips, /data-m="12\/256"[^>]*disabled/);

// keyboard focus: the same control is found again after a repaint
const el = (tag, attrs, cls, boxId) => ({ tagName: tag, classList: cls ? [cls] : [], hasAttribute: (a) => a in attrs, getAttribute: (a) => attrs[a],
  closest: () => (boxId ? { id: boxId } : null) });
assert.equal(focusSelector(el("BUTTON", { "data-e": "global" }, "pick", "duel")), '#duel button.pick[data-e="global"]');
assert.equal(focusSelector(el("BUTTON", { "data-m": "12/256" }, null, "s-mems")), '#s-mems button[data-m="12/256"]');
assert.equal(focusSelector(el("BUTTON", { "data-s": "total" }, null, "s-ledger")), '#s-ledger button[data-s="total"]');
assert.equal(focusSelector(el("A", { "data-e": "china" }, "go", "duel")), null);
assert.equal(focusSelector(el("BUTTON", {}, "watch", "phone")), null);
assert.equal(focusSelector(null), null);
console.log("phone cases: ok");
