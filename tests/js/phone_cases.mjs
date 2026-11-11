// static/js/phone.js's pure helper: node phone_cases.mjs exits non-zero on the first failed case.
import assert from "node:assert/strict";
import { pickFromHash, pickHash, parseHash, focusSelector } from "../../static/js/phone.js";
import { memChips } from "../../static/js/blocks.js";
import { pickForMemory, nearestMemory } from "../../static/js/view.js";

const r = (edition, storage, state = "ok") => ({ edition, storage, state });
const rows = [r("china", "12/256"), r("global", "12/512"), r("china", "16/512"), r("global", "12/256", "soldout"),
              r("global", "16/1024"), r("china", "8/128", "stale"), r("global", "8/128", "soldout")];

// a chip tap: the selected version stays when it has a current price at the memory, else the other one is selected
assert.deepEqual(pickForMemory(rows, "16/512", "china"), { ed: "china", mem: "16/512" });
assert.deepEqual(pickForMemory(rows, "12/512", "china"), { ed: "global", mem: "12/512" });   // only Global has it: the version switches
assert.deepEqual(pickForMemory(rows, "12/256", "global"), { ed: "china", mem: "12/256" });   // Global's is sold out
// a memory nobody sells (or only sold out / stale): the default pick, the first ok row
assert.deepEqual(pickForMemory(rows, "8/128", "global"), { ed: "china", mem: "12/256" });
// after a settings change the chosen memory has no ok row any more: the same re-pick
const after = [r("china", "12/256", "nopay"), r("global", "12/512"), r("china", "16/512", "stale")];
assert.deepEqual(pickForMemory(after, "12/256", "china"), { ed: "global", mem: "12/512" });
// the nearest button: that memory for both boxes, on the box whose button it is
assert.equal(nearestMemory(rows, "global", "16/512"), "12/512");
assert.deepEqual(pickForMemory(rows, nearestMemory(rows, "global", "16/512"), "global"), { ed: "global", mem: "12/512" });

// a shared link's pick: memory and version for both boxes; a memory nobody sells is the default pick
assert.deepEqual(pickFromHash(rows, "#16-512-china"), { ed: "china", mem: "16/512" });
assert.deepEqual(pickFromHash(rows, "#12-512-china"), { ed: "global", mem: "12/512" });
assert.deepEqual(pickFromHash(rows, "#8-128-global"), { ed: "china", mem: "12/256" });
assert.deepEqual(pickFromHash(rows, "#99-9999-global"), { ed: "china", mem: "12/256" });
assert.equal(pickFromHash(rows, "#report-thanks"), null);
assert.equal(pickFromHash(rows, ""), null);

// the live site's shareable pick: #<ram>-<rom>-<version>
assert.equal(pickHash("china", "16/512"), "#16-512-china");
assert.equal(pickHash("global", "12/1024"), "#12-1024-global");
assert.equal(pickHash("china", "base"), "");
assert.equal(pickHash("china", null), "");
assert.equal(pickHash("asia", "12/256"), "");
assert.deepEqual(parseHash("#16-512-china"), { ed: "china", mem: "16/512" });
assert.deepEqual(parseHash("#12-1024-global"), { ed: "global", mem: "12/1024" });
for (const bad of ["", null, undefined, "#", "#16-512", "#16-512-asia", "#a-512-china", "16-512-china", "#16-512-china-x", "#report-thanks", "#16/512-china"]) {
  assert.equal(parseHash(bad), null, String(bad));
}
assert.deepEqual(parseHash(pickHash("global", "12/256")), { ed: "global", mem: "12/256" });

// a memory neither version has a current price for is a disabled chip (a tap on it can't be undone by the page); a phone
// with only "base" rows has no chips
const s = { region: "EU", area: "", pay: "card", cur: "eur" };
const chips = memChips([{ ...r("china", "12/256"), total: 1000, unknown: 0 }, r("china", "8/128", "stale"), r("global", "8/128", "soldout")], "12/256", s);
assert.match(chips, /data-m="8\/128" aria-pressed="false" disabled>/);
assert.doesNotMatch(chips, /data-m="12\/256"[^>]*disabled/);
assert.equal(memChips([r("china", "base")], "base", s), "");

// keyboard focus: the same control is found again after a repaint
const el = (tag, attrs, cls, boxId, own, side) => ({ tagName: tag, classList: cls ? [cls] : [], hasAttribute: (a) => a in attrs, getAttribute: (a) => attrs[a],
  parentElement: { closest: () => (boxId ? { id: boxId } : null) }, id: own || "",
  closest: () => (side ? { getAttribute: () => side } : null) });
assert.equal(focusSelector(el("BUTTON", { "data-e": "global" }, "pickbtn", "duel", "tab-global")), '#duel button.pickbtn[data-e="global"]');   // the select button has an id of its own
// a nearest button is gone after the repaint: the chip for its memory, else its box's select button
assert.equal(focusSelector(el("BUTTON", { "data-m": "12/512" }, "near", "duel", "", "global")), '#s-mems button[data-m="12/512"], #duel .side[data-e="global"] button.pickbtn');
assert.equal(focusSelector(el("BUTTON", { "data-m": "12/256" }, null, "s-mems")), '#s-mems button[data-m="12/256"]');
assert.equal(focusSelector(el("BUTTON", { "data-s": "total" }, null, "s-ledger")), '#s-ledger button[data-s="total"]');
assert.equal(focusSelector(el("A", { "data-e": "china" }, "go", "duel")), null);
assert.equal(focusSelector(el("BUTTON", {}, "watch", "phone")), null);
assert.equal(focusSelector(null), null);

// the price trend block follows the pick and the settings: after a memory, version or currency change it is built from
// that pick's series and currency (the paint step calls trendHtml with the pick and settings it just painted)
{
  const { trendHtml } = await import("../../static/js/phone.js");
  const { rows: viewRows } = await import("../../static/js/view.js");
  const tax = { EU: { rate_pct: 0 } };
  const offer = (label, ed, st, eur) => ({ store_label: label, edition: ed, storage: st, available: true, money: { eur, gbp: eur * 0.8 },
    pay: { card: 0 }, ship: { EU: { eur: 0, gbp: 0 } }, duties: { EU: true }, checked: "2026-10-30T11:00:00Z" });
  // change points: one point for a flat listing, a fall on the last day
  const ser = (...pts) => ({ cur: "eur", pts }), flat = (ratio) => ser(["2026-10-01", ratio]), fall = ser(["2026-10-01", 1.2], ["2026-10-30", 1]);
  const doc = {
    offers: [offer("Shop", "china", "12/256", 1000), offer("Shop", "global", "12/256", 1200), offer("Shop", "china", "16/512", 1500)],
    trend: { china: { "12/256": { Shop: fall }, "16/512": { Shop: flat(1) } }, global: { "12/256": { Shop: flat(1) } } },
  };
  const eur = { region: "EU", area: "", pay: "card", cur: "eur" }, gbp = { ...eur, cur: "gbp" };
  const html = (s, ed, mem) => trendHtml(doc, tax, viewRows(doc.offers, tax, s), s, { ed, mem }, "2026-10-30T12:00:00Z", "../history/x");
  const text = (h) => h.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  const a = html(eur, "china", "12/256");
  assert.match(text(a), /€1,000 · low €1,000 – high €1,200 Lowest price in 30 days Down 17% since first listed \(1 Oct\)/);
  assert.match(text(html(eur, "global", "12/256")), /Same price for 30 days/);                      // the other version's series
  assert.match(text(html(eur, "china", "16/512")), /Same price for 30 days/);                      // the other memory's series
  assert.match(text(html(gbp, "china", "12/256")), /£800 · low £800 – high ≈£960/);                 // the visitor's currency; a past day in GBP is an estimate (the offer is in EUR)
  assert.equal(html(eur, "global", "16/512"), "");                                                 // no current price at the pick: empty
  assert.equal(trendHtml(doc, tax, viewRows(doc.offers, tax, eur), eur, { ed: "china", mem: "12/256" }, null, "../history/x").includes("price_trend"), true);
}

// the carrier check (Review Focus 3): the country comes from the settings, never another country's networks
{
  const { countryFor, resolvePick, COUNTRY_NAMES } = await import("../../static/js/carriers.js");
  const st = (region, area = "") => ({ region, area, pay: "card", cur: "eur" });
  assert.equal(countryFor(st("EU", "DE")), "DE");
  assert.equal(countryFor(st("EU")), null);                    // EU without a country: the picker's own select
  assert.equal(countryFor(st("Global")), null);
  assert.equal(countryFor(st("Global", "DE")), null);          // a stale area never counts outside the EU
  assert.equal(countryFor(st("CA", "ON")), "CA");              // any province is Canada
  assert.equal(countryFor(st("CA")), "CA");
  assert.equal(countryFor(st("UK")), "GB");
  assert.equal(countryFor(st("US")), "US");
  assert.equal(countryFor(st("AU")), "AU");
  assert.equal(COUNTRY_NAMES.DE, "Germany");

  // Review Focus 4 (ledger ruling): a saved network that is gone, or belongs to another country, is ignored and nothing is
  // preselected ("Choose your network")
  const doc = { country: "DE", networks: [{ id: "de-a", mvnos: ["Cheapo"] }, { id: "de-b", mvnos: [] }] };
  assert.equal(resolvePick(doc, { country: "DE", network: "de-b" }, "DE"), "de-b");
  assert.equal(resolvePick(doc, { country: "DE", network: "de-a|Cheapo" }, "DE"), "de-a|Cheapo");   // a virtual carrier of a network
  assert.equal(resolvePick(doc, { country: "DE", network: "de-gone" }, "DE"), null);                // removed from the data
  assert.equal(resolvePick(doc, { country: "DE", network: "de-a|Gone" }, "DE"), null);              // its virtual carrier removed
  assert.equal(resolvePick(doc, { country: "FR", network: "de-b" }, "DE"), null);                   // saved for another country
  assert.equal(resolvePick(doc, { country: "DE", network: "" }, "DE"), null);
  for (const bad of [null, undefined, {}, { country: "DE" }, { country: "DE", network: 5 }, "x", []]) assert.equal(resolvePick(doc, bad, "DE"), null);
  assert.equal(resolvePick({ networks: [] }, { country: "DE", network: "de-a" }, "DE"), null);
  assert.equal(resolvePick(null, null, "DE"), null);
}

// the paint wiring on a minimal fake DOM: a failed load, no saved pick, a stale saved pick, a pick
{
  const { wireCarrier } = await import("../../static/js/phone.js");
  const net = (id, name, mvnos = []) => ({ id, name, lte: [1, 3], nr: [], basis: "used", complete: true, mvnos });
  const table = { lte: { 1: { mhz: 2100, class: "mid", use: "u" }, 3: { mhz: 1800, class: "mid", use: "u" } }, nr: {}, covers: {} };
  const DE = { v: 1, country: "DE", name: "Germany", networks: [net("de-a", "Anet", ["Cheapo"]), net("de-b", "Bnet")], bands: table };
  const bandSets = { china: { lte: [1, 3], nr: [] }, global: null };
  const L = { china: "China", global: "Global" };
  // respond(url): the file's promise, instead of DE for every file (France's refused unless failFR is false)
  const setup = ({ settings, saved = null, failFR = true, onNets = undefined, respond = null }) => {
    const el = (extra = {}) => ({ innerHTML: "", hidden: false, value: "", ...extra });
    const dom = { carrier: { ...el(), nets: el(), out: el(), country: el(), querySelector(q) { return q === ".cc-nets" ? this.nets : q === ".cc-country" ? this.country : this.out; } },
      "s-csum": el(), "s-eu": el(), "s-clink": el({ hidden: true }), "s-csums": el({ hidden: true }), "s-eulines": el(), "cc-net": el() };
    const store = new Map(saved ? [["pc-carrier", JSON.stringify(saved)]] : []);
    const calls = [];
    let handler = null;
    const cur = { ...settings };
    const cv = wireCarrier({
      root: { addEventListener: (t, f) => { handler = f; } }, $: (id) => dom[id] || null, load: () => cur, storage: { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) },
      getJson: (u) => { calls.push(u); return respond ? respond(u) : u.includes("FR") && failFR ? Promise.reject(new Error(u)) : Promise.resolve(DE); },
      bandSets, files: { DE: "carriers/DE.json", FR: "carriers/FR.json" }, eds: ["china", "global"], L, onNets });
    return { dom, cv, cur, calls, store, change: (id, value) => handler({ target: { id, value } }) };
  };
  const eu = (area) => ({ region: "EU", area, pay: "card", cur: "eur" });
  const text = (h) => h.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

  // DE paints the summary, the network list with "Choose your network" selected, and no verdict
  let t = setup({ settings: eu("DE") });
  await t.cv.paint();
  assert.match(t.dom["s-csum"].innerHTML, /In Germany: works fully on all 2 networks/);
  assert.equal(t.dom["s-eu"].hidden, true); assert.equal(t.dom["s-clink"].hidden, false);
  assert.equal(t.dom["s-csums"].hidden, false); assert.equal(t.dom["s-eulines"].hidden, true);
  assert.match(t.dom["s-csums"].innerHTML, /China version:<\/b> <span[^>]*>In Germany/);
  assert.match(t.dom.carrier.nets.innerHTML, /<option value="" selected>Choose your network<\/option>/);
  assert.equal(t.dom.carrier.out.innerHTML, "");
  // then a country whose file fails to load: the neutral state, nothing from Germany left, and the next paint retries
  t.cur.area = "FR";
  await t.cv.paint();
  assert.match(t.dom["s-csum"].innerHTML, /Pick your country to check its networks<\/a><\/span>\.$/);
  assert.equal(t.dom["s-eu"].hidden, false); assert.equal(t.dom["s-clink"].hidden, true);
  assert.equal(t.dom["s-csums"].hidden, true); assert.equal(t.dom["s-csums"].innerHTML, ""); assert.equal(t.dom["s-eulines"].hidden, false);
  assert.equal(t.dom.carrier.nets.innerHTML, ""); assert.equal(t.dom.carrier.out.innerHTML, "");
  await t.cv.paint();
  assert.equal(t.calls.filter((u) => u.includes("FR")).length, 2);
  // a settings country with no file at all is the same state
  t = setup({ settings: eu("PL") });
  await t.cv.paint();
  assert.match(t.dom["s-csum"].innerHTML, /Pick your country/); assert.equal(t.dom["s-eulines"].hidden, false); assert.equal(t.calls.length, 0);

  // a stale saved pick (network gone, or another country's) shows no verdict and no preselection
  for (const saved of [{ country: "DE", network: "de-gone" }, { country: "FR", network: "de-a" }]) {
    t = setup({ settings: eu("DE"), saved });
    await t.cv.paint();
    assert.equal(t.dom.carrier.out.innerHTML, "");
    assert.match(t.dom.carrier.nets.innerHTML, /<option value="" selected>Choose your network<\/option>/);
  }
  // a valid saved pick is shown, naming the network
  t = setup({ settings: eu("DE"), saved: { country: "DE", network: "de-b" } });
  await t.cv.paint();
  assert.match(t.dom.carrier.nets.innerHTML, /<option value="de-b" selected>/);
  assert.match(text(t.dom.carrier.out.innerHTML), /^On Bnet: China Works fully on 4G Global Bands not published for this version Bands only/);

  // picking a network: the verdict names it, the pick is saved, and the network list is left alone
  t = setup({ settings: eu("DE") });
  await t.cv.paint();
  const before = t.dom.carrier.nets.innerHTML;
  t.dom["cc-net"].value = "de-a|Cheapo";
  await t.change("cc-net", "de-a|Cheapo");
  await new Promise((r) => setTimeout(r, 0));
  assert.match(text(t.dom.carrier.out.innerHTML), /^On Cheapo \(Anet\): China Works fully on 4G/);
  assert.equal(t.dom.carrier.nets.innerHTML, before);
  assert.deepEqual(JSON.parse(t.store.get("pc-carrier")), { country: "DE", network: "de-a|Cheapo" });
  // the server rendered the country select (no country in the default settings) but these settings give one: it goes
  t = setup({ settings: eu("DE") });
  t.dom["cc-country"] = { value: "" }; t.dom.carrier.country.innerHTML = "<label>stale</label>";
  await t.cv.paint();
  assert.equal(t.dom.carrier.country.innerHTML, "");
  // Global: the picker's own country (saved) loads its file; the settings are not touched
  t = setup({ settings: { region: "Global", area: "", pay: "card", cur: "eur" }, saved: { country: "DE", network: "de-b" } });
  t.dom["cc-country"] = { value: "" };
  await t.cv.paint();
  assert.equal(t.dom["cc-country"].value, "DE");
  assert.match(t.dom["s-csum"].innerHTML, /In Germany: works fully on all 2 networks/);   // the picker's country gives the bullet and the Specs lines
  assert.equal(t.dom["s-csum"].hidden, false); assert.equal(t.dom["s-clink"].hidden, false); assert.equal(t.dom["s-eu"].hidden, true);
  assert.equal(t.dom["s-csums"].hidden, false); assert.equal(t.dom["s-eulines"].hidden, true);
  assert.match(t.dom["s-csums"].innerHTML, /China version:<\/b> <span[^>]*>In Germany/);
  assert.match(text(t.dom.carrier.out.innerHTML), /^On Bnet:/);
  // Global with no saved country: the neutral state, picker revealed, bullet shown with its prompt
  t = setup({ settings: { region: "Global", area: "", pay: "card", cur: "eur" } });
  t.dom["s-csum"].hidden = true; t.dom.carrier.hidden = true;
  await t.cv.paint();
  assert.match(t.dom["s-csum"].innerHTML, /Pick your country/); assert.equal(t.dom["s-csum"].hidden, false); assert.equal(t.dom.carrier.hidden, false);
  // choosing a country in the picker moves the bullet to its summary
  t.dom["cc-country"] = { value: "DE" };
  await t.change("cc-country", "DE");
  await new Promise((r) => setTimeout(r, 0));
  assert.match(t.dom["s-csum"].innerHTML, /In Germany: /); assert.equal(t.dom["s-eu"].hidden, true);

  // the price boxes' network lines (onNets): the settings' country only. A paint for another country than the lines on the
  // boxes are for first takes them away (none for a country until its file is in, the prompt without a country), then every
  // draw with the country's file brings its lines; a failed load leaves none (another country's lines would be wrong)
  const lines = [], keep = (n) => lines.push(n);
  const PICK = { tone: "pick", text: "Networks: choose your country" }, NONE = { tone: "muted", text: "Bands not published for this version" };
  const BLANK = { china: null, global: null }, DE_LINES = { china: { tone: "good", text: "✓ works on both networks in Germany" }, global: NONE };
  t = setup({ settings: eu("DE"), onNets: keep });
  await t.cv.paint();
  assert.deepEqual(lines.splice(0), [BLANK, DE_LINES]);   // the server's prompt is for no country: none, then Germany's
  await t.cv.paint();   // Germany again (another network picked, say): its lines, nothing taken away first
  assert.deepEqual(lines.splice(0), [DE_LINES]);
  t.cur.area = "FR";   // France's file fails to load: not Germany's lines, none
  await t.cv.paint();
  assert.deepEqual(lines.splice(0), [BLANK]);
  await t.cv.paint();  // France fails again: the lines shown are France's (none), kept
  assert.deepEqual(lines, []);
  assert.equal(t.calls.filter((u) => u.includes("FR")).length, 2);
  t.cur.area = "";     // no country: the prompt
  await t.cv.paint();
  assert.deepEqual(lines.splice(0), [{ china: PICK, global: NONE }]);
  // Global with the picker's own country: the picker checks Germany, the boxes keep the server's prompt (nothing sent)
  t = setup({ settings: { region: "Global", area: "", pay: "card", cur: "eur" }, saved: { country: "DE", network: "de-b" }, onNets: keep });
  t.dom["cc-country"] = { value: "" };
  await t.cv.paint();
  assert.equal(t.calls.length, 1); assert.deepEqual(lines.splice(0), []);
  assert.match(t.dom["s-csum"].innerHTML, /In Germany/);   // the picker did check Germany
  // ... and when the picker's country fails to load (after Germany's lines): still the prompt, which needs no file
  t = setup({ settings: eu("DE"), saved: { country: "FR", network: "" }, onNets: keep });
  await t.cv.paint();
  lines.splice(0);
  t.cur.region = "Global"; t.cur.area = "";
  await t.cv.paint();
  assert.deepEqual(t.calls, ["carriers/DE.json", "carriers/FR.json"]); assert.deepEqual(lines.splice(0), [{ china: PICK, global: NONE }]);
  // no carrier section (no version has bands): no lines, the server's stay
  t = setup({ settings: eu("DE"), onNets: keep });
  delete t.dom.carrier;
  await t.cv.paint();
  assert.deepEqual(lines, []);

  // a newly chosen country whose file is still on its way (or never comes): at once no line, not the previous country's
  // under the new country's prices; its lines once the file is in. To no country: the prompt at once, never the picker's
  const FR = { v: 1, country: "FR", name: "France", networks: [net("fr-a", "Fnet")], bands: table };
  const later = {};   // file -> settle it (the load hangs until then)
  const slow = (u) => u.includes("DE") ? Promise.resolve(DE) : new Promise((ok) => { later[u] = () => ok(FR); });
  const tick = () => new Promise((r) => setTimeout(r, 0));
  t = setup({ settings: eu("DE"), onNets: keep, respond: slow });
  await t.cv.paint();
  lines.splice(0);
  t.cur.area = "FR";
  const loading = t.cv.paint();
  assert.deepEqual(lines.splice(0), [BLANK]);   // before the file, in the same call that repaints the prices
  await tick();
  assert.deepEqual(lines, []);                  // still loading: none, and Germany's never back
  later["carriers/FR.json"]();
  await loading;
  assert.deepEqual(lines.splice(0), [{ china: { tone: "good", text: "✓ works on Fnet" }, global: NONE }]);
  t.cur.area = "DE";   // back to Germany, its file kept: France's lines go at once, Germany's follow
  await t.cv.paint();
  assert.deepEqual(lines.splice(0), [BLANK, DE_LINES]);
  t = setup({ settings: eu("DE"), saved: { country: "FR", network: "" }, onNets: keep, respond: slow });
  await t.cv.paint();
  lines.splice(0);
  t.cur.region = "Global"; t.cur.area = "";   // no country now; the picker's own France loads
  const picking = t.cv.paint();
  assert.deepEqual(lines.splice(0), [{ china: PICK, global: NONE }]);
  later["carriers/FR.json"]();
  await picking;
  assert.deepEqual(lines, []);   // France checked in the picker only
  assert.match(t.dom["s-csum"].innerHTML, /In France/);

  // malformed saved settings never reach an object lookup as a key: no throw, the neutral state
  for (const bad of ["constructor", "__proto__", "toString", "hasOwnProperty"]) {
    t = setup({ settings: eu("DE"), saved: { country: bad, network: "x" } });
    t.cur.area = ""; t.cur.region = "Global";
    await t.cv.paint();
    assert.equal(t.calls.length, 0, bad); assert.match(t.dom["s-csum"].innerHTML, /Pick your country/, bad);
    t = setup({ settings: eu(bad) });   // the EU pc-country
    await t.cv.paint();
    assert.equal(t.calls.length, 0, bad); assert.match(t.dom["s-csum"].innerHTML, /Pick your country/, bad); assert.equal(t.dom.carrier.nets.innerHTML, "", bad);
    t = setup({ settings: { region: "Global", area: "", pay: "card", cur: "eur" }, saved: { country: ["DE"], network: 1 } });
    await t.cv.paint();
    assert.equal(t.calls.length, 0);
  }
}

console.log("phone cases: ok");
