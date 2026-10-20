// POST /api/report: one buyer's "how did your order arrive?" report, from the form on phone pages.
// Stored in Cloudflare KV (binding REPORTS) for review; nothing is published until a person approves it
// (pricechecker/buyer_reports.py). No names, emails or IP addresses are kept.
const CURRENCIES = ["EUR", "GBP", "USD", "CAD", "AUD"];
const COURIERS = ["Global Priority", "EU warehouse", "DHL", "UPS", "FedEx", "Royal Mail", "USPS", "Other", ""];

export async function onRequestPost({ request, env }) {
  const html = !(request.headers.get("content-type") || "").includes("application/json");
  let f;
  try {
    f = html ? Object.fromEntries(await request.formData()) : await request.json();
  } catch (e) {
    return reply(html, request, 400, "That didn't look like a report.");
  }
  if (!f || typeof f !== "object") return reply(html, request, 400, "That didn't look like a report.");
  if (f.website) return reply(html, request, 200, "ok");   // honeypot field: people never fill it in
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
  const bad = !/^[a-z0-9-]{0,60}$/.test(r.phone) || !/^[a-z_]{2,40}$/.test(r.store) || !/^[A-Z]{2}$/.test(r.country) ||
    (r.days != null && !(Number.isInteger(r.days) && r.days >= 1 && r.days <= 120)) || !COURIERS.includes(r.courier) ||
    (r.amount != null && !(r.amount >= 0 && r.amount <= 5000)) || !CURRENCIES.includes(r.currency) ||
    (r.days == null && r.tax == null);
  if (bad) return reply(html, request, 400, "Please check the store, country and days, then send again.");
  if (r.tax !== true) { r.amount = null; }
  if (!env.REPORTS) return reply(html, request, 503, "Reports aren't switched on yet. Please try again later.");
  const key = `r:${r.ts}:${crypto.randomUUID().slice(0, 8)}`;
  await env.REPORTS.put(key, JSON.stringify(r));
  return reply(html, request, 200, "ok");
}

function reply(html, request, status, msg) {
  if (!html) return Response.json({ ok: status === 200, error: status === 200 ? undefined : msg }, { status });
  // without JavaScript the form posts normally: go back to the page, which shows the outcome
  const back = new URL(request.headers.get("referer") || "/", request.url);
  back.hash = status === 200 ? "report-thanks" : "report-error";
  return Response.redirect(back.toString(), 303);
}
