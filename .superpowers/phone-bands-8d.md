# Task 8d: Honor, Oppo, OnePlus, Realme band lists (read 2026-11-01)

Rule used: lte = union of the page's LTE FDD and LTE TDD rows; nr = the 5G row. Suffixed bands stored as the integer: n28A/n28B/n83A -> 28/83 (noted below). 2G/3G left out. No band added to config/bands.yaml (all already present). All pages were fetched with plain HTTP GET (a normal browser user agent, one request per URL, 1 s apart); no cookies or bot-check workarounds. Pages are HTML text, no graphics.
oppo-find-x9-ultra (china + global) and oneplus-16 (china) already had bands; re-read the live pages, they match the stored lists (oneplus-16 page says 28A/28B, stored as 28), left unchanged.

## Filled (quoted band text)

### oppo-find-x10
- China: https://www.oppo.com/cn/smartphones/series-find-x/find-x10/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/18/19/25/26/28/66; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n18/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79
- Global: https://www.oppo.com/en/smartphones/series-find-x/find-x10/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66; LTE TDD 38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n38/n40/n41/n48/n66/n75/n77/n78/n79

### oppo-find-x10-pro-max
- China: https://www.oppo.com/cn/smartphones/series-find-x/find-x10-pro-max/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/17/18/19/20/25/26/28/66; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79
- Global: https://www.oppo.com/en/smartphones/series-find-x/find-x10-pro-max/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71; LTE TDD 38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n38/n40/n41/n48/n66/n71/n75/n77/n78/n79

### oppo-find-x9
- China: https://www.oppo.com/cn/smartphones/series-find-x/find-x9/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/18/19/25/26/28/66; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n18/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78
- Global: https://www.oppo.com/en/smartphones/series-find-x/find-x9/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/26/28/32/66; LTE TDD 38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n20/n26/n28/n38/n40/n41/n48/n66/n75/n77/n78

### oppo-find-x9-pro
- China: https://www.oppo.com/cn/smartphones/series-find-x/find-x9-pro/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/17/18/19/20/25/26/28/66; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n18/n20/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79
- Global: https://www.oppo.com/en/smartphones/series-find-x/find-x9-pro/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71; LTE TDD 38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n20/n25/n26/n28/n38/n40/n41/n48/n66/n71/n75/n76/n77/n78/n79

### oppo-find-x9s-pro
- China: https://www.oppo.com/cn/smartphones/series-find-x/find-x9s-pro/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/18/19/25/26/28/66; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n18/n25/n26/n28/n34/n38/n39/n40/n41/n48/n66/n77/n78/n79

### oppo-find-n6
- China: https://www.oppo.com/cn/smartphones/series-find-n/find-n6/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n13/n18/n20/n25/n26/n28/n38/n40/n41/n48/n66/n71/n75/n77/n78/n79/n80/n81/n83/n84/n89
- Global: https://www.oppo.com/en/smartphones/series-find-n/find-n6/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71; LTE TDD 38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n20/n25/n26/n28/n38/n40/n41/n66/n71/n75/n77/n78/n79

### oppo-find-n5
- China: https://www.oppo.com/cn/smartphones/series-find-n/find-n5/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/17/18/19/20/26/28/66; LTE TDD 34/38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n20/n28/n38/n40/n41/n66/n77/n78/n80/n81/n83/n84
- Global: https://www.oppo.com/en/smartphones/series-find-n/find-n5/specs/
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/66; LTE TDD 38/39/40/41/42; 5G NR n1/n2/n3/n5/n7/n8/n12/n20/n25/n26/n28/n38/n40/n41/n66/n77/n78

### oneplus-15t
- China: https://www.oneplus.com/cn/15t/specs
  quoted: LTE FDD 1/2/3/4/5/7/8/18/19/26/28/66; LTE TDD 34/38/39/40/41/42/43/48; 5G NR n1/n2/n3/n5/n7/n8/n18/n26/n28/n38/n40/n41/n66/n48/n77/n78

### oneplus-15
- China: https://www.oneplus.com/cn/15/specs
  quoted: LTE FDD 1/3/4/5/7/8/18/19/20/26/28A/66; LTE TDD 34/38/39/40/41/42/48; 5G NR n1/n3/n5/n7/n8/n20/n26/n28A/n38/n40/n41/n48/n66/n77/n78/n79/n80/n81/n83A/n84/n89
- Global: https://www.oneplus.com/global/15/specs
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/30/32/66/71; LTE TDD 34/38/39/40/41/42/48; 5G NR n1/n2/n3/n5/n7/n8/n12/n13/n20/n25/n26/n28/n30/n38/n40/n41/n48/n66/n71/n75/n77/n78

### realme-gt-8-pro
- China: https://www.realme.com/cn/realme-gt-8-pro/specs
  quoted: LTE FDD 1/3/4/5/8/18/19/20/26/28A/66; LTE TDD 34/38/39/40/41/42/48; 5G NR n1/n3/n5/n8/n18/n20/n26/n28A/n38/n40/n41/n48/n66/n77/n78/n79/n80/n81/n83/n84/n89
- Global: https://www.realme.com/global/realme-gt-8-pro/specs
  quoted: LTE FDD 1/2/3/4/5/7/8/12/13/17/18/19/20/26/28/66/71; LTE TDD 38/39/40/41/42/48; 5G NR 1/2/3/5/7/8/20/28/38/40/41/48/66/71/77/78/79

Notes on the above:
- oppo-find-x10, -x10-pro-max, -x9, -x9-pro: the catalog lists China only, but offers contain global units, and Oppo's global page publishes a list, so Global was filled too (the pages carry "[Version 1]" and "[Version 2]"; Version 1, the full-band one, is stored. Version 2 is a smaller regional SKU: x10 "LTE FDD 1/3/5/8/28; TDD 40/41; NR n1/n3/n5/n8/n28/n40/n41", x9 and x9-pro "FDD 1/3/5/8; TDD 40; NR n1/n3/n5/n8/n40", x10-pro-max has none. Same for x9-ultra and n5 (FDD 1/3/5/8, TDD 40, NR n1/n3/n5/n8/n40).)
- oppo-find-x9s-pro China: the page is titled "OPPO Find X9s Pro 卫星通信版" (satellite edition). No global page for x9s-pro (the /en x9s-pro URL is 404; /en .../find-x9s/ is a different phone, not used).
- oppo-find-n6 / -n5: URL is series-find-n, not series-find-x. n5 global FDD row is labelled "Bands 1/.../66"; 5G row is "5G:" without "NR".
- oneplus-15 China (https://www.oneplus.com/cn/15/specs): CONCERN. The band row is "4G LTE FDD: 频段 1/3/4/5/7/8/18/19/20/26/28A/66; 4G LTE TDD: 频段 34/38/39/40/41/42/48; 5G NR: n1/n3/n5/n7/n8/n20/n26/n28A/n38/n40/n41/n48/n66/n77/n78/n79/n80/n81/n83A/n84/n89" (n28A -> 28, n83A -> 83). It is copied as published, but it lacks B2/B25 and has n20, which looks unlike OnePlus's other China sheets; it should be eyeballed. The page also has a separate "4G 4x4 MIMO" line, not used.
- oneplus-15 Global: /global/15/specs; /us/15/specs and /uk/15/specs publish the identical list.
- realme-gt-8-pro China: the specs page is a Vue app, but the full spec table is embedded in the HTML (FREQUENCY_BAND attribute), readable by GET. 28A -> 28. Global list from realme.com/global/realme-gt-8-pro/specs (labels there are "LTE FDD:" etc. with bare numbers). Catalog lists China only; offers include global.
- oneplus-15t: China only in offers. oppo-find-x10/-x9 China pages: 5G row has no n79 for x9 (as published).

## Left out
- All Honor versions: honor-magic-8 (china), -8-pro (global), -8-pro-air (china), -9, -9-pro-max, -9-super (china), -magic-v5 (china), -magic-v6 (global); offers also have China versions of magic-8-pro, v5, v6 and global v5: none of them has a band list.
  - China, https://www.honor.com/cn/phones/<slug>/spec/ (slugs honor-magic9, honor-magic9-pro-max, honor-magic9-super-power, honor-magic8, honor-magic8-pro, honor-magic8-pro-air, honor-magic-v5, honor-magic-v6): readable, server-rendered. Network section only says "网络制式: 支持移动 5GA/5G/4G+/4G/2G，电信5GA/5G/4G+/4G，联通5GA/5G/4G+/4G/3G/2G，广电5GA/5G/4G+/4G; 支持 4x4 MIMO天线技术/载波聚合技术/HPUE/HO RxD". No band numbers.
  - Global, https://www.honor.com/global/phones/<slug>/spec/ (honor-magic8-pro, honor-magic-v5, honor-magic-v6): readable; "Network Standard: 5G (NR) / 4G (LTE TDD/LTE FDD) / 3G (WCDMA) / 2G (GSM)". No band numbers. uk, de, my and ae-en pages for magic8-pro/v5 carry the same section (not different).
  - Nothing written (not even nr: []), since the pages do not say 4G-only.
- oppo-find-x9s-pro Global: Oppo has no global page for it.
- oneplus-15t Global, oneplus-16 Global: not sold globally (no offers, no OnePlus global page checked for 15t; /global/15t/specs not requested because no offer exists).
- realme-gt-8-pro: nothing left out.
- No host was missing from BRAND_HOSTS (honor.com, oppo.com, oneplus.com, realme.com were enough; oppo/oneplus/realme pages are on those hosts). Honor's China-store host (honor.cn / hihonor.com) not tried since honor.com/cn already answers without bands.

## Official China URLs
Readable by plain GET:
- https://www.oppo.com/cn/smartphones/series-find-x/<slug>/specs/ (find-x10, find-x10-pro-max, find-x9, find-x9-pro, find-x9s-pro, find-x9-ultra) and https://www.oppo.com/cn/smartphones/series-find-n/<find-n6|find-n5>/specs/. Band text is in the visible page.
- https://www.oneplus.com/cn/<15|15t|16>/specs. Band text is inside the page's embedded JSON (propertyname 网络频段 / 频段), no browser needed.
- https://www.realme.com/cn/realme-gt-8-pro/specs (embedded JSON, FREQUENCY_BAND).
- https://www.honor.com/cn/phones/<slug>/spec/ (readable but carries no band list).
Not readable / wrong URL: honor.com/cn/phones/<slug>/specs/ (404; correct path is /spec/), realme.com/cn/realme-gt8-pro (404; correct slug realme-gt-8-pro), oppo.com/cn/.../series-find-x/find-n6|n5 (404; correct series is find-n).
