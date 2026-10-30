// static/js/home.js: filter and sort, region and storage cases. node home_cases.mjs exits non-zero on the first failed case.
// node home_cases.mjs --summaries <home files, comma separated> <tax file>: prints {id: summary} for EU/card/EUR (parity check).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { filterRows, sortRows, summarize, groupRows, narrow, matches, listHtml } from "../../static/js/home.js";
import { DEFAULT } from "../../static/js/view.js";

if (process.argv[2] === "--summaries") {
  const offers = process.argv[3].split(",").flatMap((f) => JSON.parse(readFileSync(f, "utf8")).offers);
  const tax = JSON.parse(readFileSync(process.argv[4], "utf8"));
  const out = {};
  for (const [id, rows] of groupRows(offers, tax, DEFAULT)) out[id] = summarize(rows);
  console.log(JSON.stringify(out));
  process.exit(0);
}

const TAX = { EU: { rate_pct: 21, countries: {} }, UK: { rate_pct: 20 }, US: { rate_pct: 0 }, CA: { rate_pct: 13, provinces: {} }, AU: { rate_pct: 10 }, Global: { rate_pct: 0 } };
const money = (eur) => ({ eur, gbp: eur * 0.86, usd: eur * 1.16, cad: eur * 1.6, aud: eur * 1.75 });
const zero = money(0);
const offer = (id, edition, storage, eur, extra = {}) => ({
  id, edition, storage, money: money(eur), pay: { card: 0, paypal: 3.5, bank: 0 }, ship: { EU: zero, UK: zero, US: zero }, duties: { EU: true, UK: true, US: true },
  available: true, store_label: "Shop", ...extra });
const s = DEFAULT;

// ---- fixtures: Oppo X9 Ultra / X9 Pro / X90 Ultra, a Pixel sold by one store, a 1 TB phone ----
const meta = [
  { id: "oppo-find-x9-ultra", name: "Oppo Find X9 Ultra", brand: "Oppo", announced: "2026-10-10" },
  { id: "oppo-find-x9-pro", name: "Oppo Find X9 Pro", brand: "Oppo", announced: "2026-10-12" },
  { id: "oppo-find-x90-ultra", name: "Oppo Find X90 Ultra", brand: "Oppo", announced: "2026-04-01" },
  { id: "pixel-11", name: "Google Pixel 11", brand: "Google", announced: "2026-08-20" },
  { id: "galaxy-s27", name: "Samsung Galaxy S27 Ultra", brand: "Samsung", announced: "2026-07-01" },
  { id: "no-date", name: "Old Phone", brand: "Honor", announced: "" },
];
const offers = [
  offer("oppo-find-x9-ultra", "china", "16/512", 900), offer("oppo-find-x9-ultra", "global", "16/512", 1100),
  offer("oppo-find-x9-ultra", "china", "16/1024", 1000), offer("oppo-find-x9-ultra", "global", "16/1024", 1300),
  offer("oppo-find-x9-pro", "china", "12/256", 700),
  offer("oppo-find-x90-ultra", "global", "12/256", 600),
  offer("pixel-11", "global", "12/256", 800, { store_label: "Gomibo" }),
  offer("galaxy-s27", "global", "12/512", 1500), offer("galaxy-s27", "china", "12/512", 1450),
];
const by = groupRows(offers, TAX, s);
const phones = meta.map((m) => ({ ...m, s: summarize(by.get(m.id) || []) }));
const ids = (opts) => filterRows(phones, { chip: "all", brand: "", storage: "", q: "", watched: new Set(), ...opts });

// search: whole words, any order; the last word may be a prefix of 3+ letters; brand counts
assert.deepEqual(ids({ q: "x9 ultra", brand: "oppo" }), ["oppo-find-x9-ultra"]);
assert.deepEqual(ids({ q: "ultra x9", brand: "oppo" }), ["oppo-find-x9-ultra"]);
assert.deepEqual(ids({ q: "Ultra X9" }), ["oppo-find-x9-ultra"]);
assert.deepEqual(ids({ q: "x9 ult" }), ["oppo-find-x9-ultra"]);
assert.deepEqual(ids({ q: "x9" }), ["oppo-find-x9-ultra", "oppo-find-x9-pro"]);
assert.deepEqual(ids({ q: "google" }), ["pixel-11"]);
assert.deepEqual(ids({ q: "no such phone" }), []);
assert.ok(matches(phones[0], "  find   x9 "));
assert.ok(!matches(phones[0], "x"), "a lone letter is a whole word only");

// chips
assert.deepEqual(ids({ chip: "both" }), ["oppo-find-x9-ultra", "galaxy-s27"]);
assert.deepEqual(ids({ chip: "china" }), ["oppo-find-x9-ultra", "oppo-find-x9-pro", "galaxy-s27"]);
assert.deepEqual(ids({ chip: "global" }), ["oppo-find-x9-ultra", "oppo-find-x90-ultra", "pixel-11", "galaxy-s27"]);
assert.deepEqual(ids({ chip: "watched", watched: new Set(["no-date", "pixel-11"]) }), ["pixel-11", "no-date"], "watched keeps the list's order");
assert.deepEqual(ids({ brand: "samsung" }), ["galaxy-s27"]);

// storage: only phones sold with that storage stay (an empty rows phone has none)
assert.deepEqual(ids({ storage: "1024" }), ["oppo-find-x9-ultra"]);
assert.deepEqual(ids({ storage: "256" }), ["oppo-find-x9-pro", "oppo-find-x90-ultra", "pixel-11"]);
assert.deepEqual(ids({ storage: "512" }), ["oppo-find-x9-ultra", "galaxy-s27"]);
// ... and prices become each phone's cheapest at that storage
const one = narrow(by.get("oppo-find-x9-ultra"), 1024);
assert.deepEqual([...new Set(one.map((r) => r.storage))], ["16/1024"]);
assert.equal(summarize(by.get("oppo-find-x9-ultra"), 1024).cheap, one.find((r) => r.state === "ok").total);
assert.deepEqual(summarize(by.get("oppo-find-x9-ultra"), 1024).roms, [512, 1024], "the memories it is sold with don't shrink");

// sorts
const order = (sort, list = phones) => sortRows(list, sort);
assert.deepEqual(order("new"), ["oppo-find-x9-pro", "oppo-find-x9-ultra", "pixel-11", "galaxy-s27", "oppo-find-x90-ultra", "no-date"]);
// cheapest settled gap first (a bigger China saving), phones without a gap last in newest order
assert.ok(summarize(by.get("oppo-find-x9-ultra")).gap > summarize(by.get("galaxy-s27")).gap);
assert.deepEqual(order("save"), ["oppo-find-x9-ultra", "galaxy-s27", "oppo-find-x9-pro", "pixel-11", "oppo-find-x90-ultra", "no-date"]);
// lowest best ok total (any version), phones with no price last
assert.deepEqual(order("cheap"), ["oppo-find-x90-ultra", "oppo-find-x9-pro", "pixel-11", "oppo-find-x9-ultra", "galaxy-s27", "no-date"]);
// phones with a listing drop first, the biggest drop first; the rest keep newest order
const withDrops = phones.map((p) => ({ ...p, drop: { "pixel-11": 60, "galaxy-s27": 120 }[p.id] || 0 }));
assert.deepEqual(order("drop", withDrops), ["galaxy-s27", "pixel-11", "oppo-find-x9-pro", "oppo-find-x9-ultra", "oppo-find-x90-ultra", "no-date"]);

// a store that doesn't deliver to the region: the Global cell reads "–" (its Gomibo-only Pixel)
const us = { region: "US", area: "", pay: "card", cur: "usd" };
const pix = groupRows([offer("pixel-11", "global", "12/256", 800, { ship: { EU: zero, US: false }, store_label: "Gomibo" })], TAX, us).get("pixel-11");
const html = listHtml([{ ...meta[3], rows: pix }], us, "");
assert.match(html, /<span class="p none">Global<b>–<\/b><\/span>/);
assert.match(html, /<span class="p none">China<b>–<\/b><\/span>/);
const eu = listHtml([{ ...meta[3], rows: by.get("pixel-11") }], s, "");
assert.match(eu, /<span class="p gl">Global<b class="num">€/);
assert.match(eu, /<span class="p none">China<b>–<\/b>/);
// the Asia label for brands that use it
assert.match(listHtml([{ ...meta[0], l: "Asia", rows: by.get("oppo-find-x9-ultra") }], s, ""), /<span class="p cn">Asia</);
assert.match(listHtml([{ ...meta[0], rows: [] }], s, "../"), /href="\.\.\/phones\/oppo-find-x9-ultra"/);
// no price at all: both cells read "–" (the row stays; the server writes the same)
assert.match(listHtml([{ ...meta[5], rows: [] }], s, ""), /<span class="p none">China<b>–<\/b><\/span><span class="p none">Global<b>–<\/b><\/span>/);
console.log("home cases: ok");
