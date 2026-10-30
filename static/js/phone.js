// The phone page (spec §5.2, templates/phone.html). The server renders every price block for the default settings; this
// module re-renders them with blocks.js when the visitor's settings differ (or when they pick another memory or
// version), from the phone's v1 data file and the tax file, and wires the page: memory chips, version boxes, delivery
// filters with counts, the ledger sort, the buy bar, Watch and Share. No markup of its own beyond blocks.js output.
// The pure helpers are exported for tests/js/phone_cases.mjs; everything touching the page is guarded.
import { rows as viewRows, bestOf, defaultPick, pickForMemory } from "./view.js";
import * as B from "./blocks.js";
import { wireShare } from "./share.js";
import { load, isDefault, watched, toggleWatch, PLACE } from "./settings.js";

/** The pick a shared link ("#16-512-china") opens: its memory for both boxes, on its version when that has a current price
 *  there, else the other version, else the default pick (view.js pickForMemory); null when the hash isn't a pick. */
export function pickFromHash(rows, hash) {
  const h = parseHash(hash);
  return h ? pickForMemory(rows, h.mem, h.ed) : null;
}

/** "Other stores" delivery filters (pages/phone.py FILTERS: the same three tests). */
export const FILTERS = { tax: (r) => r.duties === true, ship: (r) => r.ship === 0, fast: (r) => !!(r.days && r.days[1] <= 10) };

/** Approved buyer reports for a store and region (pages/phone.py buyers_text: the same). */
export function buyersText(b, region) {
  const x = (b || {})[region];
  if (!x || !x.n) return "";
  const out = [];
  if (x.nd) out.push((x.dmin === x.dmax ? `${x.dmin}` : `${x.dmin}–${x.dmax}`) + " days" + (x.nd > 2 ? ` (typically ${x.dmed})` : ""));
  if (x.tk) out.push(`${x.tx} of ${x.tk} paid import tax`);
  return out.length ? `${x.n} ${x.n === 1 ? "buyer" : "buyers"} to ${PLACE[region]}: ${out.join(" · ")}` : "";
}

/** The shareable pick, as the live site wrote it: "#16-512-china" (RAM-storage-version); "" when the memory isn't listed. */
export function pickHash(ed, mem) {
  const m = /^(\d+)\/(\d+)$/.exec(mem || "");
  return m && (ed === "global" || ed === "china") ? `#${m[1]}-${m[2]}-${ed}` : "";
}

/** "#16-512-china" -> {ed: "china", mem: "16/512"}; null for anything else. */
export function parseHash(hash) {
  const m = /^#(\d+)-(\d+)-(global|china)$/.exec(hash || "");
  return m ? { ed: m[3], mem: `${m[1]}/${m[2]}` } : null;
}

/** A selector for the same control after a repaint: its container's id, its first class and its data-e / data-m /
 *  data-s / data-f value ("#duel button.near[data-m=\"12/256\"]"); null for anything else. */
export function focusSelector(el) {
  if (!el || !el.getAttribute || el.tagName !== "BUTTON") return null;
  const attr = ["data-e", "data-m", "data-s", "data-f"].find((a) => el.hasAttribute(a));
  const box = attr && el.parentElement && el.parentElement.closest("[id]");   // not the button itself: a tab has an id of its own
  if (!box) return null;
  const cls = el.classList && el.classList[0];
  return `#${box.id} button${cls ? "." + cls : ""}[${attr}="${String(el.getAttribute(attr)).replace(/["\\]/g, "\\$&")}"]`;
}

const getJson = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); });
const json = (v, d) => { try { return v ? JSON.parse(v) : d; } catch (e) { return d; } };

function wire(root) {
  const $ = (id) => document.getElementById(id);
  const L = json(root.dataset.labels, { global: "Global", china: "China" }), now = root.dataset.now || null, id = root.dataset.id;
  const eds = (root.dataset.eds || "").split(",").filter(Boolean), buyers = json(root.dataset.buyers, {});
  const S = { ed: root.dataset.ed || null, mem: root.dataset.mem || null, f: {}, sort: "rank", touched: false };
  let docs = null;   // the [phone file, tax file] promise
  // a failed load is forgotten, so the next tap tries again
  const loadDocs = () => docs || (docs = Promise.all([getJson(root.dataset.file), getJson(root.dataset.tax)]).catch((e) => { docs = null; throw e; }));
  const set = (el, h) => { if (el) el.innerHTML = h; };

  // ---- buy bar: pinned once the price boxes have scrolled away, hidden while the details panel's own button shows ----
  const seen = { duel: true, cta: false };
  let ctaObs = null;
  const bb = () => { const bar = document.querySelector("#s-buybar .buybar"); if (bar) bar.hidden = seen.duel || seen.cta; };
  const watchCta = () => {
    if (!ctaObs) return;
    ctaObs.disconnect(); seen.cta = false;
    const c = document.querySelector("#pick-panel .cta");
    if (c) ctaObs.observe(c);
    bb();
  };
  if ("IntersectionObserver" in window && $("duel")) {
    new IntersectionObserver((es) => { es.forEach((x) => { seen.duel = x.isIntersecting || x.boundingClientRect.top > 0; }); bb(); }).observe($("duel"));
    ctaObs = new IntersectionObserver((es) => { es.forEach((x) => { seen.cta = x.isIntersecting; }); bb(); });
    watchCta();
  }

  // ---- paint every settings-dependent block from rows ----
  function paint(rows, s) {
    if (!$("duel")) return;
    const a = document.activeElement, again = a && root.contains(a) ? focusSelector(a) : null;   // keyboard focus survives the repaint
    set($("s-mems"), B.memChips(rows, S.mem, s));
    set($("duel"), eds.map((e) => B.priceBox(rows, e, S.mem, s, L, e === S.ed)).join(""));   // each box's tab button repaints with aria-selected
    const best = bestOf(rows, S.ed, S.mem), pick = rows.filter((r) => r.edition === S.ed && r.storage === S.mem);
    set($("s-verdict"), B.verdict(best, pick, s, L, now));
    set($("s-receipt"), B.receipt(best, s, L));
    const bl = $("buyers"), bt = best ? buyersText(buyers[best.store], s.region) : "";
    if (bl) { bl.textContent = bt; bl.hidden = !bt; }
    const rest = pick.filter((r) => r !== best), cand = rest.filter((r) => r.state !== "soldout" && r.state !== "nodelivery");
    $("others-h").textContent = rest.length ? `Other stores for ${L[S.ed]} · ${B.memLabel(S.mem)}` : "No other store sells this version and memory";
    const df = $("dfilt");
    df.hidden = !rest.length;
    df.querySelectorAll("button[data-f]").forEach((b) => {
      const k = b.dataset.f, n = cand.filter(FILTERS[k]).length;
      b.querySelector("span").textContent = n;
      b.disabled = !n && !S.f[k];
      b.setAttribute("aria-pressed", S.f[k] ? "true" : "false");
    });
    const on = Object.keys(FILTERS).filter((k) => S.f[k]);
    const shown = on.length ? cand.filter((r) => on.every((k) => FILTERS[k](r))) : rest;
    set($("s-stores"), B.storeList(shown, s, L, now));
    $("nomatch").hidden = !(on.length && !shown.length);
    set($("s-ledger"), B.ledger(rows, s, L, S.sort));
    if ($("n-ledger")) $("n-ledger").textContent = B.ledgerRows(rows).length;
    $("hist").querySelectorAll(":scope > [data-e]").forEach((d) => { d.hidden = d.dataset.e !== S.ed; });
    set($("s-buybar"), B.buyBar(best, s, L));
    watchCta();
    const back = again && document.querySelector(again);
    if (back && back !== document.activeElement && !back.disabled) back.focus({ preventScroll: true });
  }

  // ---- "More from <brand>": each phone's own file, only when the settings differ from the defaults ----
  let moreFor = "";
  function paintMore(s, tax) {
    const ul = $("more"), metas = ul ? json(ul.dataset.more, []) : [], key = JSON.stringify(s);
    if (!metas.length || moreFor === key) return;
    moreFor = key;
    Promise.all(metas.map((m) => getJson(m.file))).then((files) => {
      if (moreFor !== key) return;
      ul.innerHTML = metas.map((m, i) => B.homeRow(m, viewRows(files[i].offers, tax, s), s, L, "../")).join("");
    }).catch(() => {});
  }

  // the current settings' rows (loading the files the first time), then paint
  // fresh: the settings changed, so the pick is the default (until the visitor picks) or is re-checked against the new rows
  // pickOf(rows): the visitor's tap (or a shared link) -> the new {ed, mem}, applied as it is: a tap on a box whose version
  //   isn't sold with the memory keeps it, that box says so
  // remember: also put the pick in the address ("#16-512-china"), as the live site did, without a history entry
  function update(fresh = false, remember = false, pickOf = null) {
    const s = load();
    return loadDocs().then(([doc, tax]) => {
      const rows = viewRows(doc.offers, tax, s);
      if (pickOf) Object.assign(S, pickOf(rows));
      else if (fresh && !S.touched) Object.assign(S, defaultPick(rows));
      else if (fresh && S.mem) Object.assign(S, pickForMemory(rows, S.mem, S.ed));   // the memory may have no current price now
      paint(rows, s);
      if (remember && history.replaceState) history.replaceState(null, "", location.pathname + location.search + pickHash(S.ed, S.mem));
      if (!isDefault(s) || moreFor) paintMore(s, tax);
    }, () => {})   // offline or a missing file: the server's default-settings prices stay
      .catch((e) => console.error(e));   // a bug while painting: say so in the console
  }

  root.addEventListener("pointerdown", () => { if (root.dataset.file) loadDocs().catch(() => {}); }, { once: true });   // warm up before the tap lands
  root.addEventListener("click", (ev) => {
    const t = ev.target;
    const tab = t.closest("#duel button.pickbtn"), near = t.closest("#duel button.near"), mem = t.closest("#s-mems button[data-m]");
    const f = t.closest("#dfilt button[data-f]"), sort = t.closest("#s-ledger button[data-s]");
    const pickMem = (m, ed) => { S.touched = true; S.f = {}; update(false, true, (rows) => pickForMemory(rows, m, ed)); };
    if (tab) { S.touched = true; S.f = {}; const ed = tab.dataset.e; update(false, true, () => ({ ed, mem: S.mem })); }
    else if (near) pickMem(near.dataset.m, near.closest(".side").dataset.e);
    else if (mem && !mem.disabled) pickMem(mem.dataset.m, S.ed);
    else if (f && !f.disabled) { S.f[f.dataset.f] = !S.f[f.dataset.f]; update(); }
    else if (sort) { S.sort = sort.dataset.s; update(); }
  });
  const again = () => update(true);
  window.addEventListener("dp:settings", again);
  window.addEventListener("storage", (e) => { if (!e.key || (e.key.startsWith("pc-") && e.key !== "pc-watch")) again(); });
  // a shared link's pick ("#16-512-china"), else other settings than the defaults: paint once the files are in
  const shared = parseHash(location.hash);
  if (shared && root.dataset.file) {
    S.touched = true;
    update(false, false, (rows) => { const p = pickFromHash(rows, location.hash); return p && eds.includes(p.ed) ? p : {}; });
  } else if (!isDefault(load()) && root.dataset.file) again();

  // ---- the buyer report form posts natively; the endpoint sends the visitor back here with #report-thanks or #report-error ----
  const rs = $("rf-status");
  if (rs && (location.hash === "#report-thanks" || location.hash === "#report-error")) {
    const ok = location.hash === "#report-thanks";
    rs.closest("details").open = true;
    rs.className = "rf-status " + (ok ? "ok" : "err");
    rs.textContent = ok ? "Thanks! We check each report before it counts." : "Please check the store, country and days, then send again.";
  }

  // ---- Watch (this device's list) and Share (the device's share sheet, else copy the link) ----
  const wb = root.querySelector(".watch"), note = root.querySelector(".watch-note");
  const showWatch = () => {
    const on = watched().has(id);
    wb.setAttribute("aria-pressed", on ? "true" : "false");
    wb.textContent = on ? "Watching" : "Watch";
    if (note) note.hidden = !on;
  };
  if (wb) { wb.hidden = false; showWatch(); wb.addEventListener("click", () => { toggleWatch(id); showWatch(); }); }
  wireShare(root.querySelector(".share"), () => pickHash(S.ed, S.mem));   // the pick on screen
}

if (typeof document !== "undefined") {
  const start = () => { const root = document.getElementById("phone"); if (root) wire(root); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
}
