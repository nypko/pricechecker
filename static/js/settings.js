// The visitor's delivery settings (where it ships, how they pay, currency) and the shell that shows them: the header
// button, the settings sheet, the "Delivered to ..." line under each H1, the watch list, hide-on-scroll for the header.
// Storage keys are the live site's (pc-region, pc-country, pc-prov, pc-pay, pc-cur, pc-watch) so saved choices carry over.
// The pure parts take storage / time zone / language as arguments, so node tests import this file; every DOM and
// window access is guarded. No dynamic import().
import { DEFAULT } from "./view.js";

const REGIONS = ["EU", "UK", "US", "CA", "AU", "Global"];
const SYMBOL = { eur: "€", gbp: "£", usd: "$", cad: "C$", aud: "A$" };
const PAY_LABEL = { card: "Card", paypal: "PayPal", bank: "Bank" };
export const PAY_BY = { card: "card", paypal: "PayPal", bank: "bank transfer" };
export const PLACE = { EU: "the EU", UK: "the UK", US: "the US", CA: "Canada", AU: "Australia", Global: "your country" };

// First visit: region and currency from the device's time zone, worked out in the browser (no IP lookup, nothing sent
// anywhere); the browser language only when there is no time zone.
const EU_TZ = /^(Europe\/(Amsterdam|Athens|Berlin|Bratislava|Brussels|Bucharest|Budapest|Copenhagen|Dublin|Helsinki|Lisbon|Ljubljana|Luxembourg|Madrid|Malta|Mariehamn|Nicosia|Paris|Prague|Riga|Rome|Sofia|Stockholm|Tallinn|Vienna|Vilnius|Warsaw|Zagreb)|Asia\/(Nicosia|Famagusta)|Atlantic\/(Madeira|Azores))$/;
const US_TZ = /^(America\/(New_York|Chicago|Denver|Los_Angeles|Phoenix|Anchorage|Juneau|Sitka|Nome|Yakutat|Metlakatla|Adak|Detroit|Boise|Menominee|Indiana\/.+|Kentucky\/.+|North_Dakota\/.+)|Pacific\/Honolulu)$/;
// EU time zone -> member state, for that country's VAT rate (config/import_tax.yaml)
const TZ_COUNTRY = { Amsterdam: "NL", Athens: "GR", Berlin: "DE", Busingen: "DE", Bratislava: "SK", Brussels: "BE", Bucharest: "RO",
  Budapest: "HU", Copenhagen: "DK", Dublin: "IE", Helsinki: "FI", Mariehamn: "FI", Lisbon: "PT", Madeira: "PT", Azores: "PT",
  Ljubljana: "SI", Luxembourg: "LU", Madrid: "ES", Ceuta: "ES", Malta: "MT", Nicosia: "CY", Famagusta: "CY", Paris: "FR",
  Prague: "CZ", Riga: "LV", Rome: "IT", Sofia: "BG", Stockholm: "SE", Tallinn: "EE", Vienna: "AT", Vilnius: "LT", Warsaw: "PL", Zagreb: "HR" };
// Canadian time zones that belong to one province (Toronto and Halifax each cover two, so no guess there)
const TZ_PROV = { Vancouver: "BC", Edmonton: "AB", Winnipeg: "MB", Regina: "SK", Swift_Current: "SK", St_Johns: "NL", Moncton: "NB",
  Montreal: "QC", Whitehorse: "YT", Dawson: "YT", Yellowknife: "NT", Inuvik: "NT", Iqaluit: "NU", Rankin_Inlet: "NU", Cambridge_Bay: "NU" };
const CA_TZ = /^America\/(Toronto|Montreal|Vancouver|Edmonton|Winnipeg|Regina|Swift_Current|Halifax|Glace_Bay|Goose_Bay|St_Johns|Moncton|Whitehorse|Dawson|Dawson_Creek|Fort_Nelson|Creston|Yellowknife|Inuvik|Iqaluit|Rankin_Inlet|Cambridge_Bay|Resolute|Atikokan|Blanc-Sablon|Nipigon|Thunder_Bay|Rainy_River|Pangnirtung)$/;

/** Partial settings from a time zone and browser language: {region, cur, area?} or {} when neither says anything. */
export function guess(tz, lang) {
  lang = (lang || "").toLowerCase();
  if (tz && !/^(UTC|Etc\/)/.test(tz)) {
    const city = tz.split("/").pop();
    if (tz === "Europe/London") return { region: "UK", cur: "gbp" };
    if (/^Australia\//.test(tz)) return { region: "AU", cur: "aud" };
    if (EU_TZ.test(tz)) return { region: "EU", area: TZ_COUNTRY[city] || "", cur: "eur" };
    if (US_TZ.test(tz)) return { region: "US", cur: "usd" };
    if (CA_TZ.test(tz)) return { region: "CA", area: TZ_PROV[city] || "", cur: "cad" };
    return { region: "Global", cur: "usd" };
  }
  if (/-gb$/.test(lang)) return { region: "UK", cur: "gbp" };
  if (/-au$/.test(lang)) return { region: "AU", cur: "aud" };
  if (/-ca$/.test(lang)) return { region: "CA", cur: "cad" };
  return {};
}

const store = () => { try { return typeof localStorage !== "undefined" ? localStorage : null; } catch (e) { return null; } };
const get = (st, k) => { try { return st ? st.getItem(k) : null; } catch (e) { return null; } };
const put = (st, k, v) => { try { if (st) st.setItem(k, v); } catch (e) { /* private mode: the choice just isn't remembered */ } };
const zone = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) { return ""; } };
const language = () => (typeof navigator !== "undefined" && navigator.language) || "";

/** The saved settings, else the guess, else the defaults: {region, area, pay, cur}. area = country (EU) or province (CA). */
export function load(storage = store(), tz = zone(), lang = language()) {
  const g = guess(tz, lang);
  const pick = (k) => get(storage, "pc-" + k) || g[k];
  let region = pick("region"), cur = pick("cur"), pay = pick("pay");
  if (!REGIONS.includes(region)) region = DEFAULT.region;
  // own keys only: "constructor" or "__proto__" in storage must not pass as a currency or payment method
  if (!Object.hasOwn(SYMBOL, cur)) cur = region === "EU" ? DEFAULT.cur : "usd";
  if (!Object.hasOwn(PAY_LABEL, pay)) pay = DEFAULT.pay;
  const saved = region === "EU" ? get(storage, "pc-country") : region === "CA" ? get(storage, "pc-prov") : "";
  const area = region === "EU" || region === "CA" ? saved || (g.region === region ? g.area : "") || "" : "";
  return { region, area, pay, cur };
}

/** Write the settings to the live keys and tell the page (window event dp:settings, detail = settings). */
export function save(s, storage = store()) {
  put(storage, "pc-region", s.region);
  put(storage, "pc-pay", s.pay);
  put(storage, "pc-cur", s.cur);
  if (s.region === "EU") put(storage, "pc-country", s.area || "");
  if (s.region === "CA") put(storage, "pc-prov", s.area || "");
  if (typeof window !== "undefined" && typeof CustomEvent !== "undefined") window.dispatchEvent(new CustomEvent("dp:settings", { detail: s }));
}

export const isDefault = (s) => s.region === DEFAULT.region && !s.area && s.pay === DEFAULT.pay && s.cur === DEFAULT.cur;

/** "BG · Card · €" (the picked country or province, else the region; Global reads "Elsewhere"). */
export const label = (s) => `${s.area || (s.region === "Global" ? "Elsewhere" : s.region)} · ${PAY_LABEL[s.pay]} · ${SYMBOL[s.cur]}`;

/** "Delivered to Bulgaria by card"; names = {countries: {BG: "Bulgaria"}, provinces: {QC: "Quebec"}} */
export function forLine(s, names = {}) {
  const list = s.region === "EU" ? names.countries : s.region === "CA" ? names.provinces : null;
  const place = (list && list[s.area]) || PLACE[s.region] || PLACE.Global;
  return `Delivered to ${place} by ${PAY_BY[s.pay]}`;
}

// ---- watched phones: pc-watch = {"<id>": true} (older entries hold an object; any truthy value counts) ----
function watchMap(storage) { try { return JSON.parse(get(storage, "pc-watch") || "{}") || {}; } catch (e) { return {}; } }
export const watched = (storage = store()) => new Set(Object.keys(watchMap(storage)).filter((k) => watchMap(storage)[k]));
/** Flip one phone's watch; true when it is now watched. */
export function toggleWatch(id, storage = store()) {
  const w = watchMap(storage), on = !w[id];
  if (on) w[id] = true; else delete w[id];
  put(storage, "pc-watch", JSON.stringify(w));
  return on;
}

// ---- the page: everything below needs a document ----
const dialog = () => document.getElementById("prefs-sheet");
function namesOf(d) {
  try { return { countries: JSON.parse(d.dataset.countries || "{}"), provinces: JSON.parse(d.dataset.provinces || "{}") }; } catch (e) { return {}; }
}

/** Paint the header button and every [data-for] line from the saved settings. */
export function refresh() {
  if (typeof document === "undefined") return;
  const s = load(), d = dialog(), names = d ? namesOf(d) : {};
  // only the visible part changes: the button's sr-only ", delivery settings, change" stays, so its name keeps the label
  document.querySelectorAll("[data-prefs] [data-prefs-label]").forEach((t) => { t.textContent = label(s); });
  document.querySelectorAll("[data-for]").forEach((p) => { p.textContent = forLine(s, names); });
}

function fillSheet(d, s) {
  const form = d.querySelector("form");
  [["r", s.region], ["p", s.pay], ["c", s.cur]].forEach(([n, v]) => {
    const r = form.querySelector(`input[name="${n}"][value="${v}"]`);
    if (r) r.checked = true;
  });
  const eu = form.querySelector("[data-area=EU]"), ca = form.querySelector("[data-area=CA]");
  eu.hidden = s.region !== "EU"; ca.hidden = s.region !== "CA";
  eu.querySelector("select").value = s.region === "EU" ? s.area : "";
  ca.querySelector("select").value = s.region === "CA" ? s.area : "";
}
function readSheet(d) {
  const form = d.querySelector("form"), v = (n) => (form.querySelector(`input[name="${n}"]:checked`) || {}).value;
  const region = v("r") || DEFAULT.region;
  const sel = region === "EU" ? form.querySelector("[data-area=EU] select") : region === "CA" ? form.querySelector("[data-area=CA] select") : null;
  return { region, area: sel ? sel.value : "", pay: v("p") || DEFAULT.pay, cur: v("c") || DEFAULT.cur };
}

export function openSheet() {
  const d = dialog();
  if (!d) return;
  fillSheet(d, load());
  if (d.showModal) d.showModal(); else d.setAttribute("open", "");
}

function wire() {
  document.documentElement.classList.remove("no-js");
  const d = dialog();
  document.querySelectorAll("[data-prefs]").forEach((b) => b.addEventListener("click", openSheet));
  if (d) {
    const form = d.querySelector("form");
    // changing the region shows its country / province list; every change is saved at once and the page repaints
    form.addEventListener("change", (e) => {
      const was = load(), s = readSheet(d);
      if (e.target.name === "r" && s.region !== was.region) s.area = "";   // the old list's pick means nothing in the new region
      fillSheet(d, s);
      save(s);
      refresh();
    });
    d.addEventListener("click", (e) => { if (e.target === d) d.close(); });   // tap outside the panel
  }
  window.addEventListener("dp:settings", refresh);
  window.addEventListener("storage", refresh);
  refresh();
  hideOnScroll();
}

// The header slides away on the way down and returns on the way up; it stays while something inside it has focus.
// The slide is a CSS transition that only exists under prefers-reduced-motion: no-preference (static/d.css).
function hideOnScroll() {
  const head = document.querySelector("header.top");
  if (!head) return;
  let last = window.scrollY || 0;
  window.addEventListener("scroll", () => {
    const y = window.scrollY || 0;
    if (Math.abs(y - last) < 6) return;
    head.classList.toggle("is-away", y > last && y > 120);
    last = y;
  }, { passive: true });
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
}
