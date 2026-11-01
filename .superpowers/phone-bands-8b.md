# Task 8b: Xiaomi, Redmi band lists (read 2026-11-01)

## Filled (Global version only; mi.com/global spec pages are server-rendered HTML, section "Network bands"; no graphics)
nr = union of the SA and NSA lists where both are published (the NSA list is a subset of SA on every page). LTE = FDD + TDD.
- xiaomi-17 / global: https://www.mi.com/global/product/xiaomi-17/specs/
  "5G: n1/2/3/5/7/8/12/20/25/26/28/38/40/41/48/66/71/75/77/78"; "4G: FDD-LTE: B1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71"; "4G: TDD-LTE: B38/39/40/41/42/48".
- xiaomi-17-ultra / global: https://www.mi.com/global/product/xiaomi-17-ultra/specs/
  "5G SA: n1/2/3/5/7/8/12/20/25/26/28/38/40/41/48/66/71/75/77/78/79"; "5G NSA: n1/2/3/5/7/8/20/28/38/40/41/66/71/75/77/78/79"; "4G: LTE FDD: B1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71"; "4G: LTE TDD: B38/39/40/41/42/48".
- xiaomi-17t / global: https://www.mi.com/global/product/xiaomi-17t/specs/
  "5G: SA: n1/2/3/5/7/8/12/20/26/28/34/38/39/40/41/48/66/71/75/77/78"; "5G: NSA: n1/2/3/5/7/8/20/28/38/40/41/66/71/75/77/78"; "4G: LTE FDD: B1/2/3/4/5/7/8/12/13/17/18/19/20/26/28/32/66/71"; "4G: LTE TDD: B34/38/39/40/41/42/48".
- xiaomi-17t-pro / global: https://www.mi.com/global/product/xiaomi-17t-pro/specs/
  "5G: SA: n1/2/3/5/7/8/12/20/25/26/28/34/38/39/40/41/48/66/71/75/77/78"; "5G: NSA: n1/2/3/5/7/8/20/28/38/40/41/66/71/75/77/78"; "4G: LTE FDD: B1/2/3/4/5/7/8/12/13/17/18/19/20/25/26/28/32/66/71"; "4G: LTE TDD: B34/38/39/40/41/42/48".
Pages say "Connectivity and network bands may vary based on region availability and local operator support."

## Left without bands
- All China versions (all 14 phones, incl. China editions of xiaomi-17, -17-ultra, -17t, -17t-pro seen in offers): no readable official China page found. https://www.mi.com/xiaomi-17-ultra/specs redirects to /specs, which returns the mi.com "page not found" shell (小米商城 404). The mi.com China home is a JS shell. WebFetch got 403 from mi.com. A further probe of other China URLs was blocked by the automated bot-check guard and I stopped there. No sources.china added.
- Catalog phones with only China offers/catalog edition and no Global edition (redmi-k100-pro-max, redmi-k90-pro-max, xiaomi-17-max, -17-pro, -17-pro-max, xiaomi-17-ultra-leica-edition, xiaomi-18-fold, -18-pro, -18-pro-max, xiaomi-mix-flip-2): nothing filled. Regional mi.com pages (hk, tw, in etc.) are other versions, not used.

## bands.yaml
Nothing added; all bands already present.

## Concerns
- xiaomi-17-ultra: the Global FAQ (mi.com/global/support/faq/details/KA-667490/) lists NSA without n2; the spec page (used) includes n2. Union with SA already contains n2 anyway.
- Regional pages differ (India Ultra page lists different LTE sets), so the Global lists are for the mi.com/global variant only.
