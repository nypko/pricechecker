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

// The one order every store list shows: priced rows in pricing.better order (offers with no listed RAM/storage
// included) except that stale rows come after all the others, then stores that don't deliver, then sold out.
export function rows(inputs, tax, s) {
  const rule = taxRule(tax, s);
  const all = inputs.map((o) => [o, cost(o, s, rule)]);
  const live = all.filter(([o]) => o.available && (o.ship || {})[s.region] !== false);
  // same order as pricing.rank: payment accepted, current, fewer unknowns, lower total (stable)
  live.sort(([, a], [, b]) => (!a.payOk - !b.payOk) || (a.old - b.old) || (unknowns(a) - unknowns(b)) || (a.total - b.total));
  const rest = all.filter(([o]) => !live.some(([x]) => x === o));
  const priced = live.map(([o, c]) => row(o, c, s, state(o, c, s), rule.name));
  const out = [...priced.filter((r) => r.state !== "stale"), ...priced.filter((r) => r.state === "stale")];
  for (const want of ["nodelivery", "soldout"]) {
    for (const [o, c] of rest) if (state(o, c, s) === want) out.push(row(o, c, s, want, rule.name));
  }
  return out;
}

// The first (best) current, payable row of the edition; with storage, only that storage (exact match).
export function bestOf(rows, edition, storage = null) {
  return rows.find((r) => r.state === "ok" && r.edition === edition && (storage === null || r.storage === storage)) ?? null;
}

const CUR = ["eur", "usd", "gbp", "cad", "aud"];

// The best delivered price of the edition/storage on each day with a point: a point's store re-priced as its current
// offer with the point's ratio applied, ranked by rows/bestOf so delivery, payment and staleness rules are today's.
export function dailyBest(inputs, trend, edition, storage, tax, s) {
  const series = ((trend || {})[edition] || {})[storage] || {};
  const days = new Map();
  for (const [label, points] of Object.entries(series)) {
    const cur = inputs.find((o) => o.store_label === label && o.edition === edition && o.storage === storage);
    if (!cur) continue;
    for (const [day, ratio] of points) {
      // approximation: history has only the native price, so every currency is scaled by the same ratio
      const money = Object.fromEntries(Object.entries(cur.money || {}).map(([k, v]) => [k, CUR.includes(k) ? v * ratio : v]));
      if (!days.has(day)) days.set(day, []);
      days.get(day).push({ ...cur, money, available: true });
    }
  }
  const out = [];
  for (const day of [...days.keys()].sort()) {
    const best = bestOf(rows(days.get(day), tax, s), edition, storage);
    if (best) out.push({ day, total: best.total, store: best.store, approx: best.approx });
  }
  return out;
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

export const size = (s) => { const p = String(s || "").split("/"); return p.length === 2 ? { ram: +p[0], rom: +p[1] } : null; };

/** How far two RAM/storage options are apart: a storage step counts double, RAM counts per 4 GB (the old front end's distance()). */
export function distance(a, b) {
  const x = size(a), y = size(b);
  if (!x || !y) return 99;
  return Math.abs(Math.log(x.rom / y.rom) / Math.LN2) * 2 + Math.abs(x.ram - y.ram) / 4;
}

/** The option in `storages` nearest to `want` (the first listed on a tie); "" when there are none. */
export function closest(storages, want) {
  let best = "", bd = Infinity;
  for (const s of storages) {
    const d = s === want ? 0 : distance(s, want);
    if (d < bd) { best = s; bd = d; }
  }
  return best;
}

// The memory nearest `storage` among those the edition has a current, payable row for (never "base").
export function nearestMemory(rows, edition, storage) {
  const have = rows.filter((r) => r.state === "ok" && r.edition === edition && r.storage !== "base").map((r) => r.storage);
  return closest(have, storage) || null;
}

// The first (best) current, payable row's edition and storage.
export function defaultPick(rows) {
  const r = rows.find((x) => x.state === "ok");
  return r ? { ed: r.edition, mem: r.storage } : null;
}

// The version to show once a memory is picked: the preferred one if it has a current price there, else the other
// version, else the default pick; with nothing current at all, the preferred version at that memory.
export function pickForMemory(rows, storage, preferred) {
  const other = preferred === "china" ? "global" : "china";
  for (const ed of [preferred, other]) if (bestOf(rows, ed, storage)) return { ed, mem: storage };
  return defaultPick(rows) ?? { ed: preferred, mem: storage };
}
