// The one view model every page renders from: a line-for-line mirror of pricechecker/site/view.py.
// Rows carry the same camelCase keys on both sides. No DOM, no I/O.
import { taxRule, cost, leftOut, unknowns } from "./pricing.js";

export const DEFAULT = { region: "EU", area: "", pay: "card", cur: "eur" };

const tail = (c, unknown) => c.ship === null ? (c.duties === null ? "+ shipping, tax?" : "+ shipping") : (unknown ? "+ tax?" : "");

const state = (o, c, s) => {
  if (!o.available) return "soldout";
  if ((o.ship || {})[s.region] === false) return "nodelivery";
  if (c.old) return "stale";
  return c.payOk ? "ok" : "nopay";
};

function row(o, c, s, st, taxName) {
  const unknown = unknowns(c);
  const days = (o.days || {})[s.region];
  return {
    store: o.store_label ?? null, edition: o.edition ?? null, storage: o.storage ?? null, link: o.link ?? null,
    days: days && days.length ? [...days] : null, trust: o.trust ?? null,
    promoLabel: (o.promo || {}).label ?? null,
    list: c.list, promoAmt: c.promoAmt, promoPct: c.promoPct, base: c.base, adj: c.adj,
    adjAmt: c.adjAmt, ship: c.ship, shipMin: c.shipMin, taxEst: c.taxEst, taxAdded: c.taxAdded,
    duties: c.duties, total: c.total, approx: c.approx, unknown,
    left: leftOut(c), tail: tail(c, unknown), settled: unknown === 0,
    payOk: c.payOk, old: c.old, available: !!o.available,
    delivers: (o.ship || {})[s.region] !== false, state: st,
    checked: o.checked ?? null, taxName,   // when the store's prices were read (ISO, UTC); the tax's name
  };
}

// Ranked ok/nopay/stale first (pricing.better order, offers with no listed RAM/storage included), then stores that
// don't deliver, then sold out.
export function rows(inputs, tax, s) {
  const rule = taxRule(tax, s);
  const all = inputs.map((o) => [o, cost(o, s, rule)]);
  const live = all.filter(([o]) => o.available && (o.ship || {})[s.region] !== false);
  // same order as pricing.rank: payment accepted, current, fewer unknowns, lower total (stable)
  live.sort(([, a], [, b]) => (!a.payOk - !b.payOk) || (a.old - b.old) || (unknowns(a) - unknowns(b)) || (a.total - b.total));
  const rest = all.filter(([o]) => !live.some(([x]) => x === o));
  const out = live.map(([o, c]) => row(o, c, s, state(o, c, s), rule.name));
  for (const want of ["nodelivery", "soldout"]) {
    for (const [o, c] of rest) if (state(o, c, s) === want) out.push(row(o, c, s, want, rule.name));
  }
  return out;
}

// The first (best) current, payable row of the edition; with storage, only that storage (exact match).
export function bestOf(rows, edition, storage = null) {
  return rows.find((r) => r.state === "ok" && r.edition === edition && (storage === null || r.storage === storage)) ?? null;
}

// China vs Global at the same RAM/storage: settled totals of ok rows only; the storage where China is cheapest.
export function gap(rows) {
  const best = new Map();
  for (const r of rows) {
    if (r.state !== "ok" || r.storage === "base" || !r.settled) continue;
    const k = `${r.storage}\0${r.edition}`;
    best.set(k, Math.min(r.total, best.get(k) ?? r.total));
  }
  const tiers = [...best.keys()].map((k) => k.split("\0")).filter(([st, e]) => e === "china" && best.has(`${st}\0global`)).map(([st]) => st);
  if (!tiers.length) return null;
  const st = tiers.reduce((a, b) => (best.get(`${b}\0china`) < best.get(`${a}\0china`) ? b : a));
  const china = best.get(`${st}\0china`), glob = best.get(`${st}\0global`);
  return { storage: st, china, global: glob, diff: Math.round((glob - china) * 100) / 100 };
}
