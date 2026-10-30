// static/js/drops.js's pure helpers: node drops_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { keeps, findRow } from "../../static/js/drops.js";

const it = { brand: "oppo", edition: "china" };
assert.equal(keeps(it, { f: "all" }), true);
assert.equal(keeps(it, { f: "china" }), true);
assert.equal(keeps(it, { f: "global" }), false);
assert.equal(keeps(it, { b: "oppo" }), true);
assert.equal(keeps(it, { b: "vivo" }), false);

const rows = [{ store: "Giztop", edition: "china", storage: "12/256", total: 1 }, { store: "Giztop", edition: "global", storage: "12/256", total: 2 },
              { store: "Wonda Mobile", edition: "china", storage: "12/256", total: 3 }];
assert.equal(findRow(rows, { store: "Giztop", edition: "global", storage: "12/256" }).total, 2);
assert.equal(findRow(rows, { store: "Wonda Mobile", edition: "china", storage: "12/256" }).total, 3);
assert.equal(findRow(rows, { store: "Giztop", edition: "china", storage: "16/512" }), undefined);
