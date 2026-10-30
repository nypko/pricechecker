// The D blocks: every price on the site is shown through one of these. Each is the twin of a Jinja macro in
// templates/_d/blocks.html (same name in snake_case, same root element, class and text); the text helpers mirror
// pricechecker/site/blocks.py. tests/test_blocks.py keeps the two sides equal. Pure: each returns an HTML string; page
// modules insert it and wire the buttons (data-e, data-m). Rows come from view.js; s = {region, area, pay, cur};
// labels = the brand's edition names {global, china}. No DOM, no I/O, no dynamic import().
import { bestOf, gap } from "./view.js";
import { PAY_BY, PLACE } from "./settings.js";

const SYMBOL = { eur: "€", gbp: "£", usd: "$", cad: "C$", aud: "A$" };
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const LINK = 'rel="sponsored nofollow noopener" target="_blank"';

/** Escape for HTML text and attribute values: every string that comes from data goes through this. */
export const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// |v| scaled by 10^dec and rounded half up (written out: toLocaleString/toFixed round differently from Python)
const halfUp = (v, dec) => Math.floor(Math.abs(v) * 10 ** dec + 0.5);
export const group = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

/** 4.65 -> "4.7": a plain number with dec decimals, half up. */
export function fixed(v, dec = 1) {
  const n = halfUp(v, dec), f = 10 ** dec;
  return (v < 0 && n ? "-" : "") + Math.floor(n / f) + (dec ? "." + String(n % f).padStart(dec, "0") : "");
}

/** 2 -> "2", 2.5 -> "2.5". */
export const pct = (v) => fixed(v, 1).replace(/\.0$/, "");

/** Symbol + en-GB grouping: €1,049 (headline) or €1,049.00 (dec, receipt lines); "−" for a negative; "–" for none. */
export function money(v, cur, dec = false) {
  if (v === null || v === undefined) return "–";
  const d = dec ? 2 : 0, f = 10 ** d, n = halfUp(v, d);
  return (v < 0 && n ? "−" : "") + SYMBOL[cur] + group(Math.floor(n / f)) + (dec ? "." + String(n % f).padStart(2, "0") : "");
}

const rom = (gb) => (+gb >= 1024 && +gb % 1024 === 0 ? `${+gb / 1024} TB` : `${gb} GB`);
/** '12/256' -> ['12 GB', '256 GB']; null for "base" (the store doesn't list RAM/storage). */
export function memParts(st) {
  const p = (st || "").split("/");
  return p.length === 2 ? [`${esc(p[0])} GB`, rom(esc(p[1]))] : null;
}
const NOMEM = "RAM/storage not listed";
export const memLabel = (st) => { const p = memParts(st); return p ? `${p[0]} · ${p[1]}` : NOMEM; };
export const memText = (st) => { const p = memParts(st); return p ? `${p[0]} RAM · ${p[1]} storage` : NOMEM; };
export const memShort = (st) => { const p = memParts(st); return p ? `${p[0]} + ${p[1]}` : NOMEM; };
/** '12/256' -> '12 + 256', '16/1024' -> '16 + 1 TB' (home gap line). */
export function memTiny(st) {
  const p = (st || "").split("/");
  return p.length === 2 ? `${esc(p[0])} + ` + (+p[1] >= 1024 ? rom(p[1]) : esc(p[1])) : NOMEM;
}
const memKey = (st) => st.split("/").map(Number);
const memCmp = (a, b) => (memKey(a)[1] - memKey(b)[1]) || (memKey(a)[0] - memKey(b)[0]);

const ts = (iso) => new Date(iso);
/** '2026-10-30T14:05:00Z' -> '30 Oct, 14:05 UTC'. */
export function stamp(iso) {
  if (!iso) return "";
  const d = ts(iso);
  return `${d.getUTCDate()} ${MON[d.getUTCMonth()]}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")} UTC`;
}
/** Whole days between the store's last check and now (both ISO, UTC). */
export const daysAgo = (iso, now) => (!iso || !now ? null : Math.floor((ts(now) - ts(iso)) / 864e5));
/** '2026-10-02' -> 'Oct 2026'. */
export function month(iso) {
  if (!iso) return "";
  const [y, m] = iso.slice(0, 7).split("-");
  return `${MON[+m - 1]} ${y}`;
}
/** [5, 9] -> '5–9 days'. */
export const daysText = (d) => (!d || !d.length ? "delivery time not stated" : d[0] === d[1] ? `${d[0]} days` : `${d[0]}–${d[1]} days`);
const cap = (t) => t.slice(0, 1).toUpperCase() + t.slice(1);

/** What a store row's total leaves out or includes, in words. */
export function caveat(r, s) {
  const x = [];
  if (r.ship === null) x.push("shipping not listed");
  else if (r.shipMin) x.push("shipping from " + money(r.ship, s.cur));
  if (r.adj === null) x.push(PAY_BY[s.pay] + " fee unknown");
  if (r.duties === true) x.push(r.taxName + " paid by store");
  else if (r.taxEst === null) x.push(r.taxName + " not estimated");
  else if (r.duties === false) x.push("incl. ≈" + money(r.taxAdded, s.cur) + " " + r.taxName);
  else x.push(r.taxName + " not stated, may add ≈" + money(r.taxEst, s.cur));
  return x.join(" · ");
}

// the verdict's "why this one": [bold lead, rest]
function why(best, pick, s) {
  const ok = pick.filter((r) => r.state === "ok");
  const cheaper = ok.filter((r) => r.total < best.total).sort((a, b) => a.total - b.total);
  if (cheaper.length) {
    const c = cheaper[0];
    const gaps = [["shipping", c.ship === null], ["import tax", c.unknown % 2 === 1]].filter(([, o]) => o).map(([g]) => g).join(" or ");
    return ["Why this one:", `the lowest total where shipping and import tax are settled. ${c.store} lists ${money(c.total, s.cur)} but doesn't say what ${gaps} will add.`];
  }
  if (ok.length > 1) return ["Why this one:", `the lowest total of ${ok.length} stores for this version and memory.`];
  return ["Only one store", "we check sells this version and memory."];
}

/** The edition's memories (no "base"), smallest first, each with its best current payable row (or null). */
export function memOptions(rows, edition) {
  const sts = [...new Set(rows.filter((r) => r.edition === edition && r.storage !== "base" && ["ok", "nopay", "stale"].includes(r.state)).map((r) => r.storage))];
  return sts.sort(memCmp).map((st) => [st, bestOf(rows, edition, st)]);
}

const go = (r, cls) => `<a class="${cls}" href="${esc(r.link)}" ${LINK}>View at ${esc(r.store)}<span aria-hidden="true"> ↗</span></a>`;
const total = (r, s) => (r.approx ? "≈" : "") + money(r.total, s.cur) + (r.tail ? `<small>${esc(r.tail)}</small>` : "");
const memDiv = (st) => { const p = memParts(st); return `<div class="mem">${p ? `<b>${p[0]}</b> RAM · <b>${p[1]}</b> storage` : NOMEM}</div>`; };
const edCls = (e) => (e === "china" ? "cn" : "gl");

/** One version's best current price: version, memory, price, store, settled mark or what is left out, store link. */
export function priceBox(rows, edition, s, labels, on = false) {
  const b = bestOf(rows, edition), other = bestOf(rows, edition === "china" ? "global" : "china"), cls = edCls(edition);
  const lab = `<div class="lab">${esc(labels[edition])} version</div>`;
  if (!b) return `<div class="side ${cls} none" data-block="price_box" data-e="${edition}">${lab}<div class="big num">–</div><p class="st">No current price for your settings</p></div>`;
  return `<div class="side ${cls}${on && other ? " on" : ""}" data-block="price_box" data-e="${edition}"><button type="button" class="pickbtn" data-e="${edition}" aria-pressed="${on ? "true" : "false"}">` +
    lab + memDiv(b.storage) + `<div class="big num">${b.approx ? "≈" : ""}${money(b.total, s.cur)}</div><p class="st">at <b>${esc(b.store)}</b></p>` +
    (b.settled ? '<span class="ok">✓ delivered, tax settled</span>' : `<span class="unk">${esc(cap(b.left))} not included</span>`) + "</button>" +
    (edition === "china" ? '<a class="means-link" href="#means-h">Chinese software, Google Play off at first</a>' : "") + go(b, "go") +
    (other ? `<button type="button" class="pick" data-e="${edition}">${on ? "Details below ↓" : "Show this version ↓"}</button>` : "") + "</div>";
}

/** Under the two boxes: the same-memory gap (view.gap), or why there is no number. "" when only one version sells. */
export function gapLine(g, both, s, labels) {
  if (!both) return "";
  if (!g) return '<div class="gapline slim" data-block="gap_line">No memory has a settled delivered price for both versions yet, so we don\'t put a number on the gap.</div>';
  const cheap = g.diff >= 0 ? labels.china : labels.global;
  return `<div class="gapline slim" data-block="gap_line">Same memory, <b>${memLabel(g.storage)}</b>: the ${esc(cheap)} version is <b>${money(Math.abs(g.diff), s.cur)} less</b> delivered (${money(g.china, s.cur)} vs ${money(g.global, s.cur)}).</div>`;
}

/** One chip per memory of the edition with its best current price ("+" when something is left out); "–" chips are disabled. */
export function memChips(rows, edition, storage, s) {
  return '<div class="mems" data-block="mem_chips" role="group" aria-label="Memory">' + memOptions(rows, edition).map(([st, b]) =>
    `<button type="button" data-m="${esc(st)}" aria-pressed="${st === storage ? "true" : "false"}"${b ? "" : " disabled"}>${memLabel(st)} · ${b ? money(b.total, s.cur) + (b.unknown ? "+" : "") : "–"}</button>`).join("") + "</div>";
}

/** The pick for this version and memory: row = bestOf(rows, edition, storage); pick = every row of that version and memory. */
export function verdict(row, pick, s, labels, now = null) {
  const open = '<section class="verdict" data-block="verdict" aria-live="polite">';
  if (!row || row.state !== "ok") return open + '<p class="q">No store we check has a current price for this version and memory.</p></section>';
  const t = row.trust || {}, rv = t.reviews, w = why(row, pick, s);
  return open + `<div class="what"><span class="vpill ${edCls(row.edition)}">${esc(labels[row.edition])} version</span><span class="mpill">${memText(row.storage)}</span></div>` +
    `<p class="q">${row.settled ? "Cheapest delivered" : "Lowest total we can work out"}</p><div class="total num">${total(row, s)}</div>` +
    `<p class="who">at <b>${esc(row.store)}</b> · ${row.days ? "arrives in " + daysText(row.days) : "delivery time not stated"}</p>` +
    `<p class="why"><b>${esc(w[0])}</b> ${esc(w[1])}</p><ul class="badges">` +
    (row.promoAmt > 0.005 ? `<li class="sale">${pct(row.promoPct)}% ${esc((row.promoLabel || "sale").toLowerCase())} applied</li>` : "") +
    (rv ? `<li>★ ${fixed(rv.score, 1)} on ${esc(rv.source)} (${group(rv.count)})</li>` : "") +
    (row.duties === true ? `<li>${esc(cap(row.taxName))} paid by store</li>` : "") +
    `<li>${t.warranty_months ? esc(t.warranty_months) + "-month store warranty" : "Warranty not stated"}</li>` +
    (t.returns_days ? `<li>${esc(t.returns_days)}-day returns</li>` : "") + "</ul>" + go(row, "cta") +
    `<p class="fine">${row.checked ? `Price checked ${stamp(row.checked)}. ` : ""}Affiliate link: we may earn a commission; it never changes the order.</p></section>`;
}

const seg = (v, c) => (v > 0 ? `<span style="flex:${fixed(v, 1)};background:var(${c})"></span>` : "");
const dt = (c, label) => `<dt><i style="background:var(${c})"></i>${label}</dt>`;

/** How the total adds up: cost bar, store price, sale, payment, shipping, import tax, "You pay at the door". */
export function receipt(row, s, labels) {
  const open = '<section class="receipt" data-block="receipt" aria-label="How the total adds up">';
  if (!row || row.state !== "ok") return open + "</section>";   // never a stale, sold-out, undelivered or unpayable row
  const fee = row.adjAmt > 0 ? row.adjAmt : 0, d = (v) => money(v, s.cur, true);
  const tax = row.duties === true ? "paid by the store" : row.taxEst === null ? "not estimated" : row.duties === false ? "≈" + d(row.taxAdded) : `not stated (≈${money(row.taxEst, s.cur)} if due)`;
  return open + `<h3>How ${money(row.total, s.cur)} adds up</h3><div class="costbar" aria-hidden="true">` +
    seg(row.base, "--bar-phone") + seg(fee, "--bar-fee") + seg(row.ship || 0, "--bar-ship") + seg(row.taxAdded, "--bar-tax") + "</div><dl>" +
    dt("--bar-phone", "Store price") + `<dd>${d(row.list)}</dd>` +
    (row.promoAmt > 0.005 ? dt("--bar-promo", `${esc(row.promoLabel || "Sale")}, ${pct(row.promoPct)}% off at checkout`) + `<dd class="neg">−${d(row.promoAmt)}</dd>` : "") +
    dt("--bar-fee", "Paying by " + PAY_BY[s.pay]) + `<dd>${row.adj === null ? "unknown" : row.adjAmt ? d(row.adjAmt) : "no fee"}</dd>` +
    dt("--bar-ship", "Shipping to " + PLACE[s.region]) + `<dd>${row.ship === null ? "not listed" : row.ship === 0 ? "free" : (row.shipMin ? "from " : "") + d(row.ship)}</dd>` +
    dt("--bar-tax", esc(cap(row.taxName))) + `<dd>${tax}</dd>` +
    `<dt class="sum">You pay at the door</dt><dd class="sum">${row.approx ? "≈" : ""}${d(row.total)}${row.tail ? `<small>${esc(row.tail)}</small>` : ""}</dd></dl></section>`;
}

/** One store in a list, by its state: ok, nopay, stale, nodelivery (no price), soldout (no store link). now: ISO, UTC. */
export function storeRow(row, s, labels, now = null) {
  const st = row.state;
  let c;
  if (st === "nodelivery") c = "Doesn't deliver to " + PLACE[s.region];
  else if (st === "soldout") c = "Sold out";
  else if (st === "stale") { const n = daysAgo(row.checked, now); c = n !== null ? `price from ${n}${n === 1 ? " day ago" : " days ago"}` : "price from an earlier check"; }
  else if (st === "nopay") c = "Doesn't take " + PAY_BY[s.pay];
  else c = esc(daysText(row.days) + " · " + caveat(row, s)) + (row.trust && row.trust.reviews ? " · ★ " + fixed(row.trust.reviews.score, 1) : "");
  return `<li${st !== "ok" ? ` class="${st}"` : ""} data-block="store_row" data-state="${st}"><span class="s">${esc(row.store)}` +
    (row.promoAmt > 0.005 && st !== "nodelivery" ? `<span class="promo">${pct(row.promoPct)}% sale</span>` : "") + "</span>" +
    (st !== "nodelivery" ? `<span class="t num">${st === "soldout" ? money(row.total, s.cur) : total(row, s)}</span>` : "") +
    `<span class="c">${c}</span>` + (["ok", "nopay", "stale"].includes(st) ? go(row, "g") : "") + "</li>";
}

/** Stores for one version and memory, in view.rows order; the sold-out ones apart under "Sold out at". */
export function storeList(rows, s, labels, now = null) {
  const main = rows.filter((r) => r.state !== "soldout"), sold = rows.filter((r) => r.state === "soldout"), li = (rs) => rs.map((r) => storeRow(r, s, labels, now)).join("");
  return '<div class="stores" data-block="store_list">' + (main.length ? `<ul class="offers">${li(main)}</ul>` : "") +
    (sold.length ? `<h3 class="soldout-h">Sold out at</h3><ul class="offers soldout-list">${li(sold)}</ul>` : "") + "</div>";
}

/** Pinned at the bottom once the price boxes scroll away; the page shows and hides it. "" without a row. */
export function buyBar(row, s, labels) {
  if (!row || row.state !== "ok") return "";   // never a stale, sold-out, undelivered or unpayable row
  return `<div class="buybar" data-block="buy_bar" hidden><div class="bb-t"><span class="bb-l1"><b class="num">${row.approx ? "≈" : ""}${money(row.total, s.cur)}</b>` +
    `<b class="bb-w">${esc(labels[row.edition])} · ${memShort(row.storage)}</b></span><span>${row.tail ? esc(row.tail) + " · " : ""}${esc(row.store)}</span></div>` +
    `<a class="bb-go" href="${esc(row.link)}" ${LINK} aria-label="View deal at ${esc(row.store)}">View deal<span aria-hidden="true"> ↗</span></a></div>`;
}

const cell = (b, e, s, labels) => (b
  ? `<span class="p ${edCls(e)}">${esc(labels[e])}<b class="num">${b.approx ? "≈" : ""}${money(b.total, s.cur)}${b.tail ? `<small>${esc(b.tail)}</small>` : ""}</b>${memLabel(b.storage)}</span>`
  : `<span class="p none">${esc(labels[e])}<b>–</b></span>`);

/** A phone on the home list: name, launch month, China (red) and Global (blue) best current price, the gap. */
export function homeRow(phone, rows, s, labels, root = "", marks = []) {
  const g = gap(rows), n = new Set(rows.filter((r) => r.state === "ok").map((r) => r.store)).size;
  return `<li class="pair" data-block="home_row" data-id="${esc(phone.id)}"><a href="${esc(root)}phones/${esc(phone.id)}"><span class="nm">${esc(phone.name)}<small>${month(phone.announced)}</small></span>` +
    `<span class="two">${cell(bestOf(rows, "china"), "china", s, labels)}${cell(bestOf(rows, "global"), "global", s, labels)}</span>` +
    (g ? `<span class="gap">${esc(g.diff >= 0 ? labels.china : labels.global)} ${money(Math.abs(g.diff), s.cur)} less at ${memTiny(g.storage)}</span>` : "") +
    `<span class="meta">${n} ${n === 1 ? "store" : "stores"}</span></a>` +
    (marks.length ? `<span class="marks">${marks.map((m) => `<span class="mark ${esc(m.kind)}">${esc(m.text)}</span>`).join("")}</span>` : "") + "</li>";
}

/** Priced rows (ok, nopay, stale) as [rank, row] in view.rows order, then sorted by "total" or "list" (stable). */
export function ledgerRows(rows, sort = "rank") {
  const lr = rows.filter((r) => ["ok", "nopay", "stale"].includes(r.state)).map((r, i) => [i + 1, r]);
  return sort === "total" || sort === "list" ? lr.sort((a, b) => a[1][sort] - b[1][sort]) : lr;
}

/** Every priced offer with the parts of its total as columns and its rank; sort: rank | total | list. "" when none. */
export function ledger(rows, s, labels, sort = "rank") {
  const lr = ledgerRows(rows, sort);
  if (!lr.length) return "";
  const d = (v) => money(v, s.cur, true);
  const th = (key, label) => `<th scope="col"${sort === key ? ' aria-sort="ascending"' : ""}><button type="button" data-s="${key}">${label}</button></th>`;
  const td = (v, cls = "") => `<td${cls ? ` class="${cls}"` : ""}>${v}</td>`;
  return '<table class="lt" data-block="ledger"><thead><tr><th scope="col">Store · version · memory</th>' + th("list", "Store price") +
    `<th scope="col">Sale</th><th scope="col">${esc(cap(PAY_BY[s.pay]))}</th><th scope="col">Shipping</th><th scope="col">${esc(cap(lr[0][1].taxName))}</th>` +
    th("total", "Total") + th("rank", "Rank") + "</tr></thead><tbody>" + lr.map(([n, r]) =>
      `<tr${r.state !== "ok" ? ` class="${r.state}"` : ""}><td>${esc(r.store)} · ${esc(labels[r.edition])} · ${memLabel(r.storage)}` +
      (r.state === "stale" ? " <small>older price</small>" : r.state === "nopay" ? ` <small>doesn't take ${PAY_BY[s.pay]}</small>` : "") + "</td>" +
      td(d(r.list)) + (r.promoAmt > 0.005 ? td("−" + d(r.promoAmt), "p") : td("–")) +
      (r.adj === null ? td("?", "q") : td(r.adjAmt ? d(r.adjAmt) : "no fee")) +
      (r.ship === null ? td("not listed", "q") : td(r.ship === 0 ? "free" : (r.shipMin ? "from " : "") + d(r.ship))) +
      (r.duties === true ? td("store pays") : r.taxEst === null ? td("not estimated") : r.duties === false ? td("+" + d(r.taxAdded)) : td("not stated", "q")) +
      td((r.approx ? "≈" : "") + d(r.total) + (r.unknown ? "+" : ""), "tot") + td(n) + "</tr>").join("") + "</tbody></table>";
}
