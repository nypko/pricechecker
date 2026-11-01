# Task 8c: Vivo, iQOO band lists (read 2026-11-01)

Rule used: lte = union of the page's FDD and TDD rows (row labels are swapped on some Global pages; the union is unaffected); nr = the 5G row. Suffixes and notes were dropped to integers: "B28A"/"n28A"/"B28B"/"n28B" -> 28, "n25(TX 1850-1910MHz...)" -> 25, "B32(RX)" -> 32. 2G/3G left out. No band added to config/bands.yaml (all already present).

## China (filled for vivo; page text is the 网络频段 row, server-rendered, readable without a browser)
URL pattern: https://www.vivo.com/cn/products/param/<slug> (byte-identical band text to https://www.vivo.com.cn/vivo/param/<slug>).
- vivo-x300 (x300): "4G TD-LTE: B34/B38/B39/B40/B41/B42/B43/B48; 4G FDD-LTE: B1/B2/B3/B4/B5/B7/B8/B18/B19/B20/B25/B26/B28A/B66; 5G: n1/n2/n3/n5/n7/n8/n18/n20/n25/n26/n28A/n34/n38/n39/n40/n41/n48/n66/n77/n78"
- vivo-x300s (x300s): same 4G; "5G: n1/n2/n3/n5/n7/n8/n18/n20/n25/n26/n28A/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79"
- vivo-x300-pro (x300pro): same 4G; "5G: n1/n2/n3/n5/n7/n8/n18/n20/n25/n26/n28A/n66/n34/n38/n39/n40/n41/n48/n77/n78/n79"
- vivo-x300-ultra (x300ultra): "4G FDD-LTE: B1/B2/B3/B4/B5/B7/B8/B12/B17/B18/B19/B20/B25/B26/B28/B66"; TDD as above; "5G: n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n38/n40/n41/n48/n66/n77/n78/n79/n80/n81/n83/n84/n89"
- vivo-x500 (x500): same 4G as x300; "5G: n1/n2/n3/n5/n7/n8/n18/n20/n25(TX 1850-1910MHz, RX 1930-1990MHz)/n26/n28A/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79"
- vivo-x500-pro (x500pro): "FDD-LTE: ...B25/B26/B28/B66" (B28, no A); "5G: n1/n2/n3/n5/n7/n8/n18/n20/n25(TX 1850-1910MHz,RX 1930-1990MHz)/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79"
- vivo-x500-pro-max (x500promax): same 4G as x300; "5G: n1/n2/n3/n5/n7/n8/n18/n20/n25/n26/n28A/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79"
- vivo-x-fold-6 (xfold6): "FDD-LTE: B1/B2/B3/B4/B5/B7/B8/B12/B17/B18/B19/B20/B25/B26/B28/B66"; "5G: n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79"
Every page also says: "实际网络功能可用性取决于运营商网络可用性、基建部署以及手机软件版本。"

## China left out
- vivo-x300-fe: no China edition (catalog has global only).
- iqoo-15, iqoo-15-ultra, iqoo-16 (China only): the band rows ARE readable on vivo.com/cn/products/param/iqoo15 / iqoo15ultra / iqoo16 (the iQOO site links its phones to vivo.com.cn), but the brief says iqoo.com, and specs.validate only accepts iqoo.com for brand iqoo. The iqoo.com/cn pages are a JS shell or time out (HTTP 524). Not filled to keep the tests passing without touching code. Text found, for a follow-up if hosts are widened (vivo.com and vivo.com.cn added to iqoo in BRAND_HOSTS):
  - iqoo-15: "4G TD-LTE: B34/B38/B39/B40/B41/B42/B43/B48; 4G FDD-LTE: B1/B2/B3/B4/B5/B7/B8/B18/B19/B20/B25/B26/B28A/B66; 5G: n1/n2/n3/n5/n7/n8/n18/n20/n25/n26/n28A/n38/n40/n41/n48/n66/n75/n77/n78/n80/n81/n83/n84/n89/n91/n92/n93/n94"
  - iqoo-15-ultra: "FDD-LTE: B1/B2/B3/B4/B5/B7/B8/B12/B17/B18/B19/B20/B25/B26/B28A/B28B/B32/B66; 5G: n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28A/n28B/n38/n40/n41/n48/n66/n75/n77/n78/n79/n80/n81/n83/n84/n89/n91/n92/n93/n94" (TDD as above)
  - iqoo-16: "FDD-LTE: B1/B2/B3/B4/B5/B7/B8/B18/B19/B20/B25/B26/B28A/B32/B66; 5G: n1/n2/n3/n5/n7/n8/n18/n20/n25/n26/n28A/n34/n38/n39/n40/n41/n48/n66/n75/n77/n78/n79/n80/n81/n83/n84/n89/n91/n92/n93/n94" (TDD as above)

## Global (spec tables are HTML text, no graphics)
- vivo-x300: https://www.vivo.com/en/products/param/x300 : "FDD-LTE B1/B2/B3/B4/B5/B7/B8/B12/B17/B18/B19/B20/B25/B26/B28/B32/B66; TD-LTE B38/B39/B40/B41/B42; 5G n1/n2/n3/n5/n7/n8/n20/n25/n26/n28/n38/n40/n41/n66/n75/n77/n78"
- vivo-x300-pro: https://www.vivo.com/en/products/param/x300-pro : "FDD-LTE B1/B2/B3/B4/B5/B7/B8/B12/B13/B17/B18/B19/B20/B25/B26/B28/B32/B66/B71; TD-LTE B34/B38/B39/B40/B41/B42; 5G n1/n2/n3/n5/n7/n8/n20/n25/n26/n28/n38/n40/n41/n66/n71/n75/n77/n78/n79"
- vivo-x300-ultra: https://www.vivo.com/my/products/param/x300-ultra (Malaysia). The /en page prints the FDD list in the TD-LTE row too (a page error, no TDD bands), so /en was not used. sg, my, id, ph, ae pages agree. "FDD B1/B2/B3/B4/B5/B7/B8/B12/B13/B17/B18/B19/B20/B25/B26/B28/B32(RX)/B66/B71; TD-LTE B34/B38/B39/B40/B41/B42/B43/B48; 5G n1/n2/n3/n5/n7/n8/n12/n20/n25/n28/n38/n40/n41/n66/n71/n75/n77/n78/n79"
- vivo-x300-fe: https://www.vivo.com/my/products/param/x300-fe (no /en page; sg, ph, ae agree). "FDD B1/B2/B3/B4/B5/B7/B8/B12/B13/B17/B18/B19/B20/B25(1850-1910 MHz)/B26/B28/B32/B66/B71; TD-LTE B34/B38/B39/B40/B41/B42/B43/B48; 5G n1/n2/n3/n5/n7/n8/n18/n20/n25(1850-1910 MHz)/n26/n28/n38/n40/n41/n48/n66/n71/n75/n77/n78"
- vivo-x500: https://www.vivo.com/sg/products/param/x500 (Singapore; only region found). Rows labelled swapped on page: "B38/B39/B40/B41/B42/B43/B48" and "B1/B2/B3/B4/B5/B7/B8/B12/B13/B17/B18/B19/B20/B25/B26/B28/B32/B66/B71"; "5G n1/n2/n3/n5/n7/n8/n20/n25(TX 1850-1910 MHz, RX 1930-1990 MHz)/n26/n28/n38/n40/n41/n66/n71/n75/n77/n78"
- vivo-x500-pro-max: https://www.vivo.com/sg/products/param/x500-pro-max (Singapore; only region found). Same swapped rows: "B34/B38/B39/B40/B41/B42/B43/B48" + "B1/B2/B3/B4/B5/B7/B8/B12/B13/B17/B18/B19/B20/B25/B26/B28/B32/B66/B71"; "5G n1/n2/n3/n5/n7/n8/n12/n20/n25/n26/n28/n38/n40/n41/n66/n71/n75/n77/n78/n79"
- vivo-x-fold-6: https://www.vivo.com/ae/products/param/x-fold6 (UAE; only region found). "FDD B1/B2/B3/B4/B5/B7/B8/B12/B17/B18/B19/B20/B25/B26/B28/B32/B66; TD-LTE B34/B38/B39/B40/B41/B42/B43/B48; 5G n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n75/n77/n78/n79"
Global left out: none of the catalog's Global versions (x300, x300-pro, x300-ultra, x300-fe, x500, x500-pro-max, x-fold-6). No Global edition exists in the catalog or offers for x300s, x500-pro, iqoo-*.

## Readability of official China URLs
- Readable (server-rendered, HTTP 200): https://www.vivo.com/cn/products/param/<slug> and https://www.vivo.com.cn/vivo/param/<slug> for x300, x300s, x300pro, x300ultra, x500, x500pro, x500promax, xfold6, iqoo15, iqoo15ultra, iqoo16. Product pages (/vivo/x300) are heavy but carry the same text. Slugs have no dashes.
- Not readable: iqoo.com/cn/* (404, JS shell, or 524 timeout); no vivo China page for x300fe (404 shell).

## Concerns
- BRAND_HOSTS lists only vivo.com for vivo and iqoo.com for iqoo, so vivo.com.cn and iQOO's real spec pages cannot be sources; vivo.com/cn was used for vivo. iQOO needs a code change.
- n28A/n28B stored as 28 (page names a sub-band; integer list cannot show it).
- x500 / x500-pro-max / x-fold-6 Global come from one regional site each (sg, sg, ae); regional band sets differ by site (e.g. x300-pro /en vs other regions not compared).
- Offers contain no versions beyond the catalog editions.
