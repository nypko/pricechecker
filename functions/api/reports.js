// GET /api/reports?since=<ms>: reports for review, read by the weekly job (pricechecker/buyer_reports.py).
// Needs the REPORTS_ADMIN_KEY secret as a Bearer token; everyone else gets 404.
export async function onRequestGet({ request, env }) {
  const auth = request.headers.get("authorization") || "";
  if (!env.REPORTS || !env.REPORTS_ADMIN_KEY || auth !== `Bearer ${env.REPORTS_ADMIN_KEY}`) return new Response("Not found", { status: 404 });
  const since = Number(new URL(request.url).searchParams.get("since") || 0);
  const reports = [];
  let cursor;
  do {
    const page = await env.REPORTS.list({ prefix: "r:", cursor });
    for (const k of page.keys) {
      const ts = Number(k.name.split(":")[1]);
      if (ts < since) continue;
      const v = await env.REPORTS.get(k.name, "json");
      if (v) reports.push({ key: k.name.slice(2).replace(":", "-"), ...v });
    }
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  return Response.json({ reports });
}
