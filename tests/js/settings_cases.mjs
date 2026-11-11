// Pure-function cases for static/js/settings.js: node tests/js/settings_cases.mjs (exit 1 on the first failure).
import assert from "node:assert/strict";
import { load, save, guess, isDefault, label, forLine, watched, toggleWatch, refresh, REGION_CUR, curOwn, saveCurOwn, applyChange } from "../../static/js/settings.js";

const mem = (init = {}) => { const d = { ...init }; return { getItem: (k) => (k in d ? d[k] : null), setItem: (k, v) => { d[k] = String(v); }, d }; };
const names = { countries: { BG: "Bulgaria", DE: "Germany" }, provinces: { QC: "Quebec", ON: "Ontario" } };

// load: stored keys win, the missing pay falls back to card
assert.deepEqual(load(mem({ "pc-region": "CA", "pc-prov": "ON", "pc-cur": "cad" }), "", ""), { region: "CA", area: "ON", pay: "card", cur: "cad" });
assert.deepEqual(load(mem({ "pc-region": "EU", "pc-country": "BG", "pc-pay": "paypal", "pc-cur": "eur" }), "", ""), { region: "EU", area: "BG", pay: "paypal", cur: "eur" });
// nothing stored: guessed from the time zone; junk values fall back to the defaults
assert.deepEqual(load(mem(), "Europe/Sofia", "bg"), { region: "EU", area: "BG", pay: "card", cur: "eur" });
assert.deepEqual(load(mem(), "", ""), { region: "EU", area: "", pay: "card", cur: "eur" });
assert.deepEqual(load(mem({ "pc-region": "XX", "pc-cur": "yen", "pc-pay": "gold" }), "", ""), { region: "EU", area: "", pay: "card", cur: "eur" });
assert.deepEqual(load(mem({ "pc-region": "US" }), "", ""), { region: "US", area: "", pay: "card", cur: "usd" });
// prototype keys are not settings
assert.deepEqual(load(mem({ "pc-cur": "constructor", "pc-pay": "__proto__" }), "", ""), { region: "EU", area: "", pay: "card", cur: "eur" });
assert.deepEqual(load(mem({ "pc-cur": "toString", "pc-pay": "hasOwnProperty" }), "", ""), { region: "EU", area: "", pay: "card", cur: "eur" });
assert.deepEqual(load(mem({ "pc-region": "US" }), "Europe/Sofia", ""), { region: "US", area: "", pay: "card", cur: "eur" });

// guess
assert.deepEqual(guess("Europe/Sofia", "bg"), { region: "EU", area: "BG", cur: "eur" });
assert.deepEqual(guess("Europe/London", ""), { region: "UK", cur: "gbp" });
assert.deepEqual(guess("Australia/Sydney", ""), { region: "AU", cur: "aud" });
assert.deepEqual(guess("America/New_York", ""), { region: "US", cur: "usd" });
assert.deepEqual(guess("America/Vancouver", ""), { region: "CA", area: "BC", cur: "cad" });
assert.deepEqual(guess("America/Toronto", ""), { region: "CA", area: "", cur: "cad" });
assert.deepEqual(guess("Asia/Tokyo", ""), { region: "Global", cur: "usd" });
assert.deepEqual(guess("UTC", "en-GB"), { region: "UK", cur: "gbp" });
assert.deepEqual(guess("", "en-au"), { region: "AU", cur: "aud" });
assert.deepEqual(guess("", "en-CA"), { region: "CA", cur: "cad" });
assert.deepEqual(guess("Etc/GMT", "en-US"), {});

// isDefault, label
assert.equal(isDefault({ region: "EU", area: "", pay: "card", cur: "eur" }), true);
assert.equal(isDefault({ region: "EU", area: "BG", pay: "card", cur: "eur" }), false);
assert.equal(label({ region: "EU", area: "BG", pay: "card", cur: "eur" }), "BG · Card · €");
assert.equal(label({ region: "CA", area: "", pay: "paypal", cur: "cad" }), "CA · PayPal · C$");
assert.equal(label({ region: "Global", area: "", pay: "bank", cur: "usd" }), "World · Bank · $");
assert.equal(label({ region: "UK", area: "", pay: "card", cur: "gbp" }), "UK · Card · £");
assert.equal(label({ region: "AU", area: "", pay: "card", cur: "aud" }), "AU · Card · A$");

// forLine
const f = (region, area, pay) => forLine({ region, area, pay, cur: "eur" }, names);
assert.equal(f("EU", "BG", "card"), "Delivered to Bulgaria by card");
assert.equal(f("EU", "", "paypal"), "Delivered to the EU by PayPal");
assert.equal(f("UK", "", "bank"), "Delivered to the UK by bank transfer");
assert.equal(f("US", "", "card"), "Delivered to the US by card");
assert.equal(f("CA", "QC", "card"), "Delivered to Quebec by card");
assert.equal(f("CA", "", "card"), "Delivered to Canada by card");
assert.equal(f("AU", "", "card"), "Delivered to Australia by card");
assert.equal(f("Global", "", "card"), "Delivered to your country by card");

// save writes the live keys; watch list keeps the {"id": true} format
const st = mem();
save({ region: "CA", area: "ON", pay: "bank", cur: "cad" }, st);
assert.deepEqual([st.d["pc-region"], st.d["pc-prov"], st.d["pc-pay"], st.d["pc-cur"]], ["CA", "ON", "bank", "cad"]);
assert.deepEqual(load(st, "", ""), { region: "CA", area: "ON", pay: "bank", cur: "cad" });
const w = mem({ "pc-watch": '{"a":true,"b":{"k":"x","v":5}}' });
assert.deepEqual([...watched(w)].sort(), ["a", "b"]);
assert.equal(toggleWatch("c", w), true);
assert.equal(toggleWatch("a", w), false);
assert.deepEqual([...watched(w)].sort(), ["b", "c"]);

// refresh() paints only the button's visible label (the [data-prefs-label] span); the sr-only suffix is left alone
const span = { textContent: "EU · Card · €" };
globalThis.document = {
  getElementById: () => null,
  querySelectorAll: (sel) => (sel === "[data-prefs] [data-prefs-label]" ? [span] : []),
};
refresh();
assert.equal(span.textContent, label(load()));
delete globalThis.document;
// currency follows the region until the visitor picks one, then it sticks
assert.deepEqual(REGION_CUR, { EU: "eur", UK: "gbp", US: "usd", CA: "cad", AU: "aud", Global: "usd" });
const base = { region: "EU", area: "", pay: "card", cur: "eur" };
// a region change moves the currency while the visitor hasn't picked one
assert.deepEqual(applyChange(base, { ...base, region: "UK" }, "r", false), { s: { region: "UK", area: "", pay: "card", cur: "gbp" }, own: false });
assert.deepEqual(applyChange(base, { ...base, region: "Global" }, "r", false).s.cur, "usd");
// picking a currency makes it the visitor's own; later region changes leave it
const picked = applyChange(base, { ...base, cur: "usd" }, "c", false);
assert.deepEqual(picked, { s: { ...base, cur: "usd" }, own: true });
assert.deepEqual(applyChange(picked.s, { ...picked.s, region: "AU" }, "r", true).s.cur, "usd");
// other changes (country, payment) never touch the currency or the flag
assert.deepEqual(applyChange(base, { ...base, area: "BG" }, "area", false), { s: { ...base, area: "BG" }, own: false });
assert.deepEqual(applyChange(base, { ...base, pay: "bank" }, "p", true), { s: { ...base, pay: "bank" }, own: true });
// "Match currency to region" resets: the region's currency, no longer the visitor's own
assert.deepEqual(applyChange({ ...base, region: "CA", cur: "eur" }, { ...base, region: "CA", cur: "eur" }, "match", true), { s: { ...base, region: "CA", cur: "cad" }, own: false });
// curOwn: the stored flag wins. No flag (saved before it existed): the old site saved the currency on every change, so
// a saved currency counts as picked only when it differs from the saved region's own currency
assert.equal(curOwn(mem()), false);
assert.equal(curOwn(mem({ "pc-cur": "gbp" }), "Europe/Sofia"), true);
assert.equal(curOwn(mem({ "pc-region": "EU", "pc-country": "BG", "pc-cur": "eur" }), "Europe/Sofia"), false);
assert.equal(curOwn(mem({ "pc-region": "UK", "pc-cur": "eur" }), "Europe/Sofia"), true);
assert.equal(curOwn(mem({ "pc-region": "Global", "pc-cur": "usd" }), "Europe/Sofia"), false);
assert.equal(curOwn(mem({ "pc-region": "EU", "pc-cur": "eur", "pc-cur-pick": "1" }), "Europe/Sofia"), true);
// a stale pc-cur-own from the first version is ignored
assert.equal(curOwn(mem({ "pc-region": "UK", "pc-cur": "gbp", "pc-cur-own": "1" }), "Europe/Sofia"), false);
// the reported case: an older EU visitor switches to the UK and the currency follows
{ const st = mem({ "pc-region": "EU", "pc-country": "BG", "pc-pay": "card", "pc-cur": "eur" });
  const was = load(st, "Europe/Sofia"), r = applyChange(was, { ...was, region: "UK", area: "" }, "r", curOwn(st, "Europe/Sofia"));
  assert.equal(r.s.cur, "gbp"); assert.equal(r.own, false); }
assert.equal(curOwn(mem({ "pc-cur": "gbp", "pc-cur-pick": "0" })), false);
assert.equal(curOwn(mem({ "pc-cur-pick": "1" })), true);
const so = mem(); saveCurOwn(false, so); assert.equal(so.d["pc-cur-pick"], "0"); saveCurOwn(true, so); assert.equal(so.d["pc-cur-pick"], "1");

// the page wiring on a minimal fake DOM: any [data-prefs] element opens the settings sheet, also one painted after
// startup (a price box's "choose your country"), and a click opens it once
{
  let opened = 0;
  const any = () => ({ hidden: false, value: "", checked: false, dataset: {}, querySelector: () => any(), querySelectorAll: () => [], addEventListener() {} });
  const sheet = { ...any(), showModal: () => { opened += 1; } };
  const on = (el) => ({ ...el, listeners: [], addEventListener(t, f) { this.listeners.push([t, f]); } });
  const header = on({}), docListeners = [];   // header: the button that is there at startup
  globalThis.window = { addEventListener() {} };
  globalThis.document = { readyState: "complete", documentElement: { classList: { remove() {} } }, querySelector: () => null,
    getElementById: (id) => (id === "prefs-sheet" ? sheet : null), querySelectorAll: (sel) => (sel === "[data-prefs]" ? [header] : []),
    addEventListener: (t, f) => docListeners.push([t, f]) };
  await import("../../static/js/settings.js?page");   // a fresh copy of the module: it wires this document
  // a click on el (or inside it): its own listeners, then the document's (the event bubbles up)
  const click = (el) => {
    const ev = { target: { closest: (sel) => (sel === "[data-prefs]" ? el : null) } };
    for (const [t, f] of [...(el ? el.listeners : []), ...docListeners]) if (t === "click") f(ev);
  };
  click(header);
  assert.equal(opened, 1);
  click(on({}));   // painted later
  assert.equal(opened, 2);
  click(null);     // anywhere else
  assert.equal(opened, 2);
  delete globalThis.document; delete globalThis.window;
}
console.log("settings ok");
