// Verdict of one phone version on one mobile network, and the country summary: a line-for-line mirror of the
// verdict section of pricechecker/carriers.py. No DOM, no I/O; the band table comes in as an argument.

export const KINDS_ORDER = ["unknown", "risk", "4g", "minor", "nogaps", "full"];

// the network bands (`want`) the phone lacks; a phone band that contains the network band (table covers) counts
function missingBands(kind, have, want, table) {
  const covers = ((table.covers || {})[kind]) || {};
  const held = new Set(have);
  for (const big of have) for (const s of covers[big] || []) held.add(s);
  return want.filter((n) => !held.has(n)).map((n) => ({ kind, n, mhz: table[kind][n].mhz, use: table[kind][n].use }));
}

const label = (m) => m.kind === "lte" ? `no band ${m.n}` : `no 5G band n${m.n}`;

// {kind: unknown|risk|4g|minor|nogaps|full, missing: [{kind, n, mhz, use}], text}; first matching row wins.
// A null lte or nr on the network or on the phone is left out of the judgement and the result can then never be "full".
export function verdict(phone, network, table) {
  const nlte = network.lte ?? null, nnr = network.nr ?? null;
  if (phone == null || ((phone.lte ?? null) === null && (phone.nr ?? null) === null)) {
    return { kind: "unknown", missing: [], text: "Bands not published for this version" };
  }
  if (nlte === null && nnr === null) return { kind: "unknown", missing: [], text: "Bands not published for this network" };
  const plte = phone.lte ?? null, pnr = phone.nr ?? null;
  const lteKnown = nlte !== null && plte !== null, nrKnown = nnr !== null && pnr !== null;
  if (!lteKnown && !nrKnown) {   // the phone's null list hides the only part the network has
    return { kind: "unknown", missing: [], text: "Bands not published for this version" };
  }
  const mLte = lteKnown ? missingBands("lte", plte, nlte, table) : [];
  const mNr = nrKnown ? missingBands("nr", pnr, nnr, table) : [];
  const missing = [...mLte, ...mNr];
  const low = missing.filter((m) => table[m.kind][m.n].class === "low");
  const who = `which ${network.name} ${network.basis === "licensed" ? "holds" : "uses"}`;
  const say = (m) => `${label(m)}, ${who} (${m.use})`;
  const complete = !!network.complete && lteKnown && nrKnown;
  let kind, text;
  if (low.length) {
    kind = "risk"; text = "Coverage risk: " + low.map(say).join("; ");
  } else if (nrKnown && nnr.length && lteKnown && !mLte.length && mNr.length === nnr.length) {
    kind = "4g"; text = "4G works; no 5G on this network";
  } else if (missing.length) {
    kind = "minor"; text = "Works; " + missing.map(say).join("; ");
  } else if (!complete) {
    kind = "nogaps"; text = "No gaps on the bands we could confirm";
  } else {
    kind = "full"; text = nnr && nnr.length ? "Works fully on 4G and 5G" : "Works fully on 4G";
  }
  return { kind, missing, text };
}

// {counts: {kind: n}, text}: e.g. "In Germany: works fully on 2 of 3 networks; coverage risk on O2 (no band 20)"
export function summary(phone, countryDoc, table, countryName) {
  const nets = countryDoc.networks || [];
  const counts = Object.fromEntries(KINDS_ORDER.map((k) => [k, 0]));
  const parts = [];
  for (const n of nets) {
    const v = verdict(phone, n, table);
    counts[v.kind] += 1;
    let first = v.missing.length ? label(v.missing[0]) : "";
    if (v.kind === "risk") first = label(v.missing.find((m) => table[m.kind][m.n].class === "low"));
    parts.push({
      unknown: `bands unknown on ${n.name}`, nogaps: `no gaps found on ${n.name}`,
      risk: `coverage risk on ${n.name} (${first})`, minor: `minor gaps on ${n.name} (${first})`,
      "4g": `4G only on ${n.name} (no 5G)`, full: "",
    }[v.kind]);
  }
  const total = nets.length, full = counts.full;
  const head = [];
  if (full) head.push(full === total ? `works fully on all ${total} network${total !== 1 ? "s" : ""}` : `works fully on ${full} of ${total} networks`);
  return { counts, text: `In ${countryName}: ` + [...head, ...parts.filter((p) => p)].join("; ") };
}
