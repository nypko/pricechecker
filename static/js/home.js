// The home page (spec §5.1, templates/index.html). The server renders every phone's row for the default settings and
// embeds a summary per phone (versions with a price, lowest total, China saving, storage sizes); this module filters,
// sorts and searches those, and re-renders the rows with blocks.js from the region's home files when the visitor's
// settings differ from the defaults or a storage size is picked. No markup of its own beyond blocks.js output.
// The pure helpers are exported for tests/js/home_cases.mjs; everything touching the page is guarded.
import { rows as viewRows, bestOf, gap } from "./view.js";
import * as B from "./blocks.js";
import { load, isDefault, watched } from "./settings.js";

const FIRST = 20;
const romOf = (st) => { const m = /^\d+\/(\d+)$/.exec(st || ""); return m ? +m[1] : null; };
const round2 = (v) => Math.round(v * 100) / 100;

/** Rows sold with the storage size `rom` (GB; 0 or "" for any). */
export const narrow = (rows, rom) => (rom ? rows.filter((r) => romOf(r.storage) === +rom) : rows);

/** What the chips, sorts and storage list need from a phone's rows (pricechecker/site/pages/home.py summary(): the same
 *  keys, only those that apply): china / global = 1 when that version has a current price, cheap = lowest current total,
 *  gap = the settled China saving, roms = every storage size the phone is sold with (not narrowed). */
export function summarize(rows, rom = 0) {
  const n = narrow(rows, rom), out = {};
  if (bestOf(n, "china")) out.china = 1;
  if (bestOf(n, "global")) out.global = 1;
  const ok = n.filter((r) => r.state === "ok");
  if (ok.length) out.cheap = round2(Math.min(...ok.map((r) => r.total)));
  const g = gap(n);
  if (g) out.gap = round2(g.diff);
  const roms = [...new Set(rows.map((r) => romOf(r.storage)).filter(Boolean))].sort((a, b) => a - b);
  if (roms.length) out.roms = roms;
  return out;
}

/** Offers from home files -> Map(phone id -> view rows) for the settings. */
export function groupRows(offers, tax, s) {
  const by = new Map();
  for (const o of offers) { if (!by.has(o.id)) by.set(o.id, []); by.get(o.id).push(o); }
  return new Map([...by].map(([id, list]) => [id, viewRows(list, tax, s)]));
}

const tokens = (str) => String(str || "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);

/** Search: every word of the query is a whole word of the brand or name, in any order; the last word, once it is 3+
 *  letters, may be the start of one (so typing "x9 ult" already finds the Ultra, but "x9" doesn't find the X90). */
export function matches(p, q) {
  const w = tokens(q);
  if (!w.length) return true;
  const hay = tokens(`${p.brand} ${p.name}`);
  return w.every((x, i) => hay.some((t) => t === x || (i === w.length - 1 && x.length >= 3 && t.startsWith(x))));
}

/** The ids that stay on the list, in the order given. phones: {id, name, brand, announced, s: summary}.
 *  chip: all | both | china | global | watched; brand: lower case or ""; storage: GB or ""; watched: Set of ids. */
export function filterRows(phones, { chip = "all", brand = "", storage = "", q = "", watched: w = new Set() } = {}) {
  return phones.filter((p) => {
    const s = p.s || {};
    if (brand && String(p.brand).toLowerCase() !== brand) return false;
    if (chip === "both" && !(s.china && s.global)) return false;
    if (chip === "china" && !s.china) return false;
    if (chip === "global" && !s.global) return false;
    if (chip === "watched" && !w.has(p.id)) return false;
    if (storage && !(s.roms || []).includes(+storage)) return false;
    return matches(p, q);
  }).map((p) => p.id);
}

/** All ids in the sort's order. new: announced, newest first; save: the biggest settled China saving first, phones
 *  without one last; cheap: the lowest current total (any version) first, unpriced last; drop: phones with a listing
 *  drop this week first, the biggest drop first. The rest keep newest-first order. */
export function sortRows(phones, sort) {
  const base = phones.map((p, i) => [p, i]).sort(([a, i], [b, j]) => String(b.announced || "").localeCompare(String(a.announced || "")) || i - j).map(([p]) => p);
  const key = { save: (p) => (p.s || {}).gap, cheap: (p) => (p.s || {}).cheap, drop: (p) => p.drop || undefined }[sort];
  if (!key) return base.map((p) => p.id);
  const has = base.filter((p) => key(p) !== undefined && key(p) !== null), rest = base.filter((p) => !has.includes(p));
  const dir = sort === "cheap" ? 1 : -1;
  has.sort((a, b) => dir * (key(a) - key(b)));   // stable: ties keep newest-first order
  return [...has, ...rest].map((p) => p.id);
}

/** The phones' rows as HTML. phone: {id, name, announced, l?: the China version's label, rows}. */
export function listHtml(phones, s, root = "") {
  return phones.map((p) => B.homeRow(p, p.rows || [], s, { china: p.l || "China", global: "Global" }, root)).join("");
}

const getJson = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); });
const json = (v, d) => { try { return v ? JSON.parse(v) : d; } catch (e) { return d; } };

function wire(root) {
  const $ = (id) => document.getElementById(id);
  const files = json(root.dataset.files, {}), list = $("list"), q = $("q");
  const phones = json($("home-meta").textContent, []);
  const stock = new Map(phones.map((p) => [p.id, p.s || {}]));   // the server's default-settings summaries
  const dflt = new Map([...list.children].map((li) => [li.dataset.id, li]));   // and its rows
  let els = dflt, seq = 0, note = "";
  const S = { chip: "all", brand: "", sort: "new", rom: "", q: "", all: false };

  // ---- the region's home parts (all of them, in parallel) and the tax file; a failed load is forgotten so the next try fetches again ----
  const docs = new Map();
  const loadRegion = (region) => {
    if (!docs.has(region)) {
      docs.set(region, Promise.all([Promise.all((files[region] || []).map(getJson)), getJson(root.dataset.tax)])
        .then(([parts, tax]) => ({ offers: parts.flatMap((d) => d.offers), tax }))
        .catch((e) => { docs.delete(region); throw e; }));
    }
    return docs.get(region);
  };

  // ---- paint ----
  function paintChips() {
    const n = watched().size;
    const wc = root.querySelector('#chips [data-f="watched"]');
    if (wc) { wc.hidden = !n; wc.querySelector(".n").textContent = n; }
    if (S.chip === "watched" && !n) S.chip = "all";
    root.querySelectorAll("#chips button").forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.b ? S.brand === b.dataset.b : S.chip === b.dataset.f && (b.dataset.f !== "all" || !S.brand)));
    });
    root.querySelectorAll("#sorts button").forEach((b) => b.setAttribute("aria-pressed", String(S.sort === b.dataset.s)));
  }
  function render() {
    paintChips();
    const order = sortRows(phones, S.sort);
    const keep = new Set(filterRows(phones, { chip: S.chip, brand: S.brand, storage: S.rom, q: S.q, watched: watched() }));
    const ids = order.filter((id) => keep.has(id));
    const vis = S.all || S.q ? ids : ids.slice(0, FIRST);
    list.removeAttribute("data-cap");
    list.replaceChildren(...vis.map((id) => els.get(id)).filter(Boolean));
    $("count").textContent = note || (ids.length ? `${ids.length} ${ids.length === 1 ? "phone" : "phones"} · lowest delivered price per version` : "");
    const sa = $("showall");
    sa.hidden = vis.length >= ids.length;
    sa.textContent = `Show all ${ids.length} phones`;
    const nr = $("no-results");
    nr.hidden = ids.length > 0;
    nr.querySelector(".nr-q").textContent = S.q.trim();
    list.hidden = !ids.length;
  }

  // ---- settings or storage changed: the default rows and summaries, or re-priced from the region's files ----
  function apply() {
    const s = load(), token = ++seq;
    if (isDefault(s) && !S.rom) {
      els = dflt; phones.forEach((p) => { p.s = stock.get(p.id); }); note = ""; render();
      return Promise.resolve();
    }
    return loadRegion(s.region).then(({ offers, tax }) => {
      if (token !== seq) return;   // a newer change came in while the files loaded
      const by = groupRows(offers, tax, s), rom = S.rom;
      const view = phones.map((p) => ({ ...p, rows: narrow(by.get(p.id) || [], rom) }));
      els = new Map();
      const tpl = document.createElement("template");
      tpl.innerHTML = listHtml(view, s, "");
      tpl.content.querySelectorAll("li[data-id]").forEach((li) => els.set(li.dataset.id, li));
      phones.forEach((p) => { p.s = summarize(by.get(p.id) || [], rom); });
      note = ""; render();
    }, () => {
      if (token !== seq) return;
      // offline or a missing file: the prices on screen stay; say so only when the visitor asked for something new
      if (S.rom) { S.rom = ""; $("rom").value = ""; note = "Couldn't load prices for that storage size. Try again."; render(); }
    }).catch((e) => console.error(e));   // a bug while painting: say so in the console
  }

  // ---- controls ----
  const setQ = (v) => {
    S.q = v;
    if (v.trim()) { S.chip = "all"; S.brand = ""; }   // typing searches every phone: a chip chosen before would hide the match without saying why
    render();
  };
  q.addEventListener("input", () => setQ(q.value));
  $("clear-search").addEventListener("click", () => { q.value = ""; setQ(""); q.focus(); });
  root.addEventListener("click", (ev) => {
    const t = ev.target, chip = t.closest("#chips button"), sort = t.closest("#sorts button");
    if (chip) {
      if (chip.dataset.b) S.brand = S.brand === chip.dataset.b ? "" : chip.dataset.b;
      else { S.chip = chip.dataset.f; if (S.chip === "all") S.brand = ""; }
      render();
    } else if (sort) { S.sort = sort.dataset.s; render(); }
    else if (t.closest("#showall")) { S.all = true; render(); }
  });
  $("rom").addEventListener("change", (e) => { S.rom = e.target.value; apply(); });
  $("rom").addEventListener("focus", () => { loadRegion(load().region).catch(() => {}); }, { once: true });   // warm up before the choice is made

  window.addEventListener("dp:settings", () => apply());
  window.addEventListener("storage", (e) => {
    if (!e.key || e.key === "pc-watch") render();
    if (!e.key || (e.key.startsWith("pc-") && e.key !== "pc-watch")) apply();
  });
  window.addEventListener("pageshow", (e) => { if (e.persisted) render(); });   // back from a phone page after watching it

  // ---- the header's search button: on this page it just puts the cursor in the search ----
  const hb = document.querySelector('.top .icon-btn');
  if (hb) hb.addEventListener("click", (e) => { e.preventDefault(); q.focus(); q.scrollIntoView({ block: "center" }); });

  // ---- "?q=<text>" fills and applies the search, "#search" focuses it ----
  const params = new URLSearchParams(location.search), qp = params.get("q") || "";
  if (qp) { q.value = qp; setQ(qp); } else render();
  if (qp || params.has("q") || location.hash === "#search") q.focus({ preventScroll: !!qp });
  if (!isDefault(load())) apply();
}

if (typeof document !== "undefined") {
  const start = () => { const root = document.getElementById("home"); if (root) wire(root); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
}
