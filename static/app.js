(function () {
  var SYMBOL = { usd: "$", eur: "€", gbp: "£", aud: "A$" };
  var PAY_LABEL = { card: "card", paypal: "PayPal", bank: "bank transfer" };
  var state = { cur: "usd", pay: "card", region: "EU" };
  var TAX = {};   // config/import_tax.yaml: estimated VAT/GST per destination
  try { TAX = JSON.parse(document.getElementById("import-tax").textContent); } catch (e) {}

  function store(key, val) {
    try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); } catch (e) { return null; }
  }
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
  function pct(v) { return (v > 0 ? "+" : v < 0 ? "−" : "") + (Math.round(Math.abs(v) * 100) / 100) + "%"; }

  // Total for one offer under the current currency / payment / region, as landed cost:
  // store price +/- payment adjustment + shipping + estimated import VAT/GST when the store's price excludes it.
  // pay% unknown -> treated as 0 but flagged; shipping unknown -> excluded from total but flagged;
  // import tax not stated by the store -> shown as a possible amount but not added.
  function cost(o) {
    var c = state.cur, base = o.money[c], adj = o.pay[state.pay], ship = o.ship[state.region];
    var adjAmt = adj == null ? 0 : base * adj / 100;
    var shipAmt = ship ? ship[c] : 0;
    var duties = o.duties ? o.duties[state.region] : null, tax = TAX[state.region] || {};
    var taxEst = tax.rate_pct == null ? null : (base + adjAmt + shipAmt) * tax.rate_pct / 100;
    var taxAdded = duties === false && taxEst != null ? taxEst : 0;
    return {
      payOk: !o.pay_ok || o.pay_ok[state.pay] !== false,
      base: base, adj: adj, adjAmt: adjAmt, ship: ship ? shipAmt : null,
      taxEst: taxEst, taxAdded: taxAdded, taxName: tax.name || "import tax", taxNote: tax.note || "",
      total: base + adjAmt + shipAmt + taxAdded,
      approx: o.money[c + "_approx"] === 1 || taxAdded > 0,
      complete: adj != null && !!ship,
      duties: duties,
      payNote: o.notes.pay[state.pay], shipNote: o.notes.ship[state.region]
    };
  }

  // What the total contains or leaves out, in words, e.g. "excl. shipping · incl. ≈A$175 est. GST (paid on delivery)".
  function caveats(k) {
    var out = [];
    if (k.ship == null) out.push("excl. shipping");
    if (k.adj == null) out.push(PAY_LABEL[state.pay] + " fee unknown");
    if (k.duties === false)
      out.push(k.taxEst != null ? "incl. " + fmt(k.taxEst, true) + " est. " + k.taxName + " (paid on delivery)"
                                : k.taxName + " may apply, not included");
    else if (k.duties == null)
      out.push("import tax not stated" + (k.taxEst ? " · may add " + fmt(k.taxEst, true) + " " + k.taxName : ""));
    else if (out.length) out.push("import tax incl.");   // with nothing else to say, the caveat reads "incl. shipping & import tax"
    return out;
  }
  function caveatEl(k) {
    var c = caveats(k), el = document.createElement("span");
    el.className = "caveat";
    el.textContent = c.length ? c.join(" · ") : "incl. shipping & import tax";
    if (!c.length) el.classList.add("good");
    if (k.duties !== true && k.taxNote) setNote(el, k.taxNote);
    return el;
  }

  // Cheapest offer for the current choices; stores that don't take the chosen payment method rank last.
  function pick(offers) {
    var best = null;
    offers.forEach(function (o) {
      var k = cost(o);
      if (!best || (k.payOk && !best.k.payOk) || (k.payOk === best.k.payOk && k.total < best.k.total)) best = { o: o, k: k };
    });
    return best;
  }
  // Cheapest listed price, ignoring payment and shipping (index cards).
  function cheapest(offers) {
    var best = null, c = state.cur;
    offers.forEach(function (o) {
      if (!best || o.money[c] < best.k.total)
        best = { o: o, k: { total: o.money[c], approx: o.money[c + "_approx"] === 1, payOk: true } };
    });
    return best;
  }
  function byEdition(offers, ed) { return offers.filter(function (o) { return o.edition === ed; }); }

  // "China version $180 cheaper" at the cheapest configuration both versions are sold in.
  function gap(offers, choose) {
    var storages = {}, best = null;
    offers.forEach(function (o) { storages[o.storage] = 1; });
    Object.keys(storages).forEach(function (s) {
      var same = offers.filter(function (o) { return o.storage === s; });
      var g = choose(byEdition(same, "global")), c = choose(byEdition(same, "china"));
      if (g && c && g.k.payOk && c.k.payOk && (!best || Math.min(g.k.total, c.k.total) < best.low))
        best = { storage: s, g: g, c: c, low: Math.min(g.k.total, c.k.total) };
    });
    return best;
  }
  function gapText(d, withStorage) {
    var diff = d.c.k.total - d.g.k.total, approx = d.g.k.approx || d.c.k.approx;
    var where = withStorage && d.storage !== "base" ? " (" + d.storage.replace("/", " + ") + " GB)" : "";
    if (Math.abs(diff) < 1) return "Same price for both versions" + where;
    return (diff < 0 ? "China" : "Global") + " version " + fmt(Math.abs(diff), approx) + " cheaper" + where;
  }

  // "What's in the total?": the import tax rule for the chosen Ship-to destination
  var REGION_NAME = { EU: "the EU", UK: "the UK", US: "the US", AU: "Australia" };
  function taxText() {
    var t = TAX[state.region], where = "Shipping to " + REGION_NAME[state.region] + ": ";
    if (!t) return null;
    if (t.rate_pct == null) return where + t.note + " We don't add an estimate to totals.";
    return where + "when a store's price excludes " + t.name + ", you pay it to the courier on delivery and we add an " +
      "estimate (≈) to that store's total. " + t.note;
  }

  // Details behind a value (store terms, conversions, tax rules): shown inline on tap or Enter, since
  // hover tooltips never appear on phones. setNote(el, "") removes it.
  function setNote(el, text) {
    if (text) el.dataset.note = text; else delete el.dataset.note;
    noteable(el);
  }
  function noteable(el) {
    var on = !!el.dataset.note;
    if (on) { el.tabIndex = 0; el.setAttribute("role", "button"); el.setAttribute("aria-expanded", noteOf(el) ? "true" : "false"); }
    else { el.removeAttribute("tabindex"); el.removeAttribute("role"); el.removeAttribute("aria-expanded"); }
  }
  // the note goes right after the value (not inside it), so it doesn't inherit the value's dotted underline
  function noteOf(el) { var n = el.nextElementSibling; return n && n.classList.contains("note") ? n : null; }
  function toggleNote(el) {
    var open = noteOf(el);
    if (open) open.remove();
    else {
      var n = document.createElement("span");
      n.className = "note";
      n.textContent = el.dataset.note;
      el.after(n);
    }
    el.setAttribute("aria-expanded", open ? "false" : "true");
  }
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-note]");
    if (el && el.dataset.note && !e.target.closest("a")) toggleNote(el);
  });
  document.addEventListener("keydown", function (e) {
    var el = e.target;
    if ((e.key === "Enter" || e.key === " ") && el.dataset && el.dataset.note) { e.preventDefault(); toggleNote(el); }
  });
  document.querySelectorAll("[data-note]").forEach(noteable);
  // Links to an explainer (#editions) open it, not just scroll to its closed summary
  document.querySelectorAll("[data-open]").forEach(function (a) {
    a.addEventListener("click", function () { var d = document.getElementById(a.dataset.open); if (d) d.open = true; });
  });

  function cell(td) { td.textContent = ""; return td.appendChild(document.createElement("span")); }

  function render() {
    document.querySelectorAll(".note").forEach(function (n) { n.remove(); });   // values below are recomputed
    var tax = document.querySelector("#totals .tax-region"), tt = taxText();
    if (tax && tt) tax.textContent = tt;
    // simple price tags (store's own price or ECB conversion)
    document.querySelectorAll(".price").forEach(function (el) {
      var v = parseFloat(el.dataset[state.cur]);
      var approx = el.dataset[state.cur + "Approx"] === "1";
      if (!isNaN(v)) el.textContent = fmt(v, approx);
      setNote(el, approx ? "Converted at the European Central Bank rate: this store has no price in this currency." : "");
    });
    // index cards: the stores' own prices (no payment/shipping adjustments - those are on the phone pages)
    document.querySelectorAll(".card[data-offers]").forEach(function (card) {
      var offers = JSON.parse(card.dataset.offers), top = cheapest(offers);
      card.querySelectorAll(".ed").forEach(function (li) {
        var b = cheapest(byEdition(offers, li.dataset.ed));
        if (!b) return;
        li.querySelector(".price").textContent = fmt(b.k.total, b.k.approx);
        li.querySelector(".spec").textContent = spec(b.o.storage) || "RAM/storage not listed";
        li.querySelector(".where").textContent = "at " + b.o.store_label;
        li.classList.toggle("cheapest", b.o === top.o && card.querySelectorAll(".ed .price").length > 1);
      });
      var d = gap(offers, cheapest), el = card.querySelector(".diff");
      el.hidden = !d;
      if (d) el.textContent = gapText(d, true);
      if (top) card.querySelector(".deal").href = top.o.link;
    });
    // phone page headline
    document.querySelectorAll(".lead[data-offers]").forEach(function (lead) {
      var b = cheapest(JSON.parse(lead.dataset.offers));   // same listed price as the card on the index page
      if (!b) return;
      lead.querySelector(".price").textContent = fmt(b.k.total, b.k.approx);
      lead.querySelector(".lead-store").textContent = b.o.store_label;
      lead.querySelector(".lead-what").textContent = "(" + (b.o.edition === "china" ? "China" : "Global") + " version" +
        (b.o.storage !== "base" ? ", " + spec(b.o.storage) : "") + (b.k.payOk ? "" : "; " + PAY_LABEL[state.pay] + " not offered") + ")";
      lead.querySelector(".deal").href = b.o.link;
      var bar = document.querySelector(".sticky-deal");   // the phone-only bottom bar mirrors the best price
      if (bar) {
        bar.querySelector(".price").textContent = fmt(b.k.total, b.k.approx);
        bar.querySelector(".sd-store").textContent = "at " + b.o.store_label;
        bar.querySelector(".deal").href = b.o.link;
      }
    });
    // phone page: Global vs China table
    document.querySelectorAll(".cmp-row").forEach(function (row) {
      var picks = [];
      row.querySelectorAll(".cmp-cell").forEach(function (cell) {
        var b = pick(JSON.parse(cell.dataset.offers));
        picks.push(b);
        var badge = document.createElement("span");
        badge.className = "badge " + cell.dataset.ed;
        badge.textContent = cell.dataset.label;
        cell.innerHTML = "";
        cell.appendChild(badge);
        cell.appendChild(document.createTextNode(" "));
        if (!b) { var none = document.createElement("span"); none.className = "muted"; none.textContent = "not sold"; cell.appendChild(none); return; }
        var strong = document.createElement("strong"), at = document.createElement("span");
        strong.textContent = b.k.payOk ? fmt(b.k.total, b.k.approx) : fmt(b.o.money[state.cur], b.k.approx);
        strong.className = b.k.payOk ? "" : "muted";
        at.className = "muted small";
        at.textContent = " at " + b.o.store_label + (b.k.payOk ? "" : " · no " + PAY_LABEL[state.pay]);
        cell.appendChild(strong); cell.appendChild(at);
        if (b.k.payOk) cell.appendChild(caveatEl(b.k));
      });
      var diff = row.querySelector(".cmp-diff");
      if (picks.length === 2 && picks[0] && picks[1] && picks[0].k.payOk && picks[1].k.payOk) {
        var d = picks[1].k.total - picks[0].k.total;
        diff.textContent = Math.abs(d) < 1 ? "same" : (d < 0 ? "China " : "Global ") + fmt(Math.abs(d), picks[0].k.approx || picks[1].k.approx) + " cheaper";
        diff.className = "cmp-diff";
      } else { diff.textContent = "–"; diff.className = "cmp-diff muted"; }
    });
    // phone page rows
    document.querySelectorAll(".offer-row").forEach(function (row) {
      var k = cost(JSON.parse(row.dataset.offer));
      var p = row.querySelector(".c-pay"), s = row.querySelector(".c-ship"), t = row.querySelector(".c-total strong");
      var old = row.querySelector(".c-total .caveat");
      if (old) old.remove();
      var pv = cell(p);
      pv.textContent = !k.payOk ? "not offered" : k.adj == null ? "unknown" :
        k.adj === 0 ? (state.pay === "bank" ? "no discount" : "no fee") : pct(k.adj) + " (" + (k.adjAmt < 0 ? "−" : "+") + fmt(Math.abs(k.adjAmt), false) + ")";
      setNote(pv, k.payNote);
      p.className = "c-pay " + (!k.payOk || k.adj == null ? "muted" : k.adj < 0 ? "good" : k.adj > 0 ? "bad" : "");
      var sv = cell(s);
      sv.textContent = k.ship == null ? "not listed" : (k.ship === 0 ? "free" : fmt(k.ship, false));
      setNote(sv, k.shipNote);
      s.className = "c-ship " + (k.ship == null ? "muted" : "");
      t.textContent = k.payOk ? fmt(k.total, k.approx) : "–";
      setNote(t, !k.payOk ? "This store doesn't accept " + PAY_LABEL[state.pay] + " for this order" : "");
      if (k.payOk) row.querySelector(".c-total").appendChild(caveatEl(k));
      row._rank = [row.classList.contains("out") ? 1 : 0, k.payOk ? 0 : 1, Math.round(k.total), k.complete ? 0 : 1];
      row._payPlain = k.payOk && k.adj === 0;   // "no fee" / "no discount": nothing worth a column
    });
    // Payment column only where it explains something (a discount, a fee, "not offered", "unknown")
    document.querySelectorAll("table").forEach(function (tb) {
      var rows = tb.querySelectorAll(".offer-row");
      if (rows.length) tb.classList.toggle("no-pay", Array.prototype.every.call(rows, function (r) { return r._payPlain; }));
    });
    // cheapest total first within each table (out of stock and "payment not offered" last)
    document.querySelectorAll("tbody").forEach(function (tb) {
      var rows = Array.prototype.slice.call(tb.querySelectorAll(".offer-row"));
      if (rows.length < 2) return;
      rows.sort(function (a, b) {
        for (var i = 0; i < a._rank.length; i++) if (a._rank[i] !== b._rank[i]) return a._rank[i] - b._rank[i];
        return 0;
      }).forEach(function (r) { tb.appendChild(r); });
    });
    document.querySelectorAll(".cur button").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.cur === state.cur ? "true" : "false");
    });
  }

  function set(key, val) { state[key] = val; store("pc-" + key, val); render(); }

  document.querySelectorAll(".cur button").forEach(function (b) {
    b.addEventListener("click", function () { set("cur", b.dataset.cur); });
  });
  var pay = document.getElementById("pay"), region = document.getElementById("region");
  ["cur", "pay", "region"].forEach(function (k) { var v = store("pc-" + k); if (v) state[k] = v; });
  if (!SYMBOL[state.cur]) state.cur = "usd";
  if (pay) { pay.value = state.pay; pay.addEventListener("change", function () { set("pay", pay.value); }); }
  if (region) { region.value = state.region; region.addEventListener("change", function () { set("region", region.value); }); }
  render();

  // Brand chips + search on the index page
  // Phone pages: show the bottom "best deal" bar once the big best-price box has scrolled out of view
  var box = document.querySelector(".best-box"), bar = document.querySelector(".sticky-deal");
  if (box && bar && "IntersectionObserver" in window) {
    document.body.classList.add("has-sticky");
    new IntersectionObserver(function (entries) {
      var hidden = !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0;
      bar.classList.toggle("show", hidden);
      bar.setAttribute("aria-hidden", hidden ? "false" : "true");
      bar.querySelector(".deal").tabIndex = hidden ? 0 : -1;
    }).observe(box);
  }

  // Index page: until a brand (or All) is picked only the store terms are shown; picking one reveals the
  // phone list above them. A chip can't be un-picked - there is always one active filter after the first choice.
  var brand = null, q = document.getElementById("q"), phones = document.getElementById("phones");
  if (phones) document.body.classList.add("choosing");
  // Search: every word must appear in the brand + name, in any order, ignoring spaces and punctuation,
  // so "x9", "oppo x9", "x9 oppo" and "findx9" all find the Oppo Find X9 phones.
  function squash(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, ""); }
  var noResults = document.getElementById("no-results");
  function filter() {
    var words = (q ? q.value : "").toLowerCase().split(/[^a-z0-9]+/).filter(Boolean).map(squash), shown = 0;
    document.querySelectorAll("#phones .card").forEach(function (c) {
      var hay = c._hay || (c._hay = squash(c.dataset.brand + " " + c.dataset.name));
      c.hidden = !((!brand || c.dataset.brand === brand) && words.every(function (w) { return hay.indexOf(w) !== -1; }));
      if (!c.hidden) shown++;
    });
    if (noResults) {
      noResults.hidden = shown > 0 || brand === null;
      noResults.querySelector(".nr-q").textContent = q ? q.value.trim() : "";
    }
  }
  function choose(b) {
    brand = b.dataset.brand;
    document.querySelectorAll(".chips .chip").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    document.body.classList.remove("choosing");
    filter();
  }
  document.querySelectorAll(".chips .chip").forEach(function (b) {
    b.addEventListener("click", function () { choose(b); });
  });
  // Typing searches every brand: a brand chosen before would otherwise hide the match without saying why
  if (q) q.addEventListener("input", function () {
    if (brand !== "" && q.value.trim()) choose(document.querySelector('.chip[data-brand=""]'));
    else filter();
  });
  var clear = document.getElementById("clear-search");
  if (clear) clear.addEventListener("click", function () { q.value = ""; filter(); q.focus(); });
})();
