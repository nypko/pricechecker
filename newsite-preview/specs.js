/* Full spec sheets for the three sample phones, copied from each brand's own spec page on 26 Oct 2026 (the proposed
   config/specs/<id>.yaml format, as JSON). Values are the brand's words, shortened; nothing filled in from third-party sites.
   A value can differ by version: {global: ..., china: ...}. "bands" lists network bands per version; a version whose
   brand page we haven't read has no entry, and the page says so. */
window.DPS = {
  // main bands EU operators use; the band check flags any the phone's version lacks (carriers differ: always check yours)
  regionBands: {
    EU: { label: "the EU", lte: [1, 3, 7, 8, 20, 28], nr: [1, 3, 7, 8, 20, 28, 78],
          why: { 20: "800 MHz: rural coverage and indoors in most EU countries", 28: "700 MHz: wide-area 4G/5G in many EU countries", 78: "3.5 GHz: the main EU 5G band" } }
  },
  phones: {
    "oppo-find-x9-ultra": {
      // both brand pages read: {china, global} = the pages disagree; {v, from} = only one page lists it (not a difference)
      sources: { global: { url: "https://www.oppo.com/en/smartphones/series-find-x/find-x9-ultra/specs/", checked: "2026-10-26" },
                 china: { url: "https://www.oppo.com/cn/smartphones/series-find-x/find-x9-ultra/specs/", checked: "2026-10-26", lang: "Chinese" } },
      groups: [
        ["Display", [["Size", "6.82 in, flat"], ["Panel", { v: "AMOLED, Gorilla Glass Victus 2", from: "global" }], ["Resolution", "3168 × 1440 (QHD+), 510 ppi"], ["Refresh rate", "Up to 144 Hz (in some games)"], ["Brightness", "800 nits typical, 1,800 nits high-brightness mode"], ["Colour", "10-bit"]]],
        ["Performance", [["Chip", "Snapdragon 8 Elite Gen 5"], ["CPU", "8 cores"], ["Top CPU speed", { v: "4.608 GHz", from: "china" }], ["GPU", { v: "Adreno 840 @ 1,200 MHz", from: "global" }], ["RAM", "LPDDR5X"], ["Storage", "UFS 4.1, no memory card"], ["Versions", { china: "12+256, 12+512, 16+512, 16 GB + 1 TB", global: "12 GB + 512 GB, 16 GB + 1 TB" }]]],
        ["Battery and charging", [["Battery", "7,050 mAh typical (6,890 mAh rated)"], ["Wired", { china: "100 W SUPERVOOC, 100 W UFCS; also 55 W PPS, 18 W PD", global: "100 W SUPERVOOC; also 55 W PPS, 18 W PD" }], ["Wireless", "50 W"]]],
        ["Cameras", [["Main", "200 MP, f/1.5, OIS"], ["Telephoto", "200 MP, f/2.2, OIS (3x)"], ["Periscope", "50 MP, f/3.5, OIS (10x)"], ["Ultra-wide", "50 MP, f/2.0, 123°"], ["Colour lens", { china: "Danxia colour lens, f/2.4", global: "3.2 MP monochrome, f/2.4" }], ["Front", "50 MP, f/2.4, autofocus"], ["Video", "8K 30 fps, 4K 120 fps, 4K Dolby Vision 120 fps"]]],
        ["Build", [["Size", "163.16 × 76.97 × 8.65 mm (9.10 mm leather back)"], ["Weight", "235 g (236 g leather back)"], ["Colours", { china: "Three, incl. a glacier white", global: "Canyon Orange, Tundra Umber" }], ["Water and dust", null]]],
        ["Connectivity", [["Wi-Fi", "Wi-Fi 7"], ["Bluetooth", "6.0; LDAC, aptX Adaptive, LHDC 5.0"], ["LE Audio", { v: "Yes", from: "china" }], ["NFC", { china: "Yes, with Chinese transit and payment cards", global: "Yes (depends on region)" }], ["SIM", { china: "Dual nano-SIM (no eSIM listed)", global: "Dual nano-SIM + eSIM" }], ["USB", "USB-C 3.2 Gen 1, no analogue headphones"], ["Satellite positioning", { china: "BeiDou, GPS L1+L5, Galileo, GLONASS, QZSS", global: "GPS L1+L5, Galileo, BeiDou, GLONASS, QZSS, NavIC" }], ["China model number", { v: "PMA110", from: "china" }]]],
        ["Software", [["System", "ColorOS 16"], ["Updates", null]]],
        ["Other", [["Fingerprint", "Ultrasonic, under the screen"], ["Face unlock", "Yes"], ["Infrared remote", "Yes"], ["In the box", { v: "Charger, cable, case", from: "china" }]]]
      ],
      bands: { global: { lte: [1, 2, 3, 4, 5, 7, 8, 12, 13, 17, 18, 19, 20, 25, 26, 28, 32, 66, 71, 38, 39, 40, 41, 42], nr: [1, 2, 3, 5, 7, 8, 12, 20, 25, 26, 28, 38, 40, 41, 66, 71, 75, 77, 78, 79] },
               china: { lte: [1, 2, 3, 4, 5, 7, 8, 12, 17, 18, 19, 20, 25, 26, 28, 66, 34, 38, 39, 40, 41, 42, 43, 48], nr: [1, 2, 3, 5, 7, 8, 12, 18, 20, 25, 26, 28, 38, 40, 41, 48, 66, 77, 78, 79, 80, 81, 83, 84, 89] } }
    },
    "oneplus-16": {
      sources: { china: { url: "https://www.oneplus.com/cn/16/specs", checked: "2026-10-26", lang: "Chinese" } },
      groups: [
        ["Display", [["Size", "6.78 in, flat"], ["Panel", "Flat screen, Crystal Shield glass (panel type not stated)"], ["Resolution", "2772 × 1272 (FHD+), 450 ppi"], ["Refresh rate", "1–165 Hz, up to 185 Hz in games"], ["Brightness", "1,000 nits typical, 2,000 nits high-brightness mode"], ["Dimming", "3,840 Hz PWM below 70 nits, DC-like above"]]],
        ["Performance", [["Chip", "Snapdragon 8 Elite Extreme Gen 6 (2 nm)"], ["CPU", "8 cores, up to 5.01 GHz"], ["GPU", "Adreno 850 @ 1,450 MHz"], ["RAM", "LPDDR5X Ultra"], ["Storage", "UFS 4.1"], ["Versions", "12+256, 12+512, 16+512, 16 GB + 1 TB"]]],
        ["Battery and charging", [["Battery", "9,000 mAh typical (2 × 4,500; 8,780 mAh rated)"], ["Wired", "100 W SUPERVOOC / 100 W UFCS; also 55 W PPS, 18 W PD"], ["Wireless", null]]],
        ["Cameras", [["Main", "200 MP, f/1.6, OIS"], ["Telephoto", "50 MP, f/2.6, OIS (3x)"], ["Ultra-wide", "50 MP, f/2.0, 116°"], ["Front", "50 MP, f/2.0, autofocus"], ["Video", "8K 30 fps, 4K 120 fps, 4K Dolby Vision 120 fps"]]],
        ["Build", [["Size", "161.42 × 76.67 × 8.45–8.55 mm"], ["Weight", "217–220 g"], ["Colours", "Three colours (Chinese names)"], ["Water and dust", "IP66, IP68, IP69, IP69K"], ["Frame", "Metal"]]],
        ["Connectivity", [["Wi-Fi", "Wi-Fi 7"], ["Bluetooth", "6.0, LE Audio"], ["NFC", "Yes"], ["SIM", "Dual nano-SIM (no eSIM listed)"], ["USB", "USB-C 3.2 Gen 1"], ["Satellite positioning", "BeiDou, GPS L1+L2+L5, Galileo, GLONASS, QZSS"]]],
        ["Software", [["System", "ColorOS 17 (Chinese software; see what the China version means)"], ["Updates", null]]],
        ["Other", [["Speakers", "Stereo"], ["Fingerprint", "Ultrasonic, under the screen"], ["Infrared remote", "Yes"], ["In the box", "Charger, cable, case"]]]
      ],
      bands: { china: { lte: [1, 2, 3, 4, 5, 7, 8, 18, 19, 25, 26, 28, 32, 66, 34, 38, 39, 40, 41, 42, 43, 48], nr: [1, 2, 3, 5, 7, 8, 18, 25, 26, 28, 34, 38, 39, 40, 41, 48, 66, 75, 77, 78, 79, 80, 81, 83, 84, 89, 91, 92, 93, 94, 95, 98] } }
    },
    "google-pixel-11-pro": {
      sources: { global: { url: "https://support.google.com/pixelphone/answer/7158570", checked: "2026-10-26" } },
      groups: [
        ["Display", [["Size", "6.3 in, 20:9"], ["Panel", "LTPO OLED, Gorilla Glass Victus 2"], ["Resolution", "1280 × 2856, 495 ppi"], ["Refresh rate", "1–120 Hz"], ["Brightness", "2,400 nits HDR, 3,600 nits peak"]]],
        ["Performance", [["Chip", "Google Tensor G6, Titan M3 security chip"], ["Versions", "12 GB + 256 GB, 16 GB + 512 GB, 16 GB + 1 TB"]]],
        ["Battery and charging", [["Battery", "4,850 mAh typical (4,707 mAh minimum)"], ["Wired", "30 W (55% in about 30 min)"], ["Wireless", "25 W Pixelsnap (Qi2.2)"]]],
        ["Cameras", [["Main", "50 MP, f/1.68, 1/1.3\""], ["Telephoto", "48 MP, f/2.8, OIS, 5x"], ["Ultra-wide", "48 MP, f/1.7, 123°, macro"], ["Front", "42 MP, f/2.2, autofocus"], ["Video", "8K 30 fps (Video Boost), 4K 60 fps, 10-bit HDR"]]],
        ["Build", [["Size", "152.7 × 71.9 × 8.4 mm"], ["Weight", "204 g"], ["Colours", "Canyon, Olive, Fog, Obsidian"], ["Water and dust", "IP68"], ["Frame", "Recycled aluminium"]]],
        ["Connectivity", [["Wi-Fi", "Wi-Fi 7"], ["Bluetooth", "6"], ["NFC", "Yes"], ["SIM", "Nano-SIM + eSIM (EU model)"], ["USB", "USB-C 3.2"], ["Also", "Ultra-wideband, Thread"]]],
        ["Software", [["System", "Android 17"], ["Updates", "7 years of OS and security updates"]]],
        ["Other", [["Speakers", "Stereo, 3 microphones"], ["Sensors", "Barometer, gyro, compass, proximity, light"]]]
      ],
      bands: { global: { lte: [1, 2, 3, 4, 5, 7, 8, 12, 13, 14, 17, 18, 19, 20, 21, 25, 26, 28, 29, 30, 32, 38, 39, 40, 41, 42, 48, 66, 71, 75], nr: [1, 2, 3, 5, 7, 8, 12, 13, 14, 20, 25, 26, 28, 30, 38, 40, 41, 66, 71, 75, 77, 78, 79] } }
    }
  }
};
// which of a region's main bands a version lacks: null when we haven't read that version's bands
DPS.check = function (slug, ed, region) {
  var p = DPS.phones[slug], r = DPS.regionBands[region || "EU"], b = p && p.bands[ed];
  if (!b) return null;
  return { lte: r.lte.filter(function (x) { return b.lte.indexOf(x) < 0; }), nr: r.nr.filter(function (x) { return b.nr.indexOf(x) < 0; }), r: r };
};
// how many fields differ between the versions (both pages read)
DPS.diffs = function (slug) {
  var p = DPS.phones[slug]; if (!p) return 0;
  return p.groups.reduce(function (n, g) { return n + g[1].filter(function (r) { return r[1] && typeof r[1] === "object" && "china" in r[1]; }).length; }, 0);
};
DPS.count = function (slug) {
  var p = DPS.phones[slug]; if (!p) return 0;
  return p.groups.reduce(function (n, g) { return n + g[1].length; }, 0);
};
