// Prints the view rows for one phone data file (--picks: the pick rules over them instead): node view_cases.mjs --phone <v1 file> --tax <tax file> --settings region,area,pay,cur
import { readFileSync } from "node:fs";
import { rows, nearestMemory, pickForMemory, defaultPick, dailyBest, priceTrend } from "../../static/js/view.js";

const arg = (n) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
if (process.argv.includes("--trend")) {   // --trend file: {days, now, today} -> priceTrend
  const t = JSON.parse(readFileSync(arg("--trend"), "utf8"));
  console.log(JSON.stringify(priceTrend(t.days, t.now, t.today)));
  process.exit(0);
}
const doc = JSON.parse(readFileSync(arg("--phone"), "utf8"));
const tax = JSON.parse(readFileSync(arg("--tax"), "utf8"));
const [region, area, pay, cur] = (arg("--settings") ?? "EU,,card,eur").split(",");
if (process.argv.includes("--daily")) {   // --daily edition,storage: the doc's trend re-priced per day
  const [ed, mem] = arg("--daily").split(",");
  console.log(JSON.stringify(dailyBest(doc.offers, doc.trend, ed, mem, tax, { region, area, pay, cur }, arg("--today"))));
  process.exit(0);
}
const rs = rows(doc.offers, tax, { region, area, pay, cur });
if (process.argv.includes("--picks")) {
  const out = { default: defaultPick(rs), nearest: {}, pick: {} };
  for (const mem of new Set(rs.map((r) => r.storage))) {
    for (const ed of ["china", "global"]) {
      out.nearest[`${ed} ${mem}`] = nearestMemory(rs, ed, mem);
      out.pick[`${ed} ${mem}`] = pickForMemory(rs, mem, ed);
    }
  }
  console.log(JSON.stringify(out));
} else console.log(JSON.stringify(rs));
