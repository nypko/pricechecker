// POST /api/report: one buyer's "how did your order arrive?" report, from the form on phone pages.
// Stored in Cloudflare KV (binding REPORTS) for review; nothing is published until a person approves it
// (pricechecker/buyer_reports.py). No names, emails or IP addresses are kept.
import { STORES, COUNTRIES } from "../_shared/report-allowlist.js";

const CURRENCIES = ["EUR", "GBP", "USD", "CAD", "AUD"];
const COURIERS = ["Global Priority", "EU warehouse", "DHL", "UPS", "FedEx", "Royal Mail", "USPS", "Other", ""];
const MAX_BODY = 2048;                 // a real report is ~150 bytes
const MAX_FIELD = 100;                 // longer than any value the form can send
const KEEP_SECONDS = 90 * 86400;   // KV drops a report after 90 days: the weekly job has long since collected it

export async function onRequestPost({ request, env }) {
  const html = !(request.headers.get("content-type") || "").includes("application/json");
  const bad = (status, msg) => reply(html, request, status, msg);
  if (Number(request.headers.get("content-length") || 0) > MAX_BODY) return bad(413, "That report is too long.");
  let f;
  try {
    const raw = await request.text();
    if (raw.length > MAX_BODY) return bad(413, "That report is too long.");
    f = html ? Object.fromEntries(await new Request(request.url, { method: "POST", headers: { "content-type": request.headers.get("content-type") || "" }, body: raw }).formData())
      : JSON.parse(raw);
  } catch (e) {
    return bad(400, "That didn't look like a report.");
  }
  if (!f || typeof f !== "object" || Array.isArray(f)) return bad(400, "That didn't look like a report.");
  if (f.website) return reply(html, request, 200, "ok");   // honeypot field: people never fill it in
  if (Object.values(f).some((v) => String(v).length > MAX_FIELD)) return bad(400, "Please check the store, country and days, then send again.");
  const r = {
    phone: String(f.phone || "").slice(0, 60),
    store: String(f.store || ""),
    country: String(f.country || "").toUpperCase(),
    days: f.days === "" || f.days == null ? null : Number(f.days),
    courier: String(f.courier || ""),
    tax: f.tax === "yes" ? true : f.tax === "no" ? false : null,
    amount: f.amount === "" || f.amount == null ? null : Number(f.amount),
    currency: String(f.currency || "EUR").toUpperCase(),
    ts: Date.now(),
  };
  const invalid = !/^[a-z0-9-]{0,60}$/.test(r.phone) || !STORES.includes(r.store) || !COUNTRIES.includes(r.country) ||
    (r.days != null && !(Number.isInteger(r.days) && r.days >= 1 && r.days <= 120)) || !COURIERS.includes(r.courier) ||
    (r.amount != null && !(r.amount >= 0 && r.amount <= 5000)) || !CURRENCIES.includes(r.currency) ||
    (r.days == null && r.tax == null);
  if (invalid) return bad(400, "Please check the store, country and days, then send again.");
  if (r.tax !== true) { r.amount = null; }
  if (!env.REPORTS) return bad(503, "Reports aren't switched on yet. Please try again later.");
  const key = `r:${r.ts}:${crypto.randomUUID().slice(0, 8)}`;
  try {
    await env.REPORTS.put(key, JSON.stringify(r), { expirationTtl: KEEP_SECONDS });
  } catch (e) {   // e.g. the daily KV write limit
    return bad(503, "We couldn't save that just now. Please try again later.");
  }
  return reply(html, request, 200, "ok");
}

function reply(html, request, status, msg) {
  if (!html) return Response.json({ ok: status === 200, error: status === 200 ? undefined : msg }, { status });
  // without JavaScript the form posts normally: go back to the page it came from on this site (never another site)
  const here = new URL(request.url);
  let path = "/";
  try {
    const ref = new URL(request.headers.get("referer") || "");   // absolute only: browsers send the full address
    if (ref.origin === here.origin) path = ref.pathname;
  } catch (e) { /* none, relative or malformed: the home page */ }
  const back = new URL(path, here);
  back.hash = status === 200 ? "report-thanks" : "report-error";
  return Response.redirect(back.toString(), 303);
}
