/* Shared helpers for the DoorPrice redesign mockups: the logo, number formatting, ranking as the live site does it,
   the settings sheet, the sample-phone picker and the mockup switcher. Each direction only owns its layout. */
(function () {
  var D = window.DP;
  // The Door D: IBM Plex Sans Bold's D with the door-phone cut into its counter (templates/_brand.html, unchanged)
  function mark(uid) {
    return '<svg viewBox="0 0 697 698" class="dp-d" aria-hidden="true" focusable="false"><g transform="matrix(1 0 0 -1 0 698)"><mask id="' + uid + 'm" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="0" y="0" width="697" height="698"><rect x="0" y="0" width="697" height="698" fill="white"/><rect x="245" y="151" width="196" height="396" rx="24" fill="black"/><rect x="265" y="273.6" width="156" height="253.4" rx="16" fill="white"/><rect x="411" y="306.2" width="16" height="74" rx="8" fill="white"/><rect x="303" y="185" width="80" height="16" rx="8" fill="white"/></mask><path d="M77 698H340Q409 698 466 676Q523 654 563 610.5Q603 567 625 501.5Q647 436 647 349Q647 262 625 196.5Q603 131 563 87.5Q523 44 466 22Q409 0 340 0H77Z" fill="currentColor" mask="url(#' + uid + 'm)"/><rect x="275" y="283.6" width="136" height="233.4" rx="10" class="dp-glass"/></g></svg>';
  }
  function lockup(uid) {
    return '<span class="sr-only">DoorPrice</span><span class="lockup" aria-hidden="true">' + mark(uid || "dp") + 'oor<span class="brand-b">Price</span></span>';
  }
  function eur(v, dec) {
    if (v == null) return "–";
    return "€" + v.toLocaleString("en-GB", { minimumFractionDigits: dec ? 2 : 0, maximumFractionDigits: dec ? 2 : 0 });
  }
  function storage(s) {
    var p = (s || "").split("/");
    if (p.length !== 2) return s || "";
    var st = +p[1] >= 1024 ? (p[1] / 1024) + " TB" : p[1] + " GB";
    return p[0] + " GB · " + st;
  }
  function memSort(a, b) { var x = a.split("/"), y = b.split("/"); return (+x[1] - +y[1]) || (+x[0] - +y[0]); }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function day(iso) { var d = new Date(iso); return d.getUTCDate() + " " + MON[d.getUTCMonth()]; }
  function month(iso) { var d = new Date(iso + "T00:00:00Z"); return MON[d.getUTCMonth()] + " " + d.getUTCFullYear(); }
  function stamp(iso) {
    var d = new Date(iso);
    return day(iso) + ", " + String(d.getUTCHours()).padStart(2, "0") + ":" + String(d.getUTCMinutes()).padStart(2, "0") + " UTC";
  }
  function ago(iso) {
    var h = Math.round((new Date(D.updated) - new Date(iso)) / 36e5);
    return h < 1 ? "this hour" : h + " h ago";
  }
  function trackedDays() { return Math.round((new Date(D.updated) - new Date(D.since)) / 864e5) + 1; }
  // ranking as the live site does it (site._title_price, app.js better()): fewer unknowns first - unlisted shipping
  // counts 2, import tax that may be due 1 - then the lower total; sold-out and >48 h old offers leave the list
  function rank(offers) {
    return offers.filter(function (o) { return o.available && !o.old && o.storage !== "base"; }).sort(function (a, b) {
      return (a.unknown - b.unknown) || (a.total - b.total);
    });
  }
  // what a total leaves out, in the site's own words
  function caveat(o) {
    var x = [];
    if (o.ship == null) x.push("shipping not listed");
    else if (o.shipMin) x.push("shipping from " + eur(o.ship));
    if (o.payPct == null) x.push("card fee unknown");
    if (o.duties === true) x.push("import tax paid by store");
    else if (o.duties === false) x.push("incl. ≈" + eur(o.taxAdded) + " import VAT");
    else x.push("import tax not stated, may add ≈" + eur(o.vat));
    return x.join(" · ");
  }
  function settled(o) { return o.unknown === 0; }
  // the short mark after a total that isn't settled, as on the live site
  function tail(o) { return o.ship == null && o.duties == null ? "+ shipping, tax?" : o.ship == null ? "+ shipping" : o.unknown ? "+ tax?" : ""; }
  function days(o) { return o.days ? o.days[0] + "–" + o.days[1] + " days" : "delivery time not stated"; }
  var ED = { global: "Global", china: "China" };
  // why an edition has no price: the maker doesn't sell it, or no store we check lists it (live: "not offered" / "no offers")
  function missing(p, ed) {
    return (p.made || []).indexOf(ed) < 0
      ? (ed === "china" ? p.brand + " doesn't make a China version" : "No Global version so far: " + p.brand + " sells this phone in China only")
      : "No store we check lists the " + ED[ed] + " version";
  }
  // a drop worth showing: the same listing fell at least 3% and €20 this week (the Telegram channel's rule)
  function drop(h) { var d = h.drop; return d && d.pct <= -3 && d.then - d.now >= 20 ? d : null; }
  function stores(p) { return Array.from(new Set(rank(p.offers).map(function (o) { return o.label; }))); }

  // the sample phone a phone page shows: ?p=<slug>, default the Find X9 Ultra
  function phone() {
    var q = new URLSearchParams(location.search).get("p");
    return D.phones[q] || D.phones[D.samples[0]];
  }

  // Settings sheet: where it ships, how you pay, currency. One control in the header, same on every page (live: "BG · € · Card").
  var PREFS = { region: "EU", country: "Bulgaria", pay: "card", cur: "EUR" };
  function prefsLabel() { return "EU · Card · €"; }
  function sheet() {
    if (document.getElementById("prefs-sheet")) return document.getElementById("prefs-sheet");
    var d = document.createElement("dialog");
    d.id = "prefs-sheet"; d.className = "sheet"; d.setAttribute("aria-labelledby", "prefs-h");
    function radios(name, items, on) {
      return '<div class="sheet-opts" role="radiogroup">' + items.map(function (i) {
        return '<label><input type="radio" name="' + name + '" value="' + i[0] + '"' + (i[0] === on ? " checked" : "") + '><span>' + i[1] + '</span></label>';
      }).join("") + '</div>';
    }
    d.innerHTML = '<form method="dialog"><h2 id="prefs-h">Your totals</h2>' +
      '<p class="sheet-sub">Every price on DoorPrice is worked out for these. Saved on this device.</p>' +
      '<fieldset><legend>Ship to</legend>' + radios("r", [["EU", "EU"], ["UK", "UK"], ["US", "US"], ["CA", "Canada"], ["AU", "Australia"]], "EU") +
      '<label class="sheet-sel">Country (sets import VAT)<select><option>Bulgaria · 20%</option><option>Germany · 19%</option><option>France · 20%</option><option>EU average · 21%</option></select></label></fieldset>' +
      '<fieldset><legend>Pay with</legend>' + radios("p", [["card", "Card"], ["paypal", "PayPal"], ["bank", "Bank transfer"]], "card") + '</fieldset>' +
      '<fieldset><legend>Show prices in</legend>' + radios("c", [["EUR", "€ EUR"], ["GBP", "£ GBP"], ["USD", "$ USD"], ["CAD", "C$ CAD"], ["AUD", "A$ AUD"]], "EUR") + '</fieldset>' +
      '<p class="sheet-note">Mockup: totals here are for the EU, paying by card, in euro (EU average import VAT 21%).</p>' +
      '<button class="sheet-done" value="ok">Done</button></form>';
    document.body.appendChild(d);
    return d;
  }
  function wirePrefs() {
    document.querySelectorAll("[data-prefs]").forEach(function (b) {
      b.addEventListener("click", function () { var d = sheet(); d.showModal ? d.showModal() : d.setAttribute("open", ""); });
    });
  }

  // The switcher that lets the reviewer hop between directions, the home page and the three sample phones
  var DIRS = [["d", "Preview · prices from 26 Oct"]];   // newsite preview: direction D only
  var SHORT = { "oppo-find-x9-ultra": "X9 Ultra (both)", "oneplus-16": "OnePlus 16 (China only)", "google-pixel-11-pro": "Pixel 11 Pro (Global, 1 store)" };
  function switcher(dir, page) {
    var cur = page === "phone" || page === "specs" ? phone().slug : null;
    var el = document.createElement("nav");
    el.className = "mock-switch";
    el.setAttribute("aria-label", "Mockup directions");
    el.innerHTML = '' +
      DIRS.map(function (d) {
        return '<span class="ms-dir' + (d[0] === dir ? " on" : "") + '"><b>' + d[1] + '</b>' +
          '<a href="' + d[0] + '-home.html"' + (d[0] === dir && page === "home" ? ' aria-current="page"' : "") + '>Home</a>' +
          D.samples.map(function (s) {
            return '<a href="' + d[0] + '-phone.html?p=' + s + '"' + (d[0] === dir && cur === s ? ' aria-current="page"' : "") + '>' + SHORT[s] + '</a>';
          }).join("") + (d[0] === "d" ? '<a href="d-drops.html"' + (dir === "d" && page === "drops" ? ' aria-current="page"' : "") + '>Price drops</a>' +
            '<a href="d-specs.html?p=' + (cur || D.samples[0]) + '"' + (dir === "d" && page === "specs" ? ' aria-current="page"' : "") + '>All specs</a>' : "") + '</span>';
      }).join("");
    document.body.appendChild(el);
    var on = el.querySelector("[aria-current]");
    if (on) el.scrollLeft = on.offsetLeft - 120;
    wirePrefs();
  }
  // phone-page links from a home page: the three samples are real pages, the rest open the closest sample
  function phoneHref(dir, slug) {
    return dir + "-phone.html?p=" + (D.phones[slug] ? slug : D.samples[0]);
  }
  // a small two-line price chart (Global blue, China amber) over the tracked days; returns SVG markup
  function lines(hist, w, hgt, cls) {
    var all = [].concat(hist.global || [], hist.china || []);
    if (!all.length) return "";
    var ds = Array.from(new Set(all.map(function (x) { return x.d; }))).sort();
    var ps = all.map(function (x) { return x.p; }), lo = Math.min.apply(0, ps), hi = Math.max.apply(0, ps);
    if (hi - lo < 1) { lo -= 50; hi += 50; }
    var pad = 6;
    function xy(x) { return [(ds.indexOf(x.d) / Math.max(1, ds.length - 1)) * (w - 2 * pad) + pad, hgt - pad - (x.p - lo) / (hi - lo) * (hgt - 2 * pad)]; }
    function path(s) { return s.map(function (x, i) { var q = xy(x); return (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1); }).join(""); }
    return '<svg viewBox="0 0 ' + w + ' ' + hgt + '" preserveAspectRatio="none" class="' + (cls || "") + '" aria-hidden="true">' +
      ["global", "china"].map(function (e) { return hist[e] && hist[e].length ? '<path d="' + path(hist[e]) + '" class="ln-' + e + '" fill="none" stroke-width="2.2" vector-effect="non-scaling-stroke"/>' : ""; }).join("") + '</svg>';
  }
  // one line per store (PCPartPicker): {label: [{d, p}]} -> SVG with a dot at each line's last price; colours --s1..--s6
  function multi(byStore, w, hgt) {
    var names = Object.keys(byStore).filter(function (k) { return byStore[k].length; });
    var all = [].concat.apply([], names.map(function (k) { return byStore[k]; }));
    if (!all.length) return { svg: "", names: [] };
    var ds = Array.from(new Set(all.map(function (x) { return x.d; }))).sort();
    var ps = all.map(function (x) { return x.p; }), lo = Math.min.apply(0, ps), hi = Math.max.apply(0, ps);
    if (hi - lo < 1) { lo -= 50; hi += 50; }
    var pad = 8;
    function xy(x) { return [(ds.indexOf(x.d) / Math.max(1, ds.length - 1)) * (w - 2 * pad) + pad, hgt - pad - (x.p - lo) / (hi - lo) * (hgt - 2 * pad)]; }
    var svg = '<svg viewBox="0 0 ' + w + ' ' + hgt + '" aria-hidden="true">' + names.map(function (k, i) {
      var s = byStore[k], q = xy(s[s.length - 1]);
      return '<path d="' + s.map(function (x, j) { var a = xy(x); return (j ? "L" : "M") + a[0].toFixed(1) + " " + a[1].toFixed(1); }).join("") +
        '" fill="none" stroke="var(--s' + (i % 6 + 1) + ')" stroke-width="2.2" stroke-linejoin="round"/>' +
        '<circle cx="' + q[0].toFixed(1) + '" cy="' + q[1].toFixed(1) + '" r="3.5" fill="var(--s' + (i % 6 + 1) + ')"/>';
    }).join("") + '</svg>';
    return { svg: svg, names: names, lo: lo, hi: hi, first: ds[0] };
  }
  function trend(series) {
    if (!series || !series.length) return null;
    var ps = series.map(function (x) { return x.p; });
    return { now: ps[ps.length - 1], lo: Math.min.apply(0, ps), hi: Math.max.apply(0, ps), first: series[0].d };
  }
  function sameBrand(p, n) {
    return D.home.filter(function (h) { return h.brand === p.brand && h.slug !== p.slug; }).slice(0, n || 3);
  }
  window.DPX = { multi: multi, lines: lines, trend: trend, sameBrand: sameBrand, mark: mark, lockup: lockup, eur: eur, storage: storage, memSort: memSort, day: day, month: month, stamp: stamp, ago: ago,
                 trackedDays: trackedDays, rank: rank, drop: drop, caveat: caveat, settled: settled, tail: tail, days: days, ED: ED,
                 missing: missing, stores: stores, phone: phone, prefsLabel: prefsLabel, switcher: switcher, phoneHref: phoneHref };
})();
