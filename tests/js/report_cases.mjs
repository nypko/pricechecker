// functions/api/report.js and reports.js (the buyer-report endpoints) against a fake KV, with Node's own Request/Response.
import assert from "node:assert/strict";
import { onRequestPost } from "../../functions/api/report.js";
import { onRequestGet } from "../../functions/api/reports.js";
import { STORES, COUNTRIES } from "../../functions/_shared/report-allowlist.js";

function kv({ failPut = false } = {}) {
  const d = new Map(), puts = [];
  return {
    d, puts,
    async put(k, v, opt) { if (failPut) throw new Error("KV put failed: limit"); puts.push([k, opt]); d.set(k, v); },
    async get(k, type) { const v = d.get(k); return v == null ? null : type === "json" ? JSON.parse(v) : v; },
    async list({ prefix, cursor }) {
      const keys = [...d.keys()].filter((k) => k.startsWith(prefix)).sort();
      const start = Number(cursor || 0), page = keys.slice(start, start + 1000);
      const done = start + 1000 >= keys.length;
      return { keys: page.map((name) => ({ name })), list_complete: done, cursor: done ? undefined : String(start + 1000) };
    },
  };
}
const SITE = "https://doorprice.app/api/report";
const form = (fields, headers = {}) => new Request(SITE, {
  method: "POST", body: new URLSearchParams(fields).toString(),
  headers: { "content-type": "application/x-www-form-urlencoded", referer: "https://doorprice.app/phones/oneplus-16", ...headers },
});
const json = (body) => new Request(SITE, { method: "POST", body: typeof body === "string" ? body : JSON.stringify(body), headers: { "content-type": "application/json" } });
const good = { phone: "oneplus-16", store: "wonda", country: "DE", days: "9", courier: "DHL", tax: "no", currency: "EUR" };

// a good report is stored with a 90-day expiry; the no-JS post goes back to the same page with #report-thanks
let env = { REPORTS: kv() };
let r = await onRequestPost({ request: form(good), env });
assert.equal(r.status, 303);
assert.equal(r.headers.get("location"), "https://doorprice.app/phones/oneplus-16#report-thanks");
assert.equal(env.REPORTS.puts.length, 1);
assert.deepEqual(env.REPORTS.puts[0][1], { expirationTtl: 90 * 86400 });
r = await onRequestPost({ request: json(good), env });
assert.equal(r.status, 200);
assert.deepEqual(await r.json(), { ok: true });

// unknown store or country, over-long fields and big bodies are refused and nothing is written
for (const bad of [{ ...good, store: "evil_store" }, { ...good, country: "QQ" }, { ...good, store: "constructor" },
                   { ...good, courier: "x".repeat(150) }, { ...good, phone: "a".repeat(101) }]) {
  const e = { REPORTS: kv() };
  const res = await onRequestPost({ request: json(bad), env: e });
  assert.equal(res.status, 400, JSON.stringify(bad).slice(0, 80));
  assert.equal(e.REPORTS.puts.length, 0);
}
const big = { REPORTS: kv() };
r = await onRequestPost({ request: json({ ...good, website: "", pad: "y".repeat(3000) }), env: big });
assert.equal(r.status, 413);
r = await onRequestPost({ request: json(JSON.stringify(good)), env: big });   // still fine after a refused one
assert.equal(r.status, 200);
r = await onRequestPost({ request: new Request(SITE, { method: "POST", body: "{}", headers: { "content-type": "application/json", "content-length": "99999" } }), env: big });
assert.equal(r.status, 413);

// a KV failure (e.g. the daily write limit) is a 503, not a crash
r = await onRequestPost({ request: json(good), env: { REPORTS: kv({ failPut: true }) } });
assert.equal(r.status, 503);

// F9: the no-JS redirect never leaves the site
for (const [referer, want] of [["https://evil.example/x?y", "https://doorprice.app/#report-error"],
                               ["https://doorprice.app/phones/a?q=1#h", "https://doorprice.app/phones/a#report-error"],
                               ["//evil.example/p", "https://doorprice.app/#report-error"],
                               ["not a url at all", "https://doorprice.app/#report-error"],
                               ["javascript:alert(1)", "https://doorprice.app/#report-error"],
                               ["", "https://doorprice.app/#report-error"]]) {
  const res = await onRequestPost({ request: form({ ...good, country: "QQ" }, { referer }), env: { REPORTS: kv() } });
  assert.equal(res.status, 303);
  assert.equal(res.headers.get("location"), want, referer);
}

// the allowlist is what the form offers
assert.ok(STORES.includes("wonda") && STORES.includes("tradingshenzhen_eu") && COUNTRIES.includes("XX"));

// GET: 404 without the key; at most 500 rows, oldest first, truncated flagged
const many = kv();
for (let i = 0; i < 620; i++) await many.put(`r:${1700000000000 + i}:abcd${String(i).padStart(4, "0")}`, JSON.stringify({ store: "wonda", ts: 1700000000000 + i }));
const get = (auth, since = 0) => new Request(`https://doorprice.app/api/reports?since=${since}`, { headers: auth ? { authorization: auth } : {} });
r = await onRequestGet({ request: get(""), env: { REPORTS: many, REPORTS_ADMIN_KEY: "k" } });
assert.equal(r.status, 404);
r = await onRequestGet({ request: get("Bearer k"), env: { REPORTS: many, REPORTS_ADMIN_KEY: "k" } });
let doc = await r.json();
assert.equal(doc.reports.length, 500);
assert.equal(doc.truncated, true);
assert.equal(doc.reports[0].ts, 1700000000000);
r = await onRequestGet({ request: get("Bearer k", 1700000000600), env: { REPORTS: many, REPORTS_ADMIN_KEY: "k" } });
doc = await r.json();
assert.equal(doc.reports.length, 20);
assert.equal(doc.truncated, false);
console.log("report ok");
