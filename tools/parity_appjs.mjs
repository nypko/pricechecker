// One-off parity check: runs today's static/app.js pricing (taxRule1, cost1, maybeTax, unknowns, better) outside the browser.
// Called by tools/parity.py. stdin: one JSON job per line {id, tax, offers, settings: [[region, area, pay, cur], ...], pick}
// stdout: one JSON line per job {id, costs: [[cost per offer] per settings], pick: index of the offer app.js's better() puts
// first among `pick` (offer indexes), for the first settings entry, or null}.
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
import vm from "node:vm";

const SRC = readFileSync(new URL("../static/app.js", import.meta.url), "utf8");

// "function name(...) { ... }" by name, closed by brace matching (app.js has no braces inside strings in these functions)
function extract(name) {
  const start = SRC.search(new RegExp("function " + name + "\\s*\\("));
  if (start < 0) throw new Error("not in app.js: " + name);
  let i = SRC.indexOf("{", start), depth = 0;
  for (; i < SRC.length; i++) {
    if (SRC[i] === "{") depth++;
    else if (SRC[i] === "}" && --depth === 0) return SRC.slice(start, i + 1);
  }
  throw new Error("unbalanced: " + name);
}

const code = ["taxRule1", "cost1", "maybeTax", "unknowns", "better"].map(extract).join("\n") +
  "\nfunction taxRule() { return taxRule1(); }\n";
const ctx = vm.createContext({ state: {}, TAX: {}, EU_C: {}, CA_P: {}, fmt: (v) => String(v) });
vm.runInContext(code, ctx);

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  if (!line.trim()) continue;
  const job = JSON.parse(line);
  ctx.TAX = job.tax;   // context properties are the extracted functions' globals
  ctx.EU_C = (job.tax.EU && job.tax.EU.countries) || {};
  ctx.CA_P = (job.tax.CA && job.tax.CA.provinces) || {};
  const costs = [];
  let pick = null;
  job.settings.forEach(([region, area, pay, cur], si) => {
    ctx.state = { region, pay, cur, country: region === "EU" ? area : "", prov: region === "CA" ? area : "" };
    const ks = job.offers.map((o) => ctx.cost1(o));
    costs.push(ks.map((k) => ({
      total: k.total, unknowns: ctx.unknowns(k), payOk: k.payOk, old: k.old, approx: k.approx, complete: k.complete,
      taxAdded: k.taxAdded, taxEst: k.taxEst, ship: k.ship, promoPct: k.promoPct, adj: k.adj === undefined ? null : k.adj,
    })));
    if (si === 0 && job.pick) {
      for (const i of job.pick) if (pick === null || ctx.better(ks[i], ks[pick])) pick = i;
    }
  });
  process.stdout.write(JSON.stringify({ id: job.id, costs, pick }) + "\n");
}
