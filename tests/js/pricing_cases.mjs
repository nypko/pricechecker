// Runs every case in tests/fixtures/pricing_cases.json through static/js/pricing.js (the same cases test_pricing.py uses).
import { readFileSync } from "node:fs";
import * as P from "../../static/js/pricing.js";

// --offers <phone file> [--tax <tax file>]: print each offer's total (default EU,,card,eur; --settings region,area,pay,cur) as a JSON array instead of running the cases
const arg = (n) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
if (arg("--offers")) {
  const doc = JSON.parse(readFileSync(arg("--offers"), "utf8"));
  const tax = JSON.parse(readFileSync(arg("--tax") ?? new URL("../../config/import_tax.json", import.meta.url), "utf8"));
  const [region, area, pay, cur] = (arg("--settings") ?? "EU,,card,eur").split(",");   // region,area,pay,cur
  const s = { region, area, pay, cur };
  const rule = P.taxRule(tax, s);
  console.log(JSON.stringify(doc.offers.map((o) => P.cost(o, s, rule).total)));
  process.exit(0);
}

const CASES = JSON.parse(readFileSync(new URL("../fixtures/pricing_cases.json", import.meta.url), "utf8"));
let bad = 0;
const fail = (name, field, got, want) => { bad++; console.log(`FAIL ${name} ${field} got ${got} want ${want}`); };
const r2 = (x) => Math.round(x * 100) / 100;
const near = (a, b) => Math.abs(r2(a) - b) < 0.005;

for (const k of CASES.cases) {
  const [region, area, pay, cur] = k.settings;
  const s = { region, area, pay, cur };
  const c = P.cost(k.offer, s, P.taxRule(CASES.tax, s));
  const e = k.expect;
  if (!near(c.total, e.total)) fail(k.name, "total", r2(c.total), e.total);
  if ("tax_added" in e && !near(c.taxAdded, e.tax_added)) fail(k.name, "tax_added", r2(c.taxAdded), e.tax_added);
  if ("unknowns" in e && P.unknowns(c) !== e.unknowns) fail(k.name, "unknowns", P.unknowns(c), e.unknowns);
  if ("approx" in e && c.approx !== e.approx) fail(k.name, "approx", c.approx, e.approx);
  if ("pay_ok" in e && c.payOk !== e.pay_ok) fail(k.name, "pay_ok", c.payOk, e.pay_ok);
}

// the helpers test_pricing.py also pins
const run = (name) => {
  const k = CASES.cases.find((x) => x.name === name);
  const [region, area, pay, cur] = k.settings;
  const s = { region, area, pay, cur };
  return P.cost(k.offer, s, P.taxRule(CASES.tax, s));
};
const bank = run("bank_vs_sale_no_stack");
if (bank.promoPct !== 0 || r2(bank.adjAmt) !== -47.5) fail("bank_vs_sale_no_stack", "promo/adj", `${bank.promoPct}/${r2(bank.adjAmt)}`, "0/-47.5");
for (const [n, w] of [["card_free_ship_tax_paid", ""], ["ship_not_listed", "shipping and import tax"], ["duties_false_eu_avg", ""]]) {
  const got = P.leftOut(run(n));
  if (got !== w) fail(n, "leftOut", JSON.stringify(got), JSON.stringify(w));
}
const base = { list: 100, promoAmt: 0, promoPct: 0, base: 100, adj: 0, adjAmt: 0, ship: 0, shipMin: false, taxEst: null,
  taxAdded: 0, total: 100, approx: false, complete: true, payOk: true, old: false, duties: true };
const C = (o) => ({ ...base, ...o });
const checks = [
  [P.better(C({}), C({ payOk: false, total: 1 })), true, "pay beats price"],
  [P.better(C({ total: 500 }), C({ old: true, total: 1 })), true, "current beats old"],
  [P.better(C({ total: 108 }), C({ ship: null, total: 100 })), true, "fewer unknowns"],
  [P.better(C({ total: 99 }), C({ total: 100 })), true, "then price"],
  [P.better(C({ total: 100 }), C({ total: 100 })), false, "tie"],
];
for (const [got, want, what] of checks) if (got !== want) fail("better", what, got, want);

if (bad) process.exit(1);
console.log(`ok ${CASES.cases.length}`);
