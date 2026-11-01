# Task 8e: Google, Samsung, Motorola, Sony, Apple band lists (read 2026-11-01)

Rule: lte = FDD + TDD union, nr = Sub6 NR (2G/3G left out, suffixes like "(2100)" dropped). No band added to config/bands.yaml (n76 and all others already present). mmWave (n258/n260/n261) is only on US models, not recorded.

## Google (source https://support.google.com/pixelphone/answer/7158570, "ROW" model = EU/international, 5G Sub 6GHz; US mmWave models not used)
Page footnote: "Some bands supported by the device hardware may not be enabled."
- google-pixel-10-pro global, model GEHN3. LTE: 1/2/3/4/5/7/8/12/13/14/17/18/19/20/21/25/26/28/29/30/32/38/39/40/41/42/48/66/71/75. 5G Sub-6: 1/2/3/5/7/8/12/14/20/25/26/28/30/38/40/41/66/71/75/76/77/78/79.
- google-pixel-10-pro-xl global, model G45RY. Same lists as Pixel 10 Pro.
- google-pixel-11 global, model GUJ0N; google-pixel-11-pro global, model GM45K (already filled, matches the page); google-pixel-11-pro-xl global, model G4HCD. All three ROW lists: LTE 1/2/3/4/5/7/8/12/13/14/17/18/19/20/21/25/26/28/29/30 and 32/38/39/40/41/42/48/66/71/75; NR 1/2/3/5/7/8/12/13/14/20/25/26/28/30/38/40/41/66/71/75/77/78/79.
- No China edition (Google sells none).

## Samsung (Global = EU model, Network section of samsung.com business spec pages; the consumer /specs pages carry no band table)
All five pages list the same set. Page text: "4G FDD LTE B1(2100), B2(1900), B3(1800), B4(AWS), B5(850), B7(2600), B8(900), B12(700), B13(700), B17(700), B18(800), B19(800), B20(800), B25(1900), B26(850), B28(700), B32(1500), B66(AWS-3); 4G TDD LTE B38(2600), B39(1900), B40(2300), B41(2500); 5G FDD Sub6 N1, N2, N3, N5, N7, N8, N12, N20, N25, N26, N28, N66; 5G TDD Sub6 N38, N40, N41, N77, N78; 5G SDL Sub6 N75(1500+)". Recorded nr includes the SDL band 75. No note in the section.
- samsung-galaxy-s26: SM-S942B, https://www.samsung.com/uk/business/smartphones/galaxy-s/galaxy-s26-cobalt-violet-256gb-sm-s942bzvgeub/
- samsung-galaxy-s26-plus: SM-S947B, https://www.samsung.com/ie/business/smartphones/galaxy-s/galaxy-s26-plus-white-512gb-sm-s947bzwgeub/ (Ireland, EU model; no UK page found)
- samsung-galaxy-s26-ultra: SM-S948B, https://www.samsung.com/uk/business/smartphones/galaxy-s/galaxy-s26-ultra-cobalt-violet-256gb-sm-s948bzvdeub/
- samsung-galaxy-z-fold-8: SM-F971B, https://www.samsung.com/uk/business/smartphones/galaxy-z/galaxy-z-fold8-graphite-256gb-sm-f971bzkbeeb/
- samsung-galaxy-z-fold-8-ultra: SM-F976B, https://www.samsung.com/uk/business/smartphones/galaxy-z/galaxy-z-fold8-ultra-graphite-256gb-sm-f976bzkbeeb/
- Left out: China edition of all five. Samsung China is on samsung.com.cn (samsung.com/cn 301-redirects there); that host is not in BRAND_HOSTS (samsung.com only), and the page fetched carried no band table or model number.

## Motorola: all versions left out
- motorola-razr-70-ultra (china, global) and motorola-razr-fold (china, global): motorola.com support spec pages (en-gb, en-us, en-au, fr-fr, pl-pl support.motorola.com) return HTTP 403 to automated fetch (bot check). Not bypassed. Search-result snippets (not usable as a source) suggested US lists differ from UK; unverified. No China page found on motorola.com.

## Sony: all versions left out
- sony-xperia-1-vii (china) and sony-xperia-1-viii (china, global): sony.com and electronics.sony.com cannot be fetched from here; sony.com.cn / sony.jp / sony.co.uk are not allowed hosts. The Japan SIM-free page (sony.jp) lists a Japan-model set, not the Global one.

## Apple
- apple-iphone-duo: China (A3721, apple.com.cn) and Global (A3720, apple.com/uk) already filled and sourced; not changed.
