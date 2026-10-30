// The Drops page (spec §5.4, templates/drops.html). The server renders every row's current total as a store_row block for
// the default settings; this module filters the rows by the chips (All, China, Global, brands) and, when the visitor's
// settings differ from the defaults, loads the phone files of the phones on the page (and the tax file) and re-renders
// each total with blocks.js. No markup of its own beyond blocks.js output. Pure helpers are exported for tests/js/drops_cases.mjs.
import { rows as viewRows } from "./view.js";
import * as B from "./blocks.js";
import { load, isDefault } from "./settings.js";

/** True when a row (data-e edition, data-b brand) stays for the chip: {f: "all"|"china"|"global"} or {b: brand}. */
export const keeps = (item, chip) => (chip.b ? item.brand === chip.b : chip.f === "all" || chip.f === item.edition);

/** The view row of a listing: store label, version and memory. */
export const findRow = (rows, item) => rows.find((r) => r.store === item.store && r.edition === item.edition && r.storage === item.storage);

const getJson = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(u); return r.json(); });
const json = (v, d) => { try { return v ? JSON.parse(v) : d; } catch (e) { return d; } };

function wire(root) {
  const files = json(root.dataset.files, {}), now = root.dataset.now || null, tax = root.dataset.tax;
  const items = [...root.querySelectorAll("#list > li.drop")];
  const info = (li) => ({ brand: li.dataset.b, edition: li.dataset.e, storage: li.dataset.st, store: li.dataset.store, slug: li.dataset.slug });
  const chip = { f: "all" };
  const docs = new Map();   // slug -> phone file; a failed load is forgotten so the next try fetches again
  const loadDoc = (slug) => {
    if (!docs.has(slug)) docs.set(slug, getJson(files[slug]).catch((e) => { docs.delete(slug); throw e; }));
    return docs.get(slug);
  };
  let taxDoc = null;
  const loadTax = () => taxDoc || (taxDoc = getJson(tax).catch((e) => { taxDoc = null; throw e; }));

  function filter() {
    let n = 0;
    items.forEach((li) => { const on = keeps(info(li), chip); li.hidden = !on; n += on; });
    root.querySelectorAll("#chips button").forEach((b) => {
      b.setAttribute("aria-pressed", String(b.dataset.b ? chip.b === b.dataset.b : !chip.b && chip.f === b.dataset.f));
    });
    const none = root.querySelector("#no-results");
    if (none) none.hidden = n > 0;
    const c = root.querySelector("#count");
    if (c) c.textContent = n === items.length ? `${n} price drop${n === 1 ? "" : "s"} in the last 7 days` : `${n} of ${items.length} price drops in the last 7 days`;
  }

  // the totals for the current settings; only the phones on this page are loaded, and only when the settings are not the defaults
  let seq = 0;
  function reprice() {
    const s = load(), mine = ++seq;
    if (isDefault(s) || !tax) return;
    const slugs = [...new Set(items.map((li) => li.dataset.slug))];
    Promise.all([loadTax(), ...slugs.map(loadDoc)]).then(([t, ...docs2]) => {
      if (mine !== seq) return;
      const by = new Map(slugs.map((sl, i) => [sl, viewRows(docs2[i].offers, t, s)]));
      items.forEach((li) => {
        const row = findRow(by.get(li.dataset.slug) || [], info(li));
        if (row) li.querySelector("ul.offers").innerHTML = B.storeRow(row, s, json(li.dataset.l, { china: "China", global: "Global" }), now);
      });
    }).catch((e) => console.error(e));   // offline or a missing file: the default-settings totals stay
  }

  root.addEventListener("click", (ev) => {
    const b = ev.target.closest("#chips button");
    if (!b) return;
    for (const k of Object.keys(chip)) delete chip[k];
    if (b.dataset.b) chip.b = b.dataset.b; else chip.f = b.dataset.f;
    filter();
  });
  window.addEventListener("dp:settings", reprice);
  window.addEventListener("storage", (e) => { if (!e.key || (e.key.startsWith("pc-") && e.key !== "pc-watch")) reprice(); });
  reprice();
}

if (typeof document !== "undefined") {
  const start = () => { const root = document.getElementById("drops"); if (root) wire(root); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
}
