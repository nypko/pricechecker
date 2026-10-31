// The compare page (spec §5.5, templates/compare.html): up to three phones side by side, chosen in the page and kept in the
// URL hash ("#a,b,c@16-512") so a comparison can be shared. Each chosen phone's v1 data file is fetched and priced with the
// visitor's settings; every price is the shared price box (blocks.js). Key specs come with the page (pages/compare.py).
// The pure helpers are exported for tests/js/compare_cases.mjs; everything touching the page is guarded.
import { rows as viewRows, bestOf, closest, size } from "./view.js";
export { closest };   // the rule lives in view.js now; compare_cases.mjs still imports it from here
import * as B from "./blocks.js";
import { load } from "./settings.js";

const EDS = ["china", "global"];   // box order: the China version (red) first, Global (blue) second

// ---- pure helpers ----

/** One price box; the winning one carries its own "Lowest delivered" label, inside the box it describes. */
export const boxHtml = (inner, low) => `<div class="cm-box${low ? " low" : ""}">${inner}` +
  (low ? '<p class="cm-win"><span class="tick">✓</span> Lowest delivered<span class="sr-only"> of these</span></p>' : "") + "</div>";

/** One phone's boxes, each version priced at the shared memory `mem` ("" = its own best): the shared price box, so a version
 *  without that memory says "Not sold with ..." and offers its nearest. `total` is the lowest settled delivered price among
 *  the versions that have one at that memory, else null (a "Not sold" or other no-price box never wins). */
export function column(p, rows, mem, s) {
  const L = { global: "Global", china: p.cl };
  const total = [];
  const boxes = EDS.filter((e) => p.editions.includes(e)).map((e) => {
    const rs = rows.filter((r) => r.edition === e);
    const best = bestOf(rs, e, mem || null);
    const t = best && best.settled ? best.total : null;
    if (t !== null) total.push(t);
    return (win) => boxHtml(B.priceBox(rs, e, mem || null, s, L, false, false), win && t !== null && t === Math.min(...total));
  });
  return { html: (win) => boxes.map((b) => b(win)).join(""), total: total.length ? Math.min(...total) : null };
}

/** The shared memory after a click on memory `m`: a nearest button sets it, a chip toggles its own off again. */
export const memAfterClick = (cur, m, near) => (!near && cur === m ? "" : m);

/** Index of the single lowest (dir -1) or highest (dir 1) usable value, else -1 (a tie, or nothing to rank). */
function single(vals, dir) {
  const ok = vals.filter((v) => v !== null);
  if (!ok.length) return -1;
  const top = dir > 0 ? Math.max(...ok) : Math.min(...ok);
  const at = vals.map((v, i) => (v === top ? i : -1)).filter((i) => i >= 0);
  return at.length === 1 ? at[0] : -1;
}

/** The green-check winners among compared phones, as column indexes (-1: nobody). A column is {total, settled?, battery,
 *  charging}: the lowest settled delivered total, the biggest battery and the fastest wired charging win. A tie, a missing
 *  value or a single phone marks nobody. */
export function winners(columns) {
  const none = { price: -1, battery: -1, charging: -1 };
  if (columns.length < 2) return none;
  const num = (v) => (typeof v === "number" && v > 0 ? v : null);
  return {
    price: single(columns.map((c) => (typeof c.total === "number" && c.settled !== false ? c.total : null)), -1),
    battery: single(columns.map((c) => num(c.battery)), 1),
    charging: single(columns.map((c) => num(c.charging)), 1),
  };
}

/** "#a,b,c@16-512" -> {ids, mem: "16/512"}. At most three ids, no repeats, only `known` ids when a list is given;
 *  the memory only counts with a phone chosen. Anything unreadable gives no phones. */
export function parseHash(hash, known = null) {
  let h;
  try { h = decodeURIComponent(String(hash || "").replace(/^#/, "")); } catch (e) { return { ids: [], mem: "" }; }
  const m = /@(\d+)-(\d+)$/.exec(h);
  const ids = h.replace(/@.*$/, "").split(",").filter((s, i, a) => s && a.indexOf(s) === i && (!known || known.includes(s))).slice(0, 3);
  return { ids, mem: ids.length && m ? `${m[1]}/${m[2]}` : "" };
}

/** The shareable hash for the phones and memory shown; "" for no phones. */
export function formatHash(ids, mem) {
  return ids.length ? `#${ids.join(",")}${mem ? "@" + mem.replace("/", "-") : ""}` : "";
}

/** True when the compared phones' cells for one spec aren't all the same ("Show only the differences"). */
export function differs(cells) {
  return cells.length > 1 && new Set(cells.map((c) => JSON.stringify(c ?? null))).size > 1;
}

/** One-tap comparisons to start from (the live site's rules). Nothing chosen: the three newest phones, then the two newest of
 *  each of the (up to) three brands with the most phones. One chosen: its brand's two newest others, then the newest from
 *  another brand, each paired with it. Returns {heading, items: [{t, ids}]}; phones are {id, name, brand, announced}. */
export function starters(phones, chosen) {
  const newest = phones.map((p, i) => [p, i]).sort(([a, i], [b, j]) => String(b.announced || "").localeCompare(String(a.announced || "")) || i - j).map(([p]) => p);
  if (chosen.length) {
    const q0 = phones.find((p) => p.id === chosen[0]);
    if (!q0) return { heading: "", items: [] };
    const pick = newest.filter((q) => q.id !== q0.id && q.brand === q0.brand).slice(0, 2).concat(newest.filter((q) => q.brand !== q0.brand).slice(0, 1));
    return { heading: `Or compare ${q0.name} with:`, items: pick.map((q) => ({ t: q.name, ids: [q0.id, q.id] })) };
  }
  const items = [{ t: "The three newest phones", ids: newest.slice(0, 3).map((q) => q.id) }];
  const brands = new Map();
  newest.forEach((q) => brands.set(q.brand, [...(brands.get(q.brand) || []), q]));
  [...brands.values()].filter((l) => l.length > 1).sort((a, b) => b.length - a.length).slice(0, 3)
    .forEach((l) => items.push({ t: `${l[0].name} vs ${l[1].name}`, ids: [l[0].id, l[1].id] }));
  return { heading: "Start with one of these", items };
}

// ---- the page ----

const memOrder = (a, b) => { const x = size(a), y = size(b); return (x.rom - y.rom) || (x.ram - y.ram); };
const getJson = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); });

function wire(root) {
  const app = document.getElementById("cmp-app"), src = document.getElementById("cmp-phones");
  let data;
  try { data = JSON.parse(src.textContent); } catch (e) { return; }
  const by = new Map(data.phones.map((p) => [p.id, p]));
  const known = data.phones.map((p) => p.id);
  const S = { ids: [], mem: "", only: false };
  const cache = new Map();   // phone id -> its data file's promise; a failed load is forgotten, so the next try asks again
  const docOf = (p) => { if (!cache.has(p.id)) cache.set(p.id, getJson(p.file).catch((e) => { cache.delete(p.id); throw e; })); return cache.get(p.id); };
  let taxDoc = null;
  const taxOf = () => taxDoc || (taxDoc = getJson(root.dataset.tax).catch((e) => { taxDoc = null; throw e; }));
  let token = 0;

  const go = (ids, mem) => {
    S.ids = ids; S.mem = ids.length ? mem : "";
    if (history.replaceState) history.replaceState(null, "", location.pathname + location.search + formatHash(S.ids, S.mem));
    paint();
  };

  // ---- pieces ----
  const picker = () => {
    const left = data.phones.filter((p) => !S.ids.includes(p.id)), brands = [...new Set(left.map((p) => p.brand))];
    return '<label class="cm-add"><span>Add a phone</span><select data-add><option value="">Choose a phone</option>' +
      brands.map((b) => `<optgroup label="${B.esc(b)}">` + left.filter((p) => p.brand === b).map((p) => `<option value="${B.esc(p.id)}">${B.esc(p.name)}</option>`).join("") + "</optgroup>").join("") +
      "</select></label>";
  };
  const head = (chosen, n) => {
    const cells = [];
    for (let i = 0; i < n; i++) {
      const p = chosen[i];
      cells.push(p
        ? `<div class="cm-h"><a class="cm-name" href="phones/${B.esc(p.id)}">${B.esc(p.name)}</a><span class="cm-sub">${B.esc(p.brand)}${p.announced ? " · " + B.month(p.announced) : ""}</span>` +
          `<button type="button" class="cm-x" data-x="${B.esc(p.id)}" aria-label="Remove ${B.esc(p.name)}">Remove</button></div>`
        : i === chosen.length ? `<div class="cm-h">${picker()}</div>` : '<div class="cm-h cm-empty"></div>');
    }
    return `<div class="cm-grid cm-head" style="--n:${n}">${cells.join("")}</div>`;
  };

  const half = (e, t, L) => `<div class="half ${e === "china" ? "cn" : "gl"}"><span class="htag">${B.esc(L[e])}</span>${t === null ? '<span class="na">Not listed</span>' : B.esc(t)}</div>`;
  function cell(p, c, win) {
    const td = (cls, inner) => { const k = [cls, win && "win"].filter(Boolean).join(" "); return `<td${k ? ` class="${k}"` : ""}>${inner}</td>`; };
    if (!p.c) return td("na", "No spec sheet yet");
    if (c === null) return td("na", `Not on ${B.esc(p.brand)}'s page`);
    if (typeof c === "string") return td("", B.esc(c) + (win ? '<span class="tick">✓<span class="sr-only"> best of these</span></span>' : ""));
    const L = { global: "Global", china: p.cl };
    return td("split-td", `<div class="split">${half("china", c[0], L)}${half("global", c[1], L)}</div>`);
  }

  function specs(chosen, n, win) {
    const n_diff = data.rows.filter((r, i) => differs(chosen.map((p) => (p.c ? p.c[i] : "-")))).length;
    let h = `<h2 class="cm-h2">Key specs</h2>`;
    if (chosen.length > 1) {
      h += `<div class="difbar"><span>${n_diff ? `${n_diff} of ${data.rows.length} specs differ.` : "These phones list the same specs."}</span>` +
        (n_diff ? `<button type="button" id="cm-only" aria-pressed="${S.only}">${S.only ? "Show all specs" : `Show only the ${n_diff} difference${n_diff === 1 ? "" : "s"}`}</button>` : "") + "</div>";
    }
    h += `<table class="cm-t" style="--n:${n}"><caption class="sr-only">Key specs of the chosen phones</caption>`;
    data.rows.forEach((r, i) => {
      const d = differs(chosen.map((p) => (p.c ? p.c[i] : "-")));
      const mark = r.id === "battery" ? win.battery : r.id === "wired" ? win.charging : -1;
      let tds = "";
      for (let j = 0; j < n; j++) {
        const p = chosen[j];
        tds += p ? cell(p, p.c ? p.c[i] : null, j === mark) : "<td></td>";
      }
      h += `<tbody${S.only && chosen.length > 1 && !d ? " hidden" : ""} class="f${d ? " diff" : ""}"><tr><th colspan="${n}" scope="colgroup">${B.esc(r.label)}</th></tr><tr>${tds}</tr></tbody>`;
    });
    return h + "</table>";
  }

  // ---- paint ----
  function start(chosen) {
    if (chosen.length > 1) return "";
    const st = starters(data.phones, S.ids);
    return st.items.length ? `<p class="lbl" id="cm-start-h">${B.esc(st.heading)}</p><div class="mems cm-start" role="group" aria-labelledby="cm-start-h">` +
      st.items.map((x) => `<button type="button" data-s="${B.esc(x.ids.join(","))}">${B.esc(x.t)}</button>`).join("") + "</div>" : "";
  }
  function frame(chosen, n, inner) {
    return `<p class="cm-prompt"${chosen.length ? " hidden" : ""}>Pick two or three phones to compare.</p>` + head(chosen, n) + inner + start(chosen);
  }
  async function paint() {
    const my = ++token, chosen = S.ids.map((id) => by.get(id)), n = Math.max(2, Math.min(3, chosen.length + 1));
    const a = document.activeElement, back = a && app.contains(a) ? focusKey(a) : null;
    const done = (html) => {
      if (my !== token) return;
      app.innerHTML = html;
      if (back) { const el = app.querySelector(back) || app.querySelector("[data-add]"); if (el && !el.disabled) el.focus({ preventScroll: true }); }
    };
    if (!chosen.length) { done(frame(chosen, n, "")); return; }
    const s = load();
    let docs, tax;
    try { [tax, ...docs] = await Promise.all([taxOf(), ...chosen.map(docOf)]); } catch (e) {
      done(frame(chosen, n, '<p class="cm-err" role="alert">The prices could not be loaded. <button type="button" id="cm-retry">Try again</button></p>'));
      return;
    }
    if (my !== token) return;
    const all = docs.map((d) => viewRows(d.offers, tax, s));
    const cols = chosen.map((p, i) => column(p, all[i], S.mem, s));
    const win = winners(chosen.map((p, i) => ({ total: cols[i].total, battery: p.k.battery, charging: p.k.charging })));
    // the memory chips: every memory some chosen phone has a current price for
    const mems = [...new Set(all.flatMap((rs) => rs.filter((r) => r.state === "ok" && r.storage !== "base").map((r) => r.storage)))].sort(memOrder);
    let inner = "";
    if (mems.length) {
      inner += '<p class="lbl" id="cm-mem-h">Price all at one memory</p><div class="mems" role="group" aria-labelledby="cm-mem-h">' +
        mems.map((m) => `<button type="button" data-m="${B.esc(m)}" aria-pressed="${m === S.mem}">${B.memLabel(m)}</button>`).join("") + "</div>";
      inner += `<p class="cm-note">${S.mem ? "A phone that doesn't have it says so and offers its nearest memory." : "Tap a memory to price every phone at it."}</p>`;
    }
    inner += `<div class="cm-grid cm-prices" style="--n:${n}">` + chosen.map((p, j) =>
      `<div class="cm-col${win.price === j ? " win" : ""}">${cols[j].html(win.price === j)}` +
"</div>").join("") + "</div>";
    inner += specs(chosen, n, win);
    done(frame(chosen, n, inner));
  }

  // a selector for the same control after a repaint
  function focusKey(el) {
    // a nearest button is gone after the repaint: the chip for its memory (now pressed) takes the focus
    for (const a of ["data-m", "data-x", "data-s"]) if (el.hasAttribute && el.hasAttribute(a)) return `button[${a}="${String(el.getAttribute(a)).replace(/["\\]/g, "\\$&")}"]:not(.near)`;
    if (el.id === "cm-only" || el.id === "cm-retry") return "#" + el.id;
    return el.hasAttribute && el.hasAttribute("data-add") ? "[data-add]" : null;
  }

  app.addEventListener("change", (ev) => {
    const sel = ev.target.closest && ev.target.closest("select[data-add]");
    if (sel && sel.value && by.has(sel.value) && S.ids.length < 3) go([...S.ids, sel.value], S.mem);
  });
  app.addEventListener("click", (ev) => {
    const t = ev.target, m = t.closest("button[data-m]"), x = t.closest("button[data-x]"), st = t.closest("button[data-s]");
    if (st) go(st.dataset.s.split(","), "");
    else if (m) go(S.ids, memAfterClick(S.mem, m.dataset.m, m.classList.contains("near")));
    else if (x) go(S.ids.filter((id) => id !== x.dataset.x), S.mem);
    else if (t.closest("#cm-only")) { S.only = !S.only; paint(); }
    else if (t.closest("#cm-retry")) paint();
  });
  const again = () => paint();
  window.addEventListener("dp:settings", again);
  window.addEventListener("storage", (e) => { if (!e.key || (e.key.startsWith("pc-") && e.key !== "pc-watch")) again(); });
  window.addEventListener("hashchange", () => { Object.assign(S, parseHash(location.hash, known)); paint(); });
  Object.assign(S, parseHash(location.hash, known));
  paint();
}

if (typeof document !== "undefined") {
  const start = () => { const root = document.getElementById("cmp"); if (root) wire(root); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
}
