# Task 8a: Huawei band lists (read 2026-11-01)

## Filled (all Global version, from Huawei's own regional site, section "Network")
Single-SIM and dual-SIM model blocks list identical bands on every page. Text is HTML, no graphics.
- huawei-pura-80-ultra / global: https://consumer.huawei.com/en/phones/pura80-ultra/specs/ (model LMU-LX9)
  "4G LTE FDD: Bands 1/2/3/4/5/6/7/8/9/12/13/17/18/19/20/25/26/28/32/66"; "4G LTE TDD: Bands 34/38/39/40/41/42". No 5G NR line on the page, so nr: [] (page lists none).
- huawei-mate-x7 / global: https://consumer.huawei.com/en/phones/mate-x7/specs/
  "4G LTE FDD: Bands 1/2/3/4/5/6/7/8/9/12/13/17/18/19/20/26/28/66"; "4G LTE TDD: Bands 34/38/39/40/41/42/48". No 5G NR line, so nr: [].
- huawei-pura-90s-pro / global: https://consumer.huawei.com/en/phones/pura90s-pro/specs/ (MLN-LX9; /my/ and /ph/ pages identical)
  "5G NR: n1/n2/n3/n5/n7/n8/n12/n20/n26/n28/n38/n40/n41/n48/n66/n71/n77/n78/n79/n80/n81/n83/n84"; LTE FDD "Bands 1/2/3/4/5/6/7/8/9/12/13/17/18/19/20/26/28/66"; TDD "Bands 34/38/39/40/41/42/48".
- huawei-pura-90s-pro-max / global: https://consumer.huawei.com/en/phones/pura90s-pro-max/specs/ (SCA-LX9; /my/ /ph/ identical)
  Same NR and LTE lists as the Pura 90s Pro.

## China version left without bands (all 14 China phones, plus offers-only China edition of pura-80-ultra)
The China spec pages (consumer.huawei.com/cn/phones/<slug>/specs/) exist but have no 网络制式 / 频段 section and no LTE/NR band text at all (checked: mate80, mate80-pro, mate80-pro-max, mate90, mate90-pro, mate90-pro-max, mate-x7, mate-xt-ultimate-design, pura80-ultra, pura90, pura90-pro, pura90-pro-max, pura-x-max, pura-x-view; page text has only WLAN, Bluetooth, SIM, etc.). No sources.china added since no band list was read.
Pages not found (404 on guessed slugs): huawei-mate-90-rs, huawei-mate-xt-2-ultimate-design. Not located; also no bands published for them as far as found.
Global edition in offers: mate-x7 global (filled above). China edition of pura-80-ultra in offers: no China bands.

## bands.yaml
Added LTE B6 (875 MHz) and B9 (1845 MHz), generic use text.

## Concerns
- nr: [] for Pura 80 Ultra and Mate X7 global means "page lists no 5G NR", not a verified statement that the phones have no 5G.
- Third-party sites disagree for Pura 90s Pro; they were not used.
