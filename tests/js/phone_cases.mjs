// static/js/phone.js's pure helper: node phone_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { pickAfterSwitch } from "../../static/js/phone.js";

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
console.log("phone cases: ok");
