// static/js/compare.js's pure helpers: node compare_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { boxHtml, closest, column, memAfterClick, winners, parseHash, formatHash, differs, starters } from "../../static/js/compare.js";

// closest(): the distance rule the old front end used (storage steps count double, RAM steps by 4 GB)
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
// boxHtml(): the "Lowest delivered" label is inside the winning box, and only there
const w = boxHtml("<i>x</i>", true);
assert.match(w, /^<div class="cm-box low"><i>x<\/i><p class="cm-win">.*Lowest delivered.*<\/p><\/div>$/s);
assert.ok(!boxHtml("<i>x</i>", false).includes("Lowest delivered"));
assert.equal(boxHtml("x", false), '<div class="cm-box">x</div>');   // no dashed "near" variant any more

// column(): each version priced at the shared memory; no row there says "Not sold" and offers the nearest, never a substitute price
const row = (edition, storage, total, state = "ok") => ({ edition, storage, state, total, settled: true, store: "Shop", link: "https://shop.example/x", days: 3 });
const S0 = { cur: "eur" }, L = { global: "Global", china: "China" };
const txt = (h) => h.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ");
const phone = (rows, editions = ["china", "global"]) => column({ editions, cl: "China" }, rows, "16/512", S0);
const two = phone([row("china", "16/512", 900), row("global", "12/256", 800)]);
const both = two.html(true);
assert.ok(txt(both).includes("Not sold with 16 GB + 512 GB"), "global lacks 16/512");
assert.match(both, /<button type="button" class="near" data-m="12\/256">Nearest: 12 GB \+ 256 GB · €800 →<\/button>/);
assert.ok(!both.includes("cm-near") && !both.includes("cm-box near") && !both.includes("No 16"), "no dashed substitute");
assert.equal(both.split('class="big num"').length - 1, 2);
assert.ok(!both.includes('class="big num">€800'), "the nearest price is only on the button, not shown as the global price");
assert.ok(!both.includes("pickbtn") && !both.includes('role="tab"'), "plain boxes, no version switch");
// the winner ignores a column showing Not sold: €800 at 12/256 is not 16/512's price
assert.equal(two.total, 900);
assert.equal(phone([row("global", "12/256", 800)]).total, null);   // nothing at the shared memory: no price to rank
assert.equal(phone([row("global", "12/256", 800)]).html(false).includes("Nearest: 12 GB + 256 GB"), true);
assert.equal(phone([row("global", "16/512", 700, "soldout")]).total, null);   // sold out: a state, not a price
assert.ok(txt(phone([row("global", "16/512", 700, "soldout")]).html(false)).includes("Sold out at every store we check"));
const nsold = phone([row("global", "12/256", 800)]);   // global only, and not at 16/512: "Not sold" has no price to rank
assert.deepEqual(winners([{ total: nsold.total, battery: 0, charging: 0 }, { total: two.total, battery: 0, charging: 0 }]), { price: 1, battery: -1, charging: -1 });
// nothing picked: each version shows its own best, no "Not sold" anywhere
const free = column({ editions: ["china", "global"], cl: "China" }, [row("china", "16/512", 900), row("global", "12/256", 800)], "", S0);
assert.ok(!free.html(false).includes("Not sold") && free.total === 800);
// a nearest button sets the shared memory like a chip (hash @ram-rom); a chip toggles its own memory off
assert.equal(memAfterClick("16/512", "12/256", true), "12/256");
assert.equal(memAfterClick("12/256", "12/256", true), "12/256");
assert.equal(memAfterClick("12/256", "12/256", false), "");
assert.equal(memAfterClick("", "12/256", false), "12/256");
assert.equal(formatHash(["a", "b"], memAfterClick("16/512", "12/256", true)), "#a,b@12-256");
console.log("compare cases ok");
