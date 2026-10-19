(function () {
  var SYMBOL = { usd: "$", eur: "€", gbp: "£", aud: "A$" };
  var PAY_LABEL = { card: "card", paypal: "PayPal", bank: "bank transfer" };
  var PAY_SHORT = { card: "Card", paypal: "PayPal", bank: "Bank" };
  var REGION_NAME = { EU: "the EU", UK: "the UK", US: "the US", AU: "Australia" };
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

  // First visit: currency and Ship-to from the visitor's time zone (then their own choice, saved on the device)
  function guess() {
    var tz = "", lang = (navigator.language || "").toLowerCase();
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    if (tz === "Europe/London" || /-gb$/.test(lang)) return { region: "UK", cur: "gbp" };
    if (/^Australia\//.test(tz) || /-au$/.test(lang)) return { region: "AU", cur: "aud" };
    if (/^Europe\//.test(tz)) return { region: "EU", cur: "eur" };
    if (/^America\//.test(tz) || /-us$/.test(lang)) return { region: "US", cur: "usd" };
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
  // A total the store's shipping isn't in reads "$1,149 + shipping", never as if it were everything
  function totalText(k) { return fmt(k.total, k.approx) + (k.ship == null ? " + shipping" : ""); }

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
  // Cheapest listed price, ignoring payment and shipping (index cards, labelled "listed prices").
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

  // phone page: show one version's rows, or both
  var edShown = "";

  function render() {
    document.querySelectorAll(".note").forEach(function (n) { n.remove(); });   // values below are recomputed
    // settings summary: header button, sticky bar, "Totals for ..." line, panel buttons
    var summary = state.region + " · " + SYMBOL[state.cur] + " · " + PAY_SHORT[state.pay];
    document.querySelectorAll(".prefs-summary").forEach(function (el) { el.textContent = summary; });
    document.querySelectorAll(".for-region").forEach(function (el) { el.textContent = REGION_NAME[state.region]; });
    document.querySelectorAll(".for-pay").forEach(function (el) { el.textContent = PAY_LABEL[state.pay]; });
    document.querySelectorAll(".seg[data-pref] button").forEach(function (b) {
      b.setAttribute("aria-pressed", state[b.parentNode.dataset.pref] === b.dataset.val ? "true" : "false");
    });
    var tax = document.querySelector("#totals .tax-region"), tt = taxText();
    if (tax && tt) tax.textContent = tt;
    // simple price tags (store's own price or ECB conversion)
    document.querySelectorAll(".price").forEach(function (el) {
      var v = parseFloat(el.dataset[state.cur]);
      var approx = el.dataset[state.cur + "Approx"] === "1";
      if (!isNaN(v)) el.textContent = fmt(v, approx);
      setNote(el, approx ? "Converted at the European Central Bank rate: this store has no price in this currency." : "");
    });
    // index cards: the stores' listed prices (payment/shipping/tax are on the phone pages)
    var gaps = [];
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
      if (d) {
        el.textContent = gapText(d, true);
        gaps.push({ d: d, abs: Math.abs(d.c.k.total - d.g.k.total), name: card.querySelector(".name").textContent, slug: card.dataset.slug });
      }
      if (top) card.querySelector(".deal").href = top.o.link;
    });
    // index, before a brand is picked: the three biggest Global vs China gaps
    var gl = document.querySelector(".gap-list");
    if (gl) {
      gl.textContent = "";
      gaps.sort(function (a, b) { return b.abs - a.abs; }).slice(0, 3).forEach(function (x) {
        var li = document.createElement("li"), a = document.createElement("a"), t = document.createElement("span");
        a.href = "phones/" + x.slug; a.textContent = x.name;
        t.className = "gap-text"; t.textContent = gapText(x.d, true);
        li.appendChild(a); li.appendChild(t); gl.appendChild(li);
      });
      gl.parentNode.dataset.has = gaps.length ? "1" : "";
    }
    // phone page headline + bottom bar: cheapest TOTAL for the chosen region and payment, same as the first row below
    document.querySelectorAll(".lead[data-offers]").forEach(function (lead) {
      var b = pick(JSON.parse(lead.dataset.offers));
      if (!b) return;
      lead.querySelector(".lead-price .price").textContent = fmt(b.k.total, b.k.approx);
      lead.querySelector(".lead-price .plus").textContent = b.k.ship == null ? "+ shipping" : "";
      setNote(lead.querySelector(".lead-price .price"), "");   // the caveat line under it says what the total holds
      lead.querySelector(".lead-store").textContent = b.o.store_label;
      lead.querySelector(".lead-what").textContent = "(" + (b.o.edition === "china" ? "China" : "Global") + " version" +
        (b.o.storage !== "base" ? ", " + spec(b.o.storage) : "") + (b.k.payOk ? "" : "; " + PAY_LABEL[state.pay] + " not offered") + ")";
      var cv = lead.querySelector(".lead-caveat");
      cv.textContent = "";
      cv.appendChild(caveatEl(b.k));
      lead.querySelector(".deal").href = b.o.link;
      var bar = document.querySelector(".sticky-deal");
      if (bar) {
        bar.querySelector(".price").textContent = fmt(b.k.total, b.k.approx);
        bar.querySelector(".sd-store").textContent = (b.k.ship == null ? "+ shipping, " : "") + "total at " + b.o.store_label;
        bar.querySelector(".deal").href = b.o.link;
      }
    });
    // phone page: each storage tier's header shows both versions' cheapest totals and the gap
    document.querySelectorAll(".tier-eds").forEach(function (te) {
      var offers = JSON.parse(te.dataset.offers), picks = {};
      te.querySelectorAll(".tier-ed").forEach(function (sp) {
        var b = pick(byEdition(offers, sp.dataset.ed)), v = sp.querySelector(".tier-val");
        picks[sp.dataset.ed] = b;
        v.textContent = !b ? "not sold" : !b.k.payOk ? "no " + PAY_LABEL[state.pay] : totalText(b.k);
        v.className = "tier-val" + (!b || !b.k.payOk ? " muted" : "");
      });
      var gp = te.querySelector(".tier-gap"), gg = picks.global, cc = picks.china;
      if (gg && cc && gg.k.payOk && cc.k.payOk) {
        var d = cc.k.total - gg.k.total;
        gp.textContent = (Math.abs(d) < 1 ? "same price" : (d < 0 ? "China " : "Global ") + fmt(Math.abs(d), gg.k.approx || cc.k.approx) + " cheaper") +
          (gg.k.ship == null || cc.k.ship == null ? ", before shipping" : "");   // one side's total has no shipping in it
      } else gp.textContent = "";
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
      setNote(sv, k.shipNote || (k.ship == null ? "This store doesn't publish a shipping price for " + REGION_NAME[state.region] +
        "; you'll see it at checkout before paying." : ""));
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
    tiers();
  }

  // Per storage tier: only the cheapest shown row gets the solid button; out-of-stock rows fold away behind a toggle.
  function tiers() {
    document.querySelectorAll(".tier").forEach(function (sec) {
      var rows = Array.prototype.slice.call(sec.querySelectorAll(".offer-row")), first = true, oos = 0;
      var open = sec.classList.contains("show-out");
      rows.forEach(function (r) {
        var edOk = !edShown || r.dataset.ed === edShown, out = r.classList.contains("out");
        if (out && edOk) oos++;
        r.hidden = !edOk || (out && !open);
        var go = r.querySelector(".go");
        go.classList.toggle("secondary", !(first && edOk && !out));
        if (edOk && !out) first = false;
      });
      var tg = sec.querySelector(".oos-toggle");
      tg.hidden = !oos;
      tg.textContent = open ? "Hide out-of-stock" : "Show " + oos + " out of stock";
      tg.setAttribute("aria-expanded", open ? "true" : "false");
      var shown = rows.some(function (r) { return !r.hidden; });
      sec.classList.toggle("tier-empty", !shown && !oos);
    });
  }
  document.querySelectorAll(".oos-toggle").forEach(function (b) {
    b.addEventListener("click", function () { b.closest(".tier").classList.toggle("show-out"); tiers(); });
  });
  document.querySelectorAll(".ed-filter button").forEach(function (b) {
    b.addEventListener("click", function () {
      edShown = b.dataset.ed;
      document.querySelectorAll(".ed-filter button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      tiers();
    });
  });

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
    b.addEventListener("click", function () { window.scrollTo({ top: window.scrollY }); openPrefs(true); });
  });
  document.querySelectorAll(".prefs-done").forEach(function (b) {
    b.addEventListener("click", function () { openPrefs(false); toggle.focus(); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && prefs && !prefs.hidden) { openPrefs(false); toggle.focus(); }
  });
  document.querySelectorAll(".seg[data-pref] button").forEach(function (b) {
    b.addEventListener("click", function () { set(b.parentNode.dataset.pref, b.dataset.val); });
  });
  render();

  // "last update" -> "2 h ago" next to the prices
  document.querySelectorAll("time[datetime]").forEach(function (t) {
    if (!t.closest(".lead-foot, .lede")) return;
    var mins = Math.round((Date.now() - Date.parse(t.getAttribute("datetime"))) / 60000);
    if (isNaN(mins) || mins < 0) return;
    t.title = t.textContent;
    t.textContent = mins < 60 ? mins + " min ago" : mins < 48 * 60 ? Math.round(mins / 60) + " h ago" : Math.round(mins / 1440) + " days ago";
  });

  // Phone pages: show the bottom "best deal" bar once the big best-price box has scrolled out of view
  var box = document.querySelector(".best-box"), bar = document.querySelector(".sticky-deal");
  if (box && bar && "IntersectionObserver" in window) {
    document.body.classList.add("has-sticky");
    new IntersectionObserver(function (entries) {
      var hidden = !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0;
      bar.classList.toggle("show", hidden);
      bar.setAttribute("aria-hidden", hidden ? "false" : "true");
      bar.querySelectorAll("a, button").forEach(function (x) { x.tabIndex = hidden ? 0 : -1; });
    }).observe(box);
  }

  // Index page: until a brand (or All) is picked, only the biggest gaps and the (folded) store terms show.
  // Tapping the picked chip again goes back to that starting view.
  var brand = null, q = document.getElementById("q"), phones = document.getElementById("phones");
  var gapsBox = document.querySelector(".gaps");
  function choosing(on) {
    document.body.classList.toggle("choosing", on);
    if (gapsBox) gapsBox.hidden = !on || !gapsBox.dataset.has;
  }
  if (phones) choosing(true);
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
    var again = b && b.getAttribute("aria-pressed") === "true" && !(q && q.value.trim());
    brand = again ? null : b.dataset.brand;
    document.querySelectorAll(".chips .chip").forEach(function (x) { x.setAttribute("aria-pressed", !again && x === b ? "true" : "false"); });
    choosing(again);
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
  // the fade at the chip row's right edge only while there's more to scroll to
  var chips = document.querySelector(".chips");
  function chipFade() { if (chips) chips.classList.toggle("at-end", chips.scrollLeft + chips.clientWidth >= chips.scrollWidth - 4); }
  if (chips) { chips.addEventListener("scroll", chipFade, { passive: true }); window.addEventListener("resize", chipFade); chipFade(); }
})();
