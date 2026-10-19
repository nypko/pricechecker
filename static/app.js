(function () {
  document.documentElement.classList.remove("no-js");
  var SYMBOL = { usd: "$", eur: "€", gbp: "£", aud: "A$" };
  var PAY_LABEL = { card: "card", paypal: "PayPal", bank: "bank transfer" };
  var PAY_SHORT = { card: "Card", paypal: "PayPal", bank: "Bank" };
  var REGION_NAME = { EU: "the EU", UK: "the UK", US: "the US", AU: "Australia", Global: "your country" };
  var ED = { global: "Global", china: "China" };
  var state = { cur: "usd", pay: "card", region: "EU" };
  var TAX = {};   // config/import_tax.yaml: estimated VAT/GST per destination
  try { TAX = JSON.parse(document.getElementById("import-tax").textContent); } catch (e) {}

  function store(key, val) {
    try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); } catch (e) { return null; }
  }
  // Watched phones, kept on this device: {slug: {k: "EU|card|eur", v: headline total when last seen}}
  function watched() { try { return JSON.parse(store("pc-watch") || "{}") || {}; } catch (e) { return {}; } }
  function setWatched(w) { store("pc-watch", JSON.stringify(w)); }
  function prefKey() { return state.region + "|" + state.pay + "|" + state.cur; }
  function fmt(v, approx) {
    return (approx ? "≈" : "") + SYMBOL[state.cur] + Math.round(v).toLocaleString("en-US");
  }
  // "12/256" -> "12 GB RAM · 256 GB storage" (same as spec() in site.py)
  function spec(storage) {
    var p = (storage || "").split("/");
    if (p.length !== 2) return "";
    var rom = +p[1];
    return p[0] + " GB RAM · " + (rom >= 1024 && rom % 1024 === 0 ? rom / 1024 + " TB" : rom + " GB") + " storage";
  }
  // "16/1024" -> "16 + 1 TB" (short form for one-line labels)
  function short(storage) {
    var p = (storage || "").split("/");
    if (p.length !== 2) return "";
    var rom = +p[1];
    return p[0] + " + " + (rom >= 1024 && rom % 1024 === 0 ? rom / 1024 + " TB" : rom + " GB");
  }
  function pct(v) { return (v > 0 ? "+" : v < 0 ? "−" : "") + (Math.round(Math.abs(v) * 100) / 100) + "%"; }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // First visit: Ship-to and currency from the device's time zone, worked out here in the browser (no IP lookup, nothing
  // sent anywhere); the browser language only when there is no time zone. Then the visitor's own choice, saved on the device.
  var EU_TZ = /^(Europe\/(Amsterdam|Athens|Berlin|Bratislava|Brussels|Bucharest|Budapest|Copenhagen|Dublin|Helsinki|Lisbon|Ljubljana|Luxembourg|Madrid|Malta|Mariehamn|Nicosia|Paris|Prague|Riga|Rome|Sofia|Stockholm|Tallinn|Vienna|Vilnius|Warsaw|Zagreb)|Asia\/(Nicosia|Famagusta)|Atlantic\/(Madeira|Azores))$/;
  var US_TZ = /^(America\/(New_York|Chicago|Denver|Los_Angeles|Phoenix|Anchorage|Juneau|Sitka|Nome|Yakutat|Metlakatla|Adak|Detroit|Boise|Menominee|Indiana\/.+|Kentucky\/.+|North_Dakota\/.+)|Pacific\/Honolulu)$/;
  function guess() {
    var tz = "", lang = (navigator.language || "").toLowerCase();
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    if (tz && !/^(UTC|Etc\/)/.test(tz)) {
      if (tz === "Europe/London") return { region: "UK", cur: "gbp" };
      if (/^Australia\//.test(tz)) return { region: "AU", cur: "aud" };
      if (EU_TZ.test(tz)) return { region: "EU", cur: "eur" };
      if (US_TZ.test(tz)) return { region: "US", cur: "usd" };
      return { region: "Global", cur: "usd" };
    }
    if (/-gb$/.test(lang)) return { region: "UK", cur: "gbp" };
    if (/-au$/.test(lang)) return { region: "AU", cur: "aud" };
    return {};
  }
  var g = guess();
  ["cur", "pay", "region"].forEach(function (k) { var v = store("pc-" + k) || g[k]; if (v) state[k] = v; });
  if (!SYMBOL[state.cur]) state.cur = "usd";
  if (!PAY_LABEL[state.pay]) state.pay = "card";
  if (!REGION_NAME[state.region]) state.region = "EU";

  // Total for one offer under the current currency / payment / region, as landed cost:
  // store price +/- payment adjustment + shipping + estimated import VAT/GST when the store's price excludes it.
  // pay% unknown -> treated as 0 but flagged; shipping unknown -> excluded from total but flagged;
  // import tax not stated by the store -> shown as a possible amount but not added.
  function cost(o) {
    var c = state.cur, list = o.money[c], adj = o.pay[state.pay], ship = o.ship[state.region];
    // store-wide automatic discount (e.g. a summer sale); with bank transfer only the larger discount counts unless they combine
    var pr = o.promo, promoPct = !pr ? 0 : (state.pay === "bank" && adj != null && adj < 0 && !pr.stacks_with_bank) ?
      (-adj >= pr.pct ? 0 : pr.pct) : pr.pct;
    if (promoPct && state.pay === "bank" && adj != null && adj < 0 && !pr.stacks_with_bank) adj = 0;
    var promoAmt = list * promoPct / 100, base = list - promoAmt;
    var adjAmt = adj == null ? 0 : base * adj / 100;
    var shipAmt = ship ? ship[c] : 0;
    var duties = o.duties ? o.duties[state.region] : null, tax = TAX[state.region] || {};
    var taxEst = tax.rate_pct == null ? null : (base + adjAmt + shipAmt) * tax.rate_pct / 100;
    var taxAdded = duties === false && taxEst != null ? taxEst : 0;
    return {
      payOk: !o.pay_ok || o.pay_ok[state.pay] !== false,
      list: list, promoAmt: promoAmt, promoPct: promoPct, promoLabel: pr ? pr.label : "", promoNote: pr ? pr.note : "",
      base: base, baseApprox: o.money[c + "_approx"] === 1, adj: adj, adjAmt: adjAmt, ship: ship ? shipAmt : null,
      taxEst: taxEst, taxAdded: taxAdded, taxName: tax.name || "import tax", taxNote: tax.note || "",
      total: base + adjAmt + shipAmt + taxAdded,
      approx: o.money[c + "_approx"] === 1 || taxAdded > 0 || !!(ship && ship.min),
      shipMin: !!(ship && ship.min),   // the store publishes only a starting price ("from EUR 10")
      complete: adj != null && !!ship,
      duties: duties,
      payNote: o.notes ? o.notes.pay[state.pay] : "", shipNote: o.notes ? o.notes.ship[state.region] : ""   // index offers carry no notes
    };
  }

  // What the total contains or leaves out, in words, e.g. "excl. shipping · incl. ≈A$175 est. GST".
  function caveats(k) {
    var out = [];
    if (k.ship == null) out.push("excl. shipping");
    else if (k.shipMin) out.push("shipping from " + fmt(k.ship));
    if (k.adj == null) out.push(PAY_LABEL[state.pay] + " fee unknown");
    if (k.duties === false)
      out.push(k.taxEst != null ? "incl. " + fmt(k.taxEst, true) + " est. " + k.taxName : k.taxName + " may apply, not included");
    else if (k.duties == null)
      out.push("import tax not stated" + (k.taxEst ? " · may add " + fmt(k.taxEst, true) : ""));
    else if (out.length) out.push("import tax incl.");
    return out.length ? out.join(" · ") : "incl. shipping & import tax";
  }

  // What a total leaves out: shipping the store doesn't list, import tax that may still be due
  function maybeTax(k) { return k.duties !== true && !k.taxAdded; }
  function extras(k, long) {
    var x = [];
    if (k.ship == null) x.push("shipping");
    if (maybeTax(k)) x.push(long ? (k.taxEst ? "up to " + fmt(k.taxEst, true) + " import tax" : "import tax") : "tax?");
    return x.length ? "+ " + x.join(long ? " and " : ", ") : "";
  }
  function partial(k) { return k.ship == null || maybeTax(k); }
  // "≈£301 less", "before shipping" / "before tax" when either side's total leaves something out
  function gapNote(a, b) {
    var x = [];
    if (a.ship == null || b.ship == null) x.push("shipping");
    if (maybeTax(a) || maybeTax(b)) x.push("tax");
    return x.length ? " before " + x.join(" and ") : "";
  }

  // Cheapest offer for the current choices. Stores that don't take the chosen payment method rank last, and a total we can
  // fully work out leads over a lower one that leaves shipping or import tax open (that one is shown as "or €X + shipping").
  function better(k, b) {
    if (k.payOk !== b.payOk) return k.payOk;
    if (partial(k) !== partial(b)) return !partial(k);
    return k.total < b.total;
  }
  // The cheapest total that leaves something open, when it's lower than the complete one that leads
  function lowerOpen(offers, best) {
    var low = null;
    offers.forEach(function (o) {
      var k = cost(o);
      if (k.payOk && partial(k) && k.total < best.k.total && (!low || k.total < low.k.total)) low = { o: o, k: k };
    });
    return best && !partial(best.k) ? low : null;
  }
  // "Arrives in 12–19 working days" / "up to 8 working days" from the store's terms for the chosen Ship-to
  function delivery(o) {
    var d = o.days && o.days[state.region];
    if (!d) return "";
    return d[0] == null ? "up to " + d[1] + " working days" : d[0] + "–" + d[1] + " working days";
  }
  // "★ 4.7 on Trustpilot (11,216 reviews) · 12-month warranty · 7-day returns", from stores.yaml (entered by hand, dated)
  function trustText(o) {
    var t = o.trust;
    if (!t) return "";
    var x = [];
    if (t.reviews) x.push("★ " + t.reviews.score.toFixed(1) + " on " + t.reviews.source + " (" + t.reviews.count.toLocaleString("en-US") + " reviews)");
    if (t.warranty_months) x.push(t.warranty_months + "-month store warranty");
    if (t.returns_days) x.push(t.returns_days + "-day returns");
    return x.join(" · ");
  }
  // Approved buyer reports for the chosen Ship-to: "12 buyers to the EU: 8–21 days (typically 11) · 3 of 10 paid import tax"
  function buyersText(o) {
    var b = o.buyers && o.buyers[state.region];
    if (!b || !b.n) return "";
    var x = [];
    if (b.nd) x.push((b.dmin === b.dmax ? b.dmin : b.dmin + "–" + b.dmax) + " days" + (b.nd > 2 ? " (typically " + b.dmed + ")" : ""));
    if (b.tk) x.push(b.tx + " of " + b.tk + " paid import tax");
    return x.length ? b.n + (b.n === 1 ? " buyer" : " buyers") + " to " + REGION_NAME[state.region] + ": " + x.join(" · ") : "";
  }
  // Price movement from the hourly history: "↓ €40 this week" / "↓ €40 since 16 Oct" / "Lowest in 30 days"
  function trendText(o, k) {
    var t = o.trend;
    if (!t) return "";
    if (t.drop) {
      var amt = k.list * t.drop;
      if (amt >= 1) return "↓ " + fmt(amt, k.baseApprox) + (t.since ? " since " + new Date(t.since + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : " this week");
    }
    return t.low30 ? "Lowest in 30 days" : "";
  }
  function pick(offers) {
    var best = null;
    offers.forEach(function (o) { var k = cost(o); if (!best || better(k, best.k)) best = { o: o, k: k }; });
    return best;
  }
  function byEdition(offers, ed) { return offers.filter(function (o) { return o.edition === ed; }); }
  function at(offers, s) { return offers.filter(function (o) { return o.storage === s; }); }

  // Global vs China like for like: the cheapest RAM/storage both are sold in, or else the closest pair
  // (e.g. Global 12/512 vs China 16/512, labelled as such).
  function size(s) { var p = (s || "").split("/"); return p.length === 2 ? { ram: +p[0], rom: +p[1] } : null; }
  function distance(a, b) {
    var x = size(a), y = size(b);
    if (!x || !y) return 99;
    return Math.abs(Math.log(x.rom / y.rom) / Math.LN2) * 2 + Math.abs(x.ram - y.ram) / 4;
  }
  function match(offers) {
    offers = offers.filter(function (o) { return o.available !== false; });
    var G = byEdition(offers, "global"), C = byEdition(offers, "china"), best = null;
    if (!G.length || !C.length) return null;
    var gs = {}, cs = {};
    G.forEach(function (o) { gs[o.storage] = 1; });
    C.forEach(function (o) { cs[o.storage] = 1; });
    Object.keys(gs).forEach(function (a) {
      Object.keys(cs).forEach(function (b) {
        var gg = pick(at(G, a)), cc = pick(at(C, b));
        if (!gg.k.payOk || !cc.k.payOk) return;
        var dist = a === b ? 0 : distance(a, b), low = Math.min(gg.k.total, cc.k.total);
        if (!best || dist < best.dist || (dist === best.dist && low < best.low)) best = { g: gg, c: cc, dist: dist, low: low, same: a === b };
      });
    });
    return best;
  }

  // "What's in the total?": the import tax rule for the chosen Ship-to destination
  function taxText() {
    var t = TAX[state.region], where = "Shipping to " + REGION_NAME[state.region] + ": ";
    if (!t) return null;
    if (t.rate_pct == null) return where + t.note + " We don't add an estimate to totals.";
    return where + "when a store's price excludes " + t.name + ", you pay it to the courier on delivery and we add an " +
      "estimate (≈) to that store's total. " + t.note;
  }

  // Details behind a value (store terms, conversions, tax rules): shown inline on tap or Enter, since
  // hover tooltips never appear on phones. setNote(el, "") removes it.
  function setNote(e, text) {
    if (text) e.dataset.note = text; else delete e.dataset.note;
    noteable(e);
  }
  function noteable(e) {
    if (e.dataset.note) { e.tabIndex = 0; e.setAttribute("role", "button"); e.setAttribute("aria-expanded", noteOf(e) ? "true" : "false"); }
    else { e.removeAttribute("tabindex"); e.removeAttribute("role"); e.removeAttribute("aria-expanded"); }
  }
  // the note goes right after the value (not inside it), so it doesn't inherit the value's dotted underline
  function noteOf(e) { var n = e.nextElementSibling; return n && n.classList.contains("note") ? n : null; }
  function toggleNote(e) {
    var open = noteOf(e);
    if (open) open.remove(); else e.after(el("span", "note", e.dataset.note));
    e.setAttribute("aria-expanded", open ? "false" : "true");
  }
  document.addEventListener("click", function (ev) {
    var e = ev.target.closest("[data-note]");
    if (e && e.dataset.note && !ev.target.closest("a")) { ev.preventDefault(); toggleNote(e); }
  });
  document.addEventListener("keydown", function (ev) {
    var e = ev.target;
    if ((ev.key === "Enter" || ev.key === " ") && e.dataset && e.dataset.note) { ev.preventDefault(); toggleNote(e); }
  });
  document.querySelectorAll("[data-note]").forEach(noteable);
  // Links to an explainer (#editions) open it, not just scroll to its closed summary
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest("[data-open]");
    if (a) { var d = document.getElementById(a.dataset.open); if (d) d.open = true; }
  });

  // ---------- phone page: price grid -> one answer -> other stores ----------
  var OFFERS = null, sel = null;
  try { OFFERS = JSON.parse(document.getElementById("offers").textContent); } catch (e) {}
  var layout = document.querySelector(".ph-layout");
  var BRAND = layout ? layout.dataset.brand : "";
  (function () {   // shared links keep the chosen cell: #16-512-china
    var m = /^#(\d+)-(\d+)-(global|china)$/.exec(location.hash);
    if (m) sel = { storage: m[1] + "/" + m[2], ed: m[3] };
  })();
  function inStock(storage, ed) {
    return OFFERS.filter(function (o) { return o.available && o.storage === storage && o.edition === ed; });
  }

  // The answer's cost, part by part: what the bar shows and the list under it spells out
  function parts(k) {
    var p = [];
    p.push({ cls: "s-phone", label: "Phone", v: k.base + Math.min(k.adjAmt, 0), text: fmt(k.list, k.baseApprox) });
    if (k.promoAmt) p.push({ cls: "s-save", label: k.promoLabel, v: 0, text: "−" + fmt(k.promoAmt, k.baseApprox) + " (" + pct(-k.promoPct) + ")", good: true, note: k.promoNote });
    if (!k.payOk) { p.push({ cls: "s-fee", label: "Paying by " + PAY_LABEL[state.pay], v: 0, text: "not accepted for this order", muted: true, note: k.payNote }); return p; }
    if (k.adj == null) p.push({ cls: "s-fee", label: PAY_SHORT[state.pay] + " fee", v: 0, text: "unknown", muted: true, note: k.payNote });
    else if (k.adjAmt > 0) p.push({ cls: "s-fee", label: PAY_SHORT[state.pay] + " fee", v: k.adjAmt, text: "+" + fmt(k.adjAmt) + " (" + pct(k.adj) + ")", note: k.payNote });
    else if (k.adjAmt < 0) p.push({ cls: "s-save", label: PAY_SHORT[state.pay] + " discount", v: 0, text: "−" + fmt(-k.adjAmt) + " (" + pct(k.adj) + ")", good: true, note: k.payNote });
    else p.push({ cls: "s-fee", label: "Paying by " + PAY_LABEL[state.pay], v: 0, text: state.pay === "bank" ? "no discount" : "no fee", muted: true, note: k.payNote });
    if (k.ship == null) p.push({ cls: "s-ship", label: "Shipping", v: 0, text: "not listed, shown at checkout", muted: true,
                                 note: k.shipNote || "This store doesn't publish a shipping price for " + REGION_NAME[state.region] + "." });
    else p.push({ cls: "s-ship", label: "Shipping", v: k.ship, text: k.ship === 0 ? "free" : (k.shipMin ? "from " + fmt(k.ship) + ", exact at checkout" : fmt(k.ship)), note: k.shipNote });
    if (k.duties === true) p.push({ cls: "s-tax", label: "Import tax", v: 0, text: "included by the store", muted: true });
    else if (k.duties === false && k.taxEst != null) p.push({ cls: "s-tax", label: "Import tax", v: k.taxAdded, text: fmt(k.taxEst, true) + " est., paid on delivery", note: k.taxNote });
    else if (k.duties === false) p.push({ cls: "s-tax", label: "Import tax", v: 0, text: "may apply, not included", muted: true, note: k.taxNote });
    else p.push({ cls: "s-maybe", label: "Import tax", v: k.taxEst || 0, text: "not stated" + (k.taxEst ? ", may add " + fmt(k.taxEst, true) : ""), muted: true, note: k.taxNote });
    return p;
  }
  function breakdown(dl, k) {
    dl.textContent = "";
    parts(k).forEach(function (p) {
      var row = el("div", "bd-row " + p.cls), dt = el("dt", null, p.label), dd = el("dd", p.muted ? "muted" : p.good ? "good" : "");
      var span = el("span", null, p.text);
      dd.appendChild(span);
      if (p.note) setNote(span, p.note);
      row.appendChild(dt); row.appendChild(dd); dl.appendChild(row);
    });
    var tot = el("div", "bd-row bd-total");
    tot.appendChild(el("dt", null, "Total"));
    tot.appendChild(el("dd", null, k.payOk ? fmt(k.total, k.approx) + (partial(k) ? " " + extras(k, true) : "") : "not available"));
    dl.appendChild(tot);
  }
  function bar(box, k) {
    box.textContent = "";
    parts(k).forEach(function (p) {
      if (p.v > 0) { var s = el("span", "seg-part " + p.cls); s.style.flexGrow = p.v; box.appendChild(s); }
    });
  }
  function tradeoff(b) {
    var t = document.querySelector(".tradeoff");
    if (!t) return;
    var other = sel.ed === "china" ? "global" : "china", ob = pick(inStock(sel.storage, other));
    var sold = OFFERS.some(function (o) { return o.edition === other; });
    var lose = (BRAND === "huawei" ? "no Google services (true of every Huawei), " : "no Google Play, ") +
      "usually no manufacturer warranty outside China, and it may miss some 4G/5G bands";
    t.textContent = "";
    t.hidden = !b.k.payOk || (sel.ed === "global" && !(ob && ob.k.payOk));
    if (t.hidden) return;
    var text;
    if (!sold) text = "China version only. " + lose.charAt(0).toUpperCase() + lose.slice(1) + ". ";
    else if (!ob || !ob.k.payOk) text = "Only the China version is sold at this RAM/storage. It has " + lose + ". ";
    else {
      var d = ob.k.total - b.k.total;
      var lead = Math.abs(d) < 1 ? "Both versions cost about the same here" + gapNote(ob.k, b.k) + ". " :
        ED[other] + " version costs " + fmt(Math.abs(d), ob.k.approx || b.k.approx) + (d > 0 ? " more" : " less") +
        gapNote(ob.k, b.k) + " (" + fmt(ob.k.total, ob.k.approx) + "). ";   // "Global version costs ≈€215 more before shipping and tax (€1,312)."
      text = lead + (sel.ed === "china" ? "With the China version: " : "The China version has ") + lose + ". ";
    }
    t.appendChild(document.createTextNode(text));
    if (ob && ob.k.payOk) {
      var sw = el("button", "link-btn", "See " + ED[other]);
      sw.type = "button";
      sw.addEventListener("click", function () { choose({ storage: sel.storage, ed: other }); });
      t.appendChild(sw); t.appendChild(document.createTextNode(" · "));
    }
    var more = el("a", null, "What's different?");
    more.href = "#editions"; more.dataset.open = "editions";
    t.appendChild(more);
  }
  // "Code H2026: store says it saves up to 30%, until 30 Oct. Not in the total."
  function couponText(o) {
    return (o.coupons || []).map(function (c) {
      var until = c.until ? new Date(c.until + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "";
      return "Code " + c.code + ": " + c.text + (until ? ", until " + until : "") + ". Not in the total.";
    }).join(" ");
  }
  function storeRow(o, k, best) {
    var li = el("li"), d = el("details", "st"), s = el("summary");
    var name = el("span", "st-name", o.store_label);
    if (o.stale) name.appendChild(el("span", "st-stale", " · last known price"));
    if (o.trust && o.trust.reviews) name.appendChild(el("span", "st-stars", " ★ " + o.trust.reviews.score.toFixed(1)));
    s.appendChild(name);
    var tot = el("span", "st-total", !o.available ? "out of stock" : k.payOk ? fmt(k.total, k.approx) : "–");
    if (o.available && k.payOk && partial(k)) tot.appendChild(el("span", "plus", " " + extras(k)));
    s.appendChild(tot);
    s.appendChild(el("span", "st-delta", !o.available ? "" : !k.payOk ? "no " + PAY_LABEL[state.pay] :
      best ? (k.total < best.k.total ? "−" + fmt(best.k.total - k.total) + " vs best" : "+" + fmt(k.total - best.k.total) + " vs best") + gapNote(k, best.k) : ""));
    s.appendChild(el("span", "st-cav", o.available && k.payOk ? caveats(k) + (delivery(o) ? " · arrives in " + delivery(o) : "") : ""));
    d.appendChild(s);
    var body = el("div", "st-body"), dl = el("dl", "breakdown compact");
    breakdown(dl, k);
    body.appendChild(dl);
    if (couponText(o)) body.appendChild(el("p", "coupon", couponText(o)));
    if (trustText(o)) body.appendChild(el("p", "st-trust", trustText(o)));
    if (buyersText(o)) body.appendChild(el("p", "st-buyers", buyersText(o)));
    var go = el("a", "go secondary", (o.available ? "Go to " : "Check ") + o.store_label);
    go.href = o.link; go.rel = "sponsored nofollow noopener"; go.target = "_blank";
    go.appendChild(el("span", "sr-only", " (opens store site)"));
    body.appendChild(go);
    d.appendChild(body); li.appendChild(d);
    return li;
  }
  // price history: one chart block per RAM/storage, picked in the "Variant" menu above it
  var histSel = null;
  function showHist(storage) {
    document.querySelectorAll(".hist-one").forEach(function (h) { h.hidden = h.dataset.storage !== storage; });
    var m = document.getElementById("hist-var");
    if (m) m.value = storage;
    // history page: the table of changes follows the menu too
    document.querySelectorAll(".changes tbody tr[data-storage]").forEach(function (r) {
      r.hidden = storage !== "all" && r.dataset.storage !== storage;
    });
  }
  function choose(c) {
    sel = c;
    histSel = null;   // the price history follows the grid until a variant is picked in its own menu
    renderPhone();
    if (history.replaceState) history.replaceState(null, "", "#" + c.storage.replace("/", "-") + "-" + c.ed);
  }

  function renderPhone() {
    if (!OFFERS || !layout) return;
    // grid: each cell is the cheapest total for that RAM/storage + version
    var overall = null, cells = document.querySelectorAll(".cell");
    cells.forEach(function (c) {
      var b = pick(inStock(c.dataset.storage, c.dataset.ed));
      c._b = b;
      c.querySelector(".cell-v").textContent = b.k.payOk ? fmt(b.k.total, b.k.approx) : "no " + PAY_LABEL[state.pay];
      c.querySelector(".cell-sub").textContent = b.k.payOk ? extras(b.k) : "";
      c.classList.toggle("nopay", !b.k.payOk);
      if (!overall || better(b.k, overall._b.k)) overall = c;
    });
    cells.forEach(function (c) {
      c.classList.toggle("best", c === overall && overall._b.k.payOk);
      c.dataset.tag = partial(overall._b.k) ? "Lowest before " + (overall._b.k.ship == null ? "shipping" : "tax") : "Cheapest delivered";
    });
    var w = watched(), slug = layout.dataset.slug;
    if (w[slug] && overall._b.k.payOk) { w[slug] = { k: prefKey(), v: Math.round(overall._b.k.total) }; setWatched(w); }
    var payable = null;   // the cheapest cell you can actually pay for with the chosen method
    cells.forEach(function (c) { if (c._b.k.payOk && (!payable || better(c._b.k, payable._b.k))) payable = c; });
    var found = sel && Array.prototype.some.call(cells, function (c) { return c.dataset.storage === sel.storage && c.dataset.ed === sel.ed; });
    if (!found) sel = { storage: overall.dataset.storage, ed: overall.dataset.ed };
    var cur = null;
    cells.forEach(function (c) {
      var on = c.dataset.storage === sel.storage && c.dataset.ed === sel.ed;
      c.setAttribute("aria-pressed", on ? "true" : "false");
      if (on) cur = c;
    });
    // the answer
    var b = cur._b, ans = document.querySelector(".answer");
    var label = ans.querySelector(".ans-label");
    label.textContent = !b.k.payOk ? "Not available paying by " + PAY_LABEL[state.pay] :
      cur === overall ? (partial(b.k) ? "Lowest delivered price we can work out" : "Cheapest delivered price") : "Cheapest for this choice";
    label.classList.toggle("warn", !b.k.payOk);
    ans.classList.toggle("nopay", !b.k.payOk);
    var v = ans.querySelector(".ans-v .price");
    v.textContent = b.k.payOk ? fmt(b.k.total, b.k.approx) : "–";
    setNote(v, "");
    ans.querySelector(".ans-plus").textContent = b.k.payOk ? extras(b.k, true) : "";
    // a lower total that leaves shipping or import tax open (it's in "Other stores" below), named so it doesn't seem missing
    var low = b.k.payOk ? lowerOpen(inStock(sel.storage, sel.ed), b) : null, aor = ans.querySelector(".ans-or");
    aor.textContent = low ? "or " + fmt(low.k.total, low.k.approx) + " " + extras(low.k, true) + " at " + low.o.store_label : "";
    aor.hidden = !low;
    var alt = ans.querySelector(".ans-alt");
    alt.textContent = "";
    alt.hidden = b.k.payOk || !payable;
    if (!b.k.payOk && payable) {
      var go2 = el("button", "link-btn", "Cheapest you can pay by " + PAY_LABEL[state.pay] + ": " + fmt(payable._b.k.total, payable._b.k.approx) +
        " (" + ED[payable.dataset.ed] + ", " + (spec(payable.dataset.storage) || "RAM/storage not listed") + ")");
      go2.type = "button";
      go2.addEventListener("click", function () { choose({ storage: payable.dataset.storage, ed: payable.dataset.ed }); });
      alt.appendChild(go2);
    }
    var badge = ans.querySelector(".ans-ed");
    badge.className = "ans-ed badge " + b.o.edition; badge.textContent = ED[b.o.edition];
    ans.querySelector(".ans-spec").textContent = spec(b.o.storage) || "RAM/storage not listed";
    ans.querySelector(".ans-store").textContent = b.o.store_label + (b.o.stale ? " (last known price)" : "");
    var dv = ans.querySelector(".ans-days");
    dv.textContent = b.k.payOk && delivery(b.o) ? "Arrives in " + delivery(b.o) + " after you order" : "";
    dv.hidden = !dv.textContent;
    var at = ans.querySelector(".ans-trust");
    at.textContent = trustText(b.o);   // right under the store name, so it needs no name of its own
    at.hidden = !at.textContent;
    var ab = ans.querySelector(".ans-buyers");
    ab.textContent = buyersText(b.o);
    ab.hidden = !ab.textContent;
    var rs = document.getElementById("rf-store");
    if (rs && !rs.dataset.touched) rs.value = b.o.store;   // the report form starts on the store shown
    var tr = ans.querySelector(".ans-trend");
    tr.textContent = b.k.payOk ? trendText(b.o, b.k) : "";
    tr.hidden = !tr.textContent;
    bar(ans.querySelector(".bar"), b.k);
    breakdown(ans.querySelector(".breakdown"), b.k);
    tradeoff(b);
    var cp = ans.querySelector(".ans-coupon");
    cp.textContent = couponText(b.o);
    cp.hidden = !cp.textContent;
    var deal = ans.querySelector(".deal");
    deal.href = b.o.link;
    deal.className = b.k.payOk ? "deal" : "btn-quiet deal-off";
    deal.querySelector(".deal-t").textContent = b.k.payOk ? "View deal at " + b.o.store_label : "See " + b.o.store_label + "'s payment options";
    ans.classList.remove("settle"); void ans.offsetWidth; ans.classList.add("settle");   // a short settle when the answer changes
    // the other stores for the same choice, cheapest first
    var others = OFFERS.filter(function (o) { return o.storage === sel.storage && o.edition === sel.ed && o !== b.o; });
    var live = others.filter(function (o) { return o.available; }).map(function (o) { return { o: o, k: cost(o) }; });
    live.sort(function (x, y) { return better(x.k, y.k) ? -1 : better(y.k, x.k) ? 1 : 0; });
    var list = document.querySelector(".others > .store-list");
    list.textContent = "";
    live.forEach(function (x) { list.appendChild(storeRow(x.o, x.k, b)); });
    document.querySelector(".others-none").hidden = live.length > 0;
    var oos = others.filter(function (o) { return !o.available; }), od = document.querySelector(".oos");
    od.hidden = !oos.length;
    od.querySelector("summary").textContent = "Out of stock at " + oos.length + " store" + (oos.length === 1 ? "" : "s");
    var ol = od.querySelector(".oos-list");
    ol.textContent = "";
    oos.forEach(function (o) { ol.appendChild(storeRow(o, cost(o), null)); });
    // price history for the chosen RAM/storage
    showHist(histSel || sel.storage);
    // phone-only bottom bar
    var sb = document.querySelector(".sticky-deal");
    if (sb) {
      sb.querySelector(".sd-price").textContent = b.k.payOk ? fmt(b.k.total, b.k.approx) + (partial(b.k) ? " " + extras(b.k) : "") : "Not available by " + PAY_LABEL[state.pay];
      sb.querySelector(".sd-store").textContent = ED[b.o.edition] + " · " + b.o.store_label;
      sb.querySelector(".deal").href = b.o.link;
    }
  }
  document.querySelectorAll(".cell").forEach(function (c) {
    c.addEventListener("click", function () { choose({ storage: c.dataset.storage, ed: c.dataset.ed }); });
  });
  // Tap or hover a price history chart: a line at that moment and each store's price then
  function readout(svg, ev) {
    var box = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    var x = (ev.clientX - box.left) / box.width * vb.width, l = +svg.dataset.l, r = +svg.dataset.r;
    var wrap = svg.parentNode, tip = wrap.querySelector(".readout"), cross = svg.querySelector(".cross");
    if (x < l || x > r) { if (tip) tip.hidden = true; if (cross) cross.remove(); return; }
    var t0 = Date.parse(svg.dataset.t0 + "Z"), t1 = Date.parse(svg.dataset.t1 + "Z");
    var when = new Date(t0 + (x - l) / (r - l) * (t1 - t0));
    if (!tip) { tip = el("div", "readout"); tip.setAttribute("aria-live", "polite"); wrap.appendChild(tip); }
    tip.textContent = "";
    tip.appendChild(el("strong", null, when.toLocaleDateString("en-GB", { day: "numeric", month: "short" }) + ", " +
      when.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC"));
    svg.querySelectorAll("path[data-steps]").forEach(function (p) {
      if (p.closest("[hidden]") || getComputedStyle(p).display === "none") return;
      var v = null;
      p.dataset.steps.split(";").forEach(function (st) { var i = st.indexOf(":"); if (+st.slice(0, i) <= x) v = st.slice(i + 1); });
      if (!v) return;
      var row = el("span", "ro-row"), sw = el("i", "ro-sw");
      sw.style.borderColor = p.getAttribute("stroke");
      if (p.dataset.ed === "china") sw.style.borderStyle = "dashed";
      row.appendChild(sw); row.appendChild(el("span", null, p.dataset.name + " "));
      row.appendChild(el("b", null, v));
      tip.appendChild(row);
    });
    tip.hidden = false;
    tip.style.left = Math.min(Math.max(0, ev.clientX - box.left - tip.offsetWidth / 2), box.width - tip.offsetWidth) + "px";
    if (!cross) { cross = document.createElementNS("http://www.w3.org/2000/svg", "line"); cross.setAttribute("class", "cross"); svg.appendChild(cross); }
    cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("y1", 10); cross.setAttribute("y2", vb.height - 26);
  }
  document.querySelectorAll("svg.chart[data-t0]").forEach(function (svg) {
    svg.addEventListener("pointermove", function (ev) { readout(svg, ev); });
    svg.addEventListener("pointerdown", function (ev) { readout(svg, ev); });
    svg.addEventListener("pointerleave", function (ev) { if (ev.pointerType === "mouse") readout(svg, { clientX: -1e6 }); });
  });
  var wb = document.querySelector(".watch");
  function showWatch() {
    var on = !!watched()[wb.dataset.slug];
    wb.setAttribute("aria-pressed", on ? "true" : "false");
    wb.textContent = on ? "Watching" : "Watch";
    document.querySelector(".watch-note").hidden = !on;
  }
  if (wb) {
    showWatch();
    wb.addEventListener("click", function () {
      var w = watched();
      if (w[wb.dataset.slug]) delete w[wb.dataset.slug]; else w[wb.dataset.slug] = { k: "", v: 0 };
      setWatched(w);
      renderPhone();   // records today's price as the starting point
      showWatch();
    });
  }
  // Buyer report form: sent in the background; without JavaScript it posts normally and comes back with #report-thanks
  var rf = document.querySelector(".report-form");
  if (rf) {
    var status = rf.querySelector(".rf-status"), amt = rf.querySelector(".rf-amount");
    var taxNow = function () { var c = rf.querySelector("input[name=tax]:checked"); amt.hidden = !c || c.value !== "yes"; };
    rf.querySelectorAll("input[name=tax]").forEach(function (x) { x.addEventListener("change", taxNow); });
    taxNow();
    document.getElementById("rf-store").addEventListener("change", function (ev) { ev.target.dataset.touched = "1"; });
    var cc = document.getElementById("rf-country");
    if (!cc.value) cc.value = { UK: "GB", US: "US", AU: "AU" }[state.region] || "";
    rf.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var data = {};
      new FormData(rf).forEach(function (v, k) { data[k] = v; });
      if (!data.days && !data.tax) { status.className = "rf-status err"; status.textContent = "Add the days or whether you paid import tax."; return; }
      status.className = "rf-status"; status.textContent = "Sending…";
      fetch(rf.getAttribute("action"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok && j.ok, j: j }; }); })
        .then(function (x) {
          status.className = "rf-status " + (x.ok ? "ok" : "err");
          status.textContent = x.ok ? "Thanks! We check each report before it counts." : (x.j.error || "Couldn't send it. Please try again.");
          if (x.ok) { rf.querySelector(".rf-send").disabled = true; }
        })
        .catch(function () { status.className = "rf-status err"; status.textContent = "Couldn't send it. Check your connection and try again."; });
    });
    if (location.hash === "#report-thanks" || location.hash === "#report-error") {
      document.querySelector(".report-box").open = true;
      status.className = "rf-status " + (location.hash === "#report-thanks" ? "ok" : "err");
      status.textContent = location.hash === "#report-thanks" ? "Thanks! We check each report before it counts." : "Please check the store, country and days, then send again.";
    }
  }
  var hv = document.getElementById("hist-var");
  if (hv) hv.addEventListener("change", function () { histSel = hv.value; showHist(histSel); });
  var ht = document.querySelector(".hist-toggle");
  if (ht) ht.addEventListener("click", function () {
    var box = document.getElementById(ht.getAttribute("aria-controls")), open = ht.getAttribute("aria-expanded") !== "true";
    ht.setAttribute("aria-expanded", open ? "true" : "false");
    box.classList.toggle("open", open);
    box.inert = !open;
  });

  // ---------- index: one row per phone, ranked ----------
  var sortBy = "date";
  var globalOnly = store("pc-global") === "1";   // "Global version only" chip on the index, remembered on this device
  var WATCH = {};
  function renderIndex() {
    var list = document.getElementById("phones");
    if (!list) return;
    WATCH = watched();
    list.querySelectorAll(".prow[data-offers]").forEach(function (row) {
      var all = row._offers || (row._offers = JSON.parse(row.dataset.offers));
      var offers = globalOnly ? byEdition(all, "global") : all;
      row._noGlobal = !offers.length;
      if (!offers.length) return;
      var b = pick(offers), m = globalOnly ? null : match(offers), low = lowerOpen(offers, b);
      var badge = row.querySelector(".prow-sub .badge");
      badge.className = "badge " + b.o.edition; badge.textContent = ED[b.o.edition];
      row.querySelector(".prow-spec").textContent = spec(b.o.storage) || "RAM/storage not listed";
      row.querySelector(".prow-store").textContent = " · " + b.o.store_label;
      var pv = row.querySelector(".prow-v .price");
      pv.textContent = fmt(b.k.total, b.k.approx);
      setNote(pv, "");
      row.querySelector(".prow-plus").textContent = partial(b.k) ? extras(b.k) : "delivered";
      row.querySelector(".prow-or").textContent = low ? "or " + fmt(low.k.total, low.k.approx) + " " + extras(low.k) + " at " + low.o.store_label : "";
      var n = {};
      offers.forEach(function (o) { n[o.store_label] = 1; });
      row.querySelector(".prow-count").textContent = " · " + Object.keys(n).length + (Object.keys(n).length === 1 ? " store" : " stores");
      var pill = row.querySelector(".prow-trend");
      pill.textContent = b.k.payOk ? trendText(b.o, b.k) : "";
      pill.hidden = !pill.textContent;
      row._drop = b.o.trend && b.o.trend.drop ? b.k.list * b.o.trend.drop : 0;
      var seen = WATCH[row.dataset.slug], wl = row.querySelector(".prow-watch"), diff = seen && seen.k === prefKey() && !globalOnly ? Math.round(b.k.total) - seen.v : 0;
      row._watched = !!seen;
      wl.hidden = !seen;
      wl.className = "pill prow-watch" + (diff > 0 ? " up" : diff < 0 ? "" : " flat");
      wl.textContent = !seen ? "" : Math.abs(diff) >= 1 ? (diff < 0 ? "↓ " : "↑ ") + fmt(Math.abs(diff)) + " since your last visit" : "Watching";
      row.querySelector(".prow-link").href = "phones/" + row.dataset.slug + "#" + b.o.storage.replace("/", "-") + "-" + b.o.edition;
      var gp = row.querySelector(".prow-gap");
      row._price = b.k.payOk ? b.k.total : Infinity;
      row._gap = -Infinity;
      gp.hidden = !m;
      if (m) {
        var d = m.g.k.total - m.c.k.total, approx = m.g.k.approx || m.c.k.approx;
        row._gap = d;
        var cfg = m.same ? (short(m.g.o.storage) ? " at " + short(m.g.o.storage) : "") : " (closest RAM/storage)";
        gp.className = "prow-gap";
        gp.textContent = Math.abs(d) < 1 ? "Same price both versions" + cfg :
          (d > 0 ? "China " : "Global ") + fmt(Math.abs(d), approx) + " less" + cfg + gapNote(m.g.k, m.c.k);
      }
    });
    sortRows();
  }
  function sortRows() {
    var list = document.getElementById("phones"), rows = Array.prototype.slice.call(list.children);
    rows.sort(function (a, b) {
      var ao = a.dataset.offers ? 0 : 1, bo = b.dataset.offers ? 0 : 1;
      if (sortBy === "date" && a.dataset.date !== b.dataset.date) return a.dataset.date < b.dataset.date ? 1 : -1;
      if (ao !== bo) return ao - bo;
      if (sortBy === "price" && a._price !== b._price) return a._price - b._price;
      if (sortBy === "gap" && a._gap !== b._gap) return b._gap - a._gap;
      if (sortBy === "drop" && a._drop !== b._drop) return b._drop - a._drop;
      return a.dataset.name < b.dataset.name ? -1 : 1;
    }).forEach(function (r) { list.appendChild(r); });
  }
  document.querySelectorAll(".sort button").forEach(function (b) {
    b.addEventListener("click", function () {
      sortBy = b.dataset.sort;
      document.querySelectorAll(".sort button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      sortRows();
    });
  });

  // ---------- everywhere ----------
  function render() {
    document.querySelectorAll(".note").forEach(function (n) { n.remove(); });   // values below are recomputed
    var summary = state.region + " · " + SYMBOL[state.cur] + " · " + PAY_SHORT[state.pay];
    document.querySelectorAll(".prefs-summary").forEach(function (e) { e.textContent = summary; });
    document.querySelectorAll(".for-region").forEach(function (e) { e.textContent = REGION_NAME[state.region]; });
    document.querySelectorAll(".for-pay").forEach(function (e) { e.textContent = PAY_LABEL[state.pay]; });
    document.querySelectorAll(".for-cur").forEach(function (e) { e.textContent = state.cur.toUpperCase(); });
    // price history charts are drawn once per currency; show the chosen one
    document.querySelectorAll(".chart-wrap[data-cur], .hstats-box[data-cur]").forEach(function (e) { e.hidden = e.dataset.cur !== state.cur; });
    document.querySelectorAll(".seg[data-pref] button").forEach(function (b) {
      b.setAttribute("aria-pressed", state[b.parentNode.dataset.pref] === b.dataset.val ? "true" : "false");
    });
    var tax = document.querySelector("#totals .tax-region"), tt = taxText();
    if (tax && tt) tax.textContent = tt;
    // plain price tags (history table, store terms, no-JS fallbacks): the store's own price or an ECB conversion
    document.querySelectorAll(".price").forEach(function (e) {
      var v = parseFloat(e.dataset[state.cur]), approx = e.dataset[state.cur + "Approx"] === "1";
      if (!isNaN(v)) e.textContent = fmt(v, approx);
      setNote(e, approx ? "Converted at the European Central Bank rate: this store has no price in this currency." : "");
    });
    renderIndex();
    renderPhone();
  }

  function set(key, val) { state[key] = val; store("pc-" + key, val); render(); }

  // Settings panel under the header: Ship to, currency, payment in one place, reachable from anywhere on the page
  var prefs = document.getElementById("prefs"), toggle = document.querySelector(".prefs-toggle");
  function openPrefs(on) {
    if (!prefs) return;
    prefs.hidden = !on;
    toggle.setAttribute("aria-expanded", on ? "true" : "false");
    if (on) { var p = prefs.querySelector('[aria-pressed="true"]') || prefs.querySelector("button"); p.focus({ preventScroll: true }); }
  }
  if (toggle) toggle.addEventListener("click", function () { openPrefs(prefs.hidden); });
  document.querySelectorAll("[data-prefs]").forEach(function (b) {
    b.addEventListener("click", function () { openPrefs(true); });
  });
  document.querySelectorAll(".prefs-done").forEach(function (b) {
    b.addEventListener("click", function () { openPrefs(false); toggle.focus(); });
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && prefs && !prefs.hidden) { openPrefs(false); toggle.focus(); }
  });
  document.querySelectorAll(".seg[data-pref] button").forEach(function (b) {
    b.addEventListener("click", function () { set(b.parentNode.dataset.pref, b.dataset.val); });
  });
  render();

  // "last update" -> "2 h ago" next to the prices
  document.querySelectorAll(".ans-foot time, .lede time").forEach(function (t) {
    var mins = Math.round((Date.now() - Date.parse(t.getAttribute("datetime"))) / 60000);
    if (isNaN(mins) || mins < 0) return;
    t.title = t.textContent;
    t.textContent = mins < 60 ? mins + " min ago" : mins < 48 * 60 ? Math.round(mins / 60) + " h ago" : Math.round(mins / 1440) + " days ago";
  });

  // Phone pages: show the bottom "deal" bar once the answer's button has scrolled out of view
  var dealBtn = document.querySelector(".answer .deal"), sbar = document.querySelector(".sticky-deal");
  if (dealBtn && sbar && "IntersectionObserver" in window) {
    document.body.classList.add("has-sticky");
    new IntersectionObserver(function (entries) {
      var e = entries[0], hidden = e.intersectionRatio < 1 && e.boundingClientRect.top < 64;   // partly under the header or above it
      sbar.classList.toggle("show", hidden);
      sbar.setAttribute("aria-hidden", hidden ? "false" : "true");
      sbar.querySelectorAll("a, button").forEach(function (x) { x.tabIndex = hidden ? 0 : -1; });
    }, { rootMargin: "-64px 0px 0px 0px", threshold: [0, 1] }).observe(dealBtn);   // the sticky header's area counts as off screen
  }

  // Index: search + brand filter over the ranked list
  var brand = "", q = document.getElementById("q");
  function squash(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, ""); }
  var noResults = document.getElementById("no-results"), count = document.querySelector(".list-meta .count");
  function filter() {
    var words = (q ? q.value : "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).map(squash), shown = 0;
    document.querySelectorAll("#phones .prow").forEach(function (c) {
      var hay = c._hay || (c._hay = squash(c.dataset.brand + " " + c.dataset.name));
      c.hidden = !((!brand || c.dataset.brand === brand) && !(globalOnly && (c._noGlobal || !c.dataset.offers)) && !(watchOnly && !c._watched) &&
                   words.every(function (w) { return hay.indexOf(w) !== -1; }));
      if (!c.hidden) shown++;
    });
    if (count) count.textContent = shown;
    if (noResults) {
      noResults.hidden = shown > 0;
      noResults.querySelector(".nr-q").textContent = q ? q.value.trim() : "";
    }
  }
  function chooseBrand(b) {
    brand = b.dataset.brand;
    document.querySelectorAll(".chips .chip").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    filter();
  }
  document.querySelectorAll(".chips .chip").forEach(function (b) {
    b.addEventListener("click", function () { chooseBrand(b); });
  });
  // Typing searches every brand: a brand chosen before would otherwise hide the match without saying why
  if (q) q.addEventListener("input", function () {
    if (brand && q.value.trim()) chooseBrand(document.querySelector('.chip[data-brand=""]'));
    else filter();
  });
  // "Global version only": rank each phone by its Global offers and hide phones sold only as a China version
  // "Watched": only the phones watched on this device; the chip shows once there is at least one
  var watchOnly = false, wchip = document.getElementById("watch-only");
  if (wchip) {
    var nw = Object.keys(watched()).length;
    wchip.hidden = !nw;
    wchip.querySelector(".n").textContent = nw;
    wchip.addEventListener("click", function () {
      watchOnly = !watchOnly;
      wchip.setAttribute("aria-pressed", watchOnly ? "true" : "false");
      filter();
    });
  }
  var gchip = document.getElementById("global-only");
  if (gchip) {
    gchip.setAttribute("aria-pressed", globalOnly ? "true" : "false");
    gchip.addEventListener("click", function () {
      globalOnly = !globalOnly;
      store("pc-global", globalOnly ? "1" : "0");
      gchip.setAttribute("aria-pressed", globalOnly ? "true" : "false");
      renderIndex(); filter();
    });
    if (globalOnly) filter();
  }
  // Header search (every page but the list): a suggested name opens that phone; anything else opens the list, filtered
  var hs = document.querySelector(".hsearch");
  if (hs) {
    var hq = document.getElementById("hq");
    var slugFor = function (v) {
      var o = Array.prototype.find.call(document.querySelectorAll("#phone-names option"), function (x) { return x.value.toLowerCase() === v.trim().toLowerCase(); });
      return o ? o.dataset.slug : null;
    };
    var go = function (ev) {
      var slug = slugFor(hq.value);
      if (slug) { if (ev) ev.preventDefault(); location.href = hs.dataset.root + "phones/" + slug; }
    };
    hq.addEventListener("change", function () { go(); });
    hs.addEventListener("submit", go);   // no exact match: the form opens the list with ?q=...
  }
  // The list, opened from header search: ?q=... fills the search, #search puts the cursor in it
  if (q) {
    var qp = new URLSearchParams(location.search).get("q");
    if (qp) { q.value = qp; filter(); }
    if (location.hash === "#search" || qp) q.focus({ preventScroll: !!qp });
  }
  var clear = document.getElementById("clear-search");
  if (clear) clear.addEventListener("click", function () { q.value = ""; filter(); q.focus(); });
  // the fade at the chip row's right edge only while there's more to scroll to
  var chips = document.querySelector(".chips");
  function chipFade() { if (chips) chips.classList.toggle("at-end", chips.scrollLeft + chips.clientWidth >= chips.scrollWidth - 4); }
  if (chips) { chips.addEventListener("scroll", chipFade, { passive: true }); window.addEventListener("resize", chipFade); chipFade(); }
})();
