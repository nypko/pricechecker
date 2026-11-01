// Prints the verdicts and summaries for a cases file (Python builds it): node carrier_cases.mjs <cases.json>
// {phones, networks, table, names} -> {verdicts: [per phone: [per network]], summaries: [per phone, per 1/3/7/11 networks]}
import { readFileSync } from "node:fs";
import { verdict, summary } from "../../static/js/carriers.js";

const { phones, networks, table, names } = JSON.parse(readFileSync(process.argv[2], "utf8"));
const verdicts = phones.map((p) => networks.map((n) => verdict(p, n, table)));
const summaries = [];
for (const p of phones) for (const k of [1, 3, 7, 11]) summaries.push(summary(p, { networks: networks.slice(0, k) }, table, names[0]));
console.log(JSON.stringify({ verdicts, summaries }));
