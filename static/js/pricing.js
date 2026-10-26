// The delivered-total rule in the browser: a line-for-line mirror of pricechecker/pricing.py (the single definition).
// tests/js/pricing_cases.mjs holds this file to the same cases as tests/test_pricing.py. No DOM, no I/O.
// s = {region, area, pay, cur}; offers and the tax config are the dicts the site build already makes.

// Python truthiness for the dict-valued fields: absent, null and {} are all "nothing there"
const has = (d) => !!d && Object.keys(d).length > 0;

export function taxRule(taxCfg, s) {
  const t = taxCfg[s.region] || {};
  const c = s.region === "EU" ? (t.countries || {})[s.area] : null;
  const shipTaxed = t.ship_taxed !== false;   // Canada taxes the phone only, not the international shipping
  const prov = s.region === "CA" ? (t.provinces || {})[s.area] : null;
  if (prov) return { rate: prov.rate, name: prov.tax, fee: null, shipTaxed };
  if (!c) return { rate: t.rate_pct ?? null, name: t.name || "import tax", fee: null, shipTaxed };
  return { rate: c.vat, name: "import VAT", fee: has(c.fee) ? c.fee : null, shipTaxed: true };
}

export function cost(o, s, rule) {
  const c = s.cur;
  const lst = o.money[c];
  let adj = (o.pay || {})[s.pay];
  if (adj === undefined) adj = null;
  let ship = (o.ship || {})[s.region];
  if (!has(ship)) ship = null;
  // store-wide automatic discount; with bank transfer only the larger discount counts unless they combine
  const pr = o.promo;
  const bankBeats = s.pay === "bank" && adj !== null && adj < 0 && !!pr && !pr.stacks_with_bank;
  const promoPct = !pr ? 0 : bankBeats ? (-adj >= pr.pct ? 0 : pr.pct) : pr.pct;
  if (promoPct && bankBeats) adj = 0;
  const promoAmt = lst * promoPct / 100;
  const base = lst - promoAmt;
  const adjAmt = adj === null ? 0 : base * adj / 100;
  const shipAmt = ship ? ship[c] : 0;
  const duties = (o.duties || {})[s.region];
  const vat = rule.rate === null ? null : (base + adjAmt + (rule.shipTaxed ? shipAmt : 0)) * rule.rate / 100;
  const taxFee = vat !== null && rule.fee ? Math.max(vat * rule.fee.pct / 100, rule.fee.min_m[c]) : 0;
  const taxEst = vat === null ? null : vat + taxFee;
  const taxAdded = duties === false && taxEst !== null ? taxEst : 0;
  const approxMoney = o.money[c + "_approx"] === 1;
  const shipMin = !!(ship && ship.min);
  return {
    list: lst, promoAmt, promoPct, base, adj, adjAmt,
    ship: ship ? shipAmt : null, shipMin,   // the store publishes only a starting price ("from EUR 10")
    taxEst, taxAdded,
    total: base + adjAmt + shipAmt + taxAdded,
    approx: approxMoney || taxAdded > 0 || shipMin,
    complete: adj !== null && !!ship,
    payOk: !has(o.pay_ok) || o.pay_ok[s.pay] !== false,
    old: !!o.old,   // the store hasn't answered for days: its price ranks after current ones
    duties: duties === undefined ? null : duties,
  };
}

// What a total leaves out: shipping the store doesn't list, import tax that may still be due
const maybeTax = (c) => c.duties !== true && !c.taxAdded;

export function leftOut(c) {
  return [["shipping", c.ship === null], ["import tax", maybeTax(c)]].filter(([, gone]) => gone).map(([x]) => x).join(" and ");
}

// Fewer unknowns lead: unlisted shipping weighs 2, import tax that may be due 1; a "from EUR 10" floor is known.
export function unknowns(c) {
  return (c.ship === null ? 2 : 0) + (maybeTax(c) ? 1 : 0);
}

// True when a ranks ahead of b: payment accepted, then current over old, then fewer unknowns, then lower total.
export function better(a, b) {
  if (a.payOk !== b.payOk) return a.payOk;
  if (a.old !== b.old) return !a.old;
  if (unknowns(a) !== unknowns(b)) return unknowns(a) < unknowns(b);
  return a.total < b.total;
}
