// Renders the D blocks for one phone data file with static/js/blocks.js, for tests/test_blocks.py to compare with the
// Jinja macros: node render_blocks.mjs --phone <v1 file> --tax <tax file> --edition <e> --storage <st>
//   [--settings region,area,pay,cur] [--labels '{"global":..,"china":..}'] [--meta '{"id","name","announced","brand"}']
//   [--now <ISO>] [--root <prefix>]
// prints {"<snake name>": "<html>", "store_row": ["<html>", ...one per row], "ledger": [by rank, by total, by store price]}. Or --money '[[v, cur, dec], ...]' prints
// the money() text of each.
import { readFileSync } from "node:fs";
import { rows as viewRows, bestOf, gap } from "../../static/js/view.js";
import * as B from "../../static/js/blocks.js";

const arg = (n, d = null) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };

if (arg("--money")) {
  console.log(JSON.stringify(JSON.parse(arg("--money")).map(([v, c, d]) => B.money(v, c, d))));
} else {
  const doc = JSON.parse(readFileSync(arg("--phone"), "utf8"));
  const tax = JSON.parse(readFileSync(arg("--tax"), "utf8"));
  const [region, area, pay, cur] = arg("--settings", "EU,,card,eur").split(",");
  const s = { region, area, pay, cur };
  const labels = JSON.parse(arg("--labels", '{"global":"Global","china":"China"}'));
  const meta = JSON.parse(arg("--meta", "null")) || doc.meta || { id: "", name: "", announced: "", brand: "" };
  const now = arg("--now", doc.now || new Date().toISOString().replace(/\.\d+Z$/, "Z"));
  const e = arg("--edition"), st = arg("--storage"), root = arg("--root", "");
  const rows = viewRows(doc.offers, tax, s);
  const pick = rows.filter((r) => r.edition === e && r.storage === st);
  const best = bestOf(rows, e, st);
  const both = ["china", "global"].every((x) => bestOf(rows, x));
  console.log(JSON.stringify({
    price_box: B.priceBox(rows, e, s, labels, true),
    gap_line: B.gapLine(gap(rows), both, s, labels),
    mem_chips: B.memChips(rows, e, st, s),
    verdict: B.verdict(best, pick, s, labels, now),
    receipt: B.receipt(best, s, labels),
    store_row: rows.map((r) => B.storeRow(r, s, labels, now)),
    store_list: B.storeList(pick.filter((r) => r !== best), s, labels, now),
    buy_bar: B.buyBar(best, s, labels),
    home_row: B.homeRow(meta, rows, s, labels, root),
    ledger: ["rank", "total", "list"].map((k) => B.ledger(rows, s, labels, k)),
  }));
}
