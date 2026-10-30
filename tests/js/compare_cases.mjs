// static/js/compare.js's pure helpers: node compare_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { closest, winners, parseHash, formatHash, differs, starters, shownMemory } from "../../static/js/compare.js";

// closest(): the same distance rule as the live app.js distance() (storage steps count double, RAM steps by 4 GB)
assert.equal(closest(["12/256", "16/512"], "16/1024"), "16/512");
assert.equal(closest(["12/256", "16/512"], "12/256"), "12/256");
assert.equal(closest(["12/256", "16/512"], "12/512"), "16/512");   // 4 GB more RAM is a smaller step than half the storage
assert.equal(closest(["12/256", "12/1024"], "12/512"), "12/256");   // tie on distance: the first listed
assert.equal(closest(["12/1024", "12/256"], "12/512"), "12/1024");
assert.equal(closest(["12/256", "16/1024"], "16/512"), "16/1024");
assert.equal(closest(["8/128", "12/256"], "16/1024"), "12/256");
assert.equal(closest(["base", "12/256"], "16/512"), "12/256");
assert.equal(closest(["base"], "16/512"), "base");
assert.equal(closest([], "16/512"), "");

// shownMemory(): which memory a version is priced at for the picked one, and whether that is a substitute
assert.deepEqual(shownMemory(["12/256", "16/512"], "16/512"), { mem: "16/512", near: false });
assert.deepEqual(shownMemory(["12/256", "16/512"], "16/1024"), { mem: "16/512", near: true });
assert.deepEqual(shownMemory(["12/256", "base"], ""), { mem: null, near: false });   // none picked: its own best
assert.deepEqual(shownMemory([], "16/512"), { mem: null, near: false });

// winners(): lowest settled total, biggest battery, fastest wired charging; a tie or no value marks nobody
const col = (total, battery, charging) => ({ total, battery, charging });
assert.deepEqual(winners([col(1200, 5000, 65), col(1100, 7050, 100), col(1300, 6000, 80)]), { price: 1, battery: 1, charging: 1 });
assert.deepEqual(winners([col(1200, 7050, 80), col(1300, 5000, 100), col(1100, 6000, 65)]), { price: 2, battery: 0, charging: 1 });
assert.deepEqual(winners([col(1000, 5000, 100), col(1000, 5000, 100)]), { price: -1, battery: -1, charging: -1 });
assert.deepEqual(winners([col(null, 0, 0), col(900, 4000, 0)]), { price: 1, battery: 1, charging: -1 });   // no price / no value: not a candidate
assert.deepEqual(winners([col(null, 0, 0), col(null, 0, 0)]), { price: -1, battery: -1, charging: -1 });
assert.deepEqual(winners([col(900, 4000, 30)]), { price: -1, battery: -1, charging: -1 });   // one phone: nothing to beat
assert.deepEqual(winners([]), { price: -1, battery: -1, charging: -1 });
// a column whose best price is still missing a cost is not a winner by price
assert.deepEqual(winners([{ total: 800, settled: false, battery: 0, charging: 0 }, col(900, 0, 0)]), { price: 1, battery: -1, charging: -1 });


// the hash: "#a,b,c@<ram>-<rom>" as the live site wrote it
const known = ["a", "b", "c", "d"];
assert.deepEqual(parseHash("#a,b,c@16-512", known), { ids: ["a", "b", "c"], mem: "16/512" });
assert.deepEqual(parseHash("#a,b", known), { ids: ["a", "b"], mem: "" });
assert.deepEqual(parseHash("#a,a,zzz,b,c,d@12-256", known), { ids: ["a", "b", "c"], mem: "12/256" });   // unknown and repeated dropped, max three
assert.deepEqual(parseHash("#a%2Cb", known), { ids: ["a", "b"], mem: "" });
assert.deepEqual(parseHash("#a,b@x-y", known), { ids: ["a", "b"], mem: "" });
assert.deepEqual(parseHash("#a@16-512-china", known), { ids: ["a"], mem: "" });
for (const bad of ["", null, undefined, "#", "#zzz", "#@16-512", "#%E0%A4%A"]) assert.deepEqual(parseHash(bad, known), { ids: [], mem: "" }, String(bad));
assert.deepEqual(parseHash("#q,r@16-512"), { ids: ["q", "r"], mem: "16/512" });   // without a list: nothing is dropped
assert.equal(formatHash(["a", "b", "c"], "16/512"), "#a,b,c@16-512");
assert.equal(formatHash(["a", "b"], ""), "#a,b");
assert.equal(formatHash([], "16/512"), "");
assert.equal(formatHash([], ""), "");
assert.deepEqual(parseHash(formatHash(["b", "a"], "12/1024"), known), { ids: ["b", "a"], mem: "12/1024" });

// "Show only the differences": a row differs when the chosen phones' cells aren't all the same
assert.equal(differs(["Dimensity", "Dimensity"]), false);
assert.equal(differs(["Dimensity", "Snapdragon"]), true);
assert.equal(differs([null, null]), false);
assert.equal(differs([null, "x"]), true);
assert.equal(differs([["a", "b"], ["a", "b"]]), false);
assert.equal(differs([["a", "b"], ["a", "c"]]), true);
assert.equal(differs(["x"]), false);

// starters(): the live site's one-tap comparisons, from the phone list
const ph = (id, brand, announced) => ({ id, name: id.toUpperCase(), brand, announced });
const list = [ph("a1", "A", "2026-01-01"), ph("a2", "A", "2026-05-01"), ph("a3", "A", "2026-03-01"), ph("b1", "B", "2026-09-01"),
  ph("b2", "B", "2026-02-01"), ph("c1", "C", "2026-10-01"), ph("d1", "D", "2025-01-01"), ph("e1", "E", "2026-06-01"), ph("e2", "E", "2026-07-01"),
  ph("e3", "E", "2026-08-01"), ph("f1", "F", "2024-01-01"), ph("f2", "F", "2024-02-01"), ph("f3", "F", "2024-03-01")];
// nothing chosen: the three newest, then the two newest of the brands with most phones (at most three, most first)
assert.deepEqual(starters(list, []), { heading: "Start with one of these", items: [
  { t: "The three newest phones", ids: ["c1", "b1", "e3"] },
  { t: "E3 vs E2", ids: ["e3", "e2"] },   // E, A and F have 3 each: the first-seen brand of equal size goes first
  { t: "A2 vs A3", ids: ["a2", "a3"] },
  { t: "F3 vs F2", ids: ["f3", "f2"] }] });
// the brands with one phone (C, D) are never offered a pair; with fewer than three phones there is still the newest line
assert.deepEqual(starters([ph("x", "X", "2026-01-01")], []).items, [{ t: "The three newest phones", ids: ["x"] }]);
// one chosen: its brand's two newest others, then the newest from another brand
assert.deepEqual(starters(list, ["a1"]), { heading: "Or compare A1 with:", items: [
  { t: "A2", ids: ["a1", "a2"] }, { t: "A3", ids: ["a1", "a3"] }, { t: "C1", ids: ["a1", "c1"] }] });
assert.deepEqual(starters(list, ["c1"]).items.map((x) => x.t), ["B1"]);   // no other C phone: only the newest of another brand
assert.deepEqual(starters(list, ["zzz"]), { heading: "", items: [] });
console.log("compare cases ok");
