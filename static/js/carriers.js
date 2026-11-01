// Verdict of one phone version on one mobile network, and the country summary: a line-for-line mirror of the
// verdict section of pricechecker/carriers.py. No DOM, no I/O; the band table comes in as an argument.

export const KINDS_ORDER = ["unknown", "risk", "4g", "minor", "nogaps", "full"];
const GROUPS = ["risk", "4g", "minor", "nogaps", "full", "unknown"];   // the order the summary names them in

// the phone's bands plus every band they contain, following `covers` chains
function held(kind, have, table) {
  const covers = ((table.covers || {})[kind]) || {};
  const out = new Set(have), todo = [...have];
  while (todo.length) for (const s of covers[todo.pop()] || []) if (!out.has(s)) { out.add(s); todo.push(s); }
  return out;
}

// the network bands (`want`) the phone lacks; a phone band that contains the network band (table covers) counts
function missingBands(kind, have, want, table) {
  const h = held(kind, have, table);
  return want.filter((n) => !h.has(n)).map((n) => ({ kind, n, mhz: table[kind][n].mhz, use: table[kind][n].use }));
}

const label = (m) => m.kind === "lte" ? `no band ${m.n}` : `no 5G band n${m.n}`;
const unknown = (why) => ({ kind: "unknown", missing: [], text: `Bands not published for this ${why}` });

// [verdict, the first reason in short words, e.g. "no band 20"]; see verdict()
function judge(phone, network, table) {
  if (phone == null || ((phone.lte ?? null) === null && (phone.nr ?? null) === null)) return [unknown("version"), ""];
  const used = network.basis !== "licensed";   // mmWave counts only where the network is known to use it
  const keep = (kind, xs) => xs == null ? null : xs.filter((n) => used || table[kind][n].class !== "mmwave");
  const wlte = keep("lte", network.lte), wnr = keep("nr", network.nr);
  const plte = phone.lte ?? null, pnr = phone.nr ?? null;
  const lteKnown = wlte !== null && plte !== null, nrKnown = wnr !== null && pnr !== null;
  if (!((lteKnown && wlte.length) || (nrKnown && wnr.length))) {   // nothing left to compare
    const phoneSide = (wlte !== null && plte === null) || (wnr !== null && pnr === null);
    return [unknown(phoneSide ? "version" : "network"), ""];
  }
  const mLte = lteKnown ? missingBands("lte", plte, wlte, table) : [];
  const mNr = nrKnown ? missingBands("nr", pnr, wnr, table) : [];
  const missing = [...mLte, ...mNr];
  const low = missing.filter((m) => table[m.kind][m.n].class === "low");
  const who = `which ${network.name} ${network.basis === "licensed" ? "holds" : "uses"}`;
  const say = (m) => `${label(m)}, ${who} (${m.use})`;
  const complete = !!network.complete && lteKnown && nrKnown;
  if (low.length) return [{ kind: "risk", missing, text: "Coverage risk: " + low.map(say).join("; ") }, label(low[0])];
  if (nrKnown && wnr.length && lteKnown && !mLte.length && mNr.length === wnr.length) {
    return [{ kind: "4g", missing, text: "4G works; no 5G on this network" }, "no 5G"];
  }
  if (missing.length) {
    const no5g = mNr.length > 0 && mNr.length === wnr.length;   // all the network's 5G bands: one clause
    const clauses = [...mLte.map((m) => [label(m), say(m)]),
      ...(no5g ? [["no 5G on this network", "no 5G on this network"]] : mNr.map((m) => [label(m), say(m)]))];
    return [{ kind: "minor", missing, text: "Works; " + clauses.map((c) => c[1]).join("; ") }, clauses[0][0]];
  }
  if (!complete) return [{ kind: "nogaps", missing: [], text: "No gaps on the bands we could confirm" }, ""];
  return [{ kind: "full", missing: [], text: wnr.length ? "Works fully on 4G and 5G" : "Works fully on 4G" }, ""];
}

// {kind: unknown|risk|4g|minor|nogaps|full, missing: [{kind, n, mhz, use}], text}; first matching row wins.
// A null lte or nr on the network or on the phone is left out of the judgement and the result can then never be "full";
// if no band is left to compare the verdict is unknown. mmWave bands of a licensed network are ignored.
export const verdict = (phone, network, table) => judge(phone, network, table)[0];

const names = (xs) => xs.length === 1 ? xs[0] : xs.slice(0, -1).join(", ") + " and " + xs[xs.length - 1];

// {counts: {kind: n}, text}, networks grouped by verdict:
// "In Germany: works fully on 2 of 3 networks; coverage risk on O2 (no band 20)"
export function summary(phone, countryDoc, table, countryName) {
  const nets = countryDoc.networks || [];
  const counts = Object.fromEntries(KINDS_ORDER.map((k) => [k, 0]));
  const groups = Object.fromEntries(KINDS_ORDER.map((k) => [k, []]));
  for (const n of nets) {
    const [v, first] = judge(phone, n, table);
    counts[v.kind] += 1;
    groups[v.kind].push(v.kind === "risk" || v.kind === "minor" ? `${n.name} (${first})` : n.name);
  }
  if (phone == null || ((phone.lte ?? null) === null && (phone.nr ?? null) === null)) {
    return { counts, text: `In ${countryName}: bands not published for this version` };
  }
  const total = nets.length, full = counts.full;
  const parts = {
    full: !full ? "" : total === 1 ? "works fully on its only network"
      : full === total ? `works fully on all ${total} networks` : `works fully on ${full} of ${total} networks`,
    nogaps: groups.nogaps.length ? `no gaps found on ${names(groups.nogaps)}` : "",
    minor: groups.minor.length ? `minor gaps on ${names(groups.minor)}` : "",
    "4g": groups["4g"].length ? `4G only on ${names(groups["4g"])} (no 5G)` : "",
    risk: groups.risk.length ? `coverage risk on ${names(groups.risk)}` : "",
    unknown: groups.unknown.length ? `bands unknown on ${names(groups.unknown)}` : "",
  };
  return { counts, text: `In ${countryName}: ` + GROUPS.map((k) => parts[k]).filter((p) => p).join("; ") };
}

// ---- the visitor's country, the picker's names and the saved pick (pricechecker/carriers.py country_for / COUNTRY_NAMES) ----

export const COUNTRY_NAMES = {
  AT: "Austria", BE: "Belgium", BG: "Bulgaria", HR: "Croatia", CY: "Cyprus", CZ: "Czechia",
  DK: "Denmark", EE: "Estonia", FI: "Finland", FR: "France", DE: "Germany", GR: "Greece",
  HU: "Hungary", IE: "Ireland", IT: "Italy", LV: "Latvia", LT: "Lithuania", LU: "Luxembourg",
  MT: "Malta", NL: "Netherlands", PL: "Poland", PT: "Portugal", RO: "Romania", SK: "Slovakia",
  SI: "Slovenia", ES: "Spain", SE: "Sweden", GB: "United Kingdom", US: "United States",
  CA: "Canada", AU: "Australia" };

const REGION_COUNTRY = { UK: "GB", US: "US", CA: "CA", AU: "AU" };

/** The carrier country of the settings: EU -> its country (null until one is picked), UK -> GB, US, CA (any province), AU;
 *  Global -> null (the picker has its own country select). */
export const countryFor = (s) => s.region === "EU" ? (s.area || null) : (REGION_COUNTRY[s.region] || null);

/** The saved pick as the option value to select in `doc`'s network list: only when it is for this country `cc` and the
 *  network ("de-telekom", or a virtual carrier of it: "de-telekom|congstar") is still in the file; else null, and the
 *  picker says "Choose your network" (a stale or other-country pick is ignored, none is preselected). */
export function resolvePick(doc, saved, cc) {
  const nets = (doc && doc.networks) || [];
  const v = saved && saved.country === cc && typeof saved.network === "string" ? saved.network : "";
  const i = v.indexOf("|"), host = i < 0 ? v : v.slice(0, i), net = nets.find((n) => n.id === host);
  return net && (i < 0 || (net.mvnos || []).includes(v.slice(i + 1))) ? v : null;
}
