// Prints the view rows for one phone data file: node view_cases.mjs --phone <v1 file> --tax <tax file> --settings region,area,pay,cur
import { readFileSync } from "node:fs";
import { rows } from "../../static/js/view.js";

const arg = (n) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const doc = JSON.parse(readFileSync(arg("--phone"), "utf8"));
const tax = JSON.parse(readFileSync(arg("--tax"), "utf8"));
const [region, area, pay, cur] = (arg("--settings") ?? "EU,,card,eur").split(",");
console.log(JSON.stringify(rows(doc.offers, tax, { region, area, pay, cur })));
