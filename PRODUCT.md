# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Mainstream bargain hunters in the EU, UK, US and Australia who want a current flagship phone for less than local retail. They often don't know that many flagships (Huawei, Honor, Oppo, Xiaomi…) come as a Global and a China version, that specialist importers sell them, or that import tax and payment-method fees change the real price. Their job: find the cheapest trustworthy place to buy a specific phone and understand what they'll actually pay.

## Product Purpose
DoorPrice is a static site that compares flagship phone prices across specialist importers, refreshed every hour, and earns affiliate commissions on outbound store links. Success is a visitor who finds the phone they want, trusts the total they see, and clicks through to buy.

## Positioning
Three things together, none leading:
- **True landed cost** — each store's own price in the visitor's currency, adjusted for payment method (bank transfer discount, PayPal fee), shipping to their region and estimated import tax when the store doesn't cover duties.
- **Global vs China gap** — both editions of a model side by side, so the price difference is visible.
- **Importer coverage** — stores mainstream comparison sites ignore (Wonda Mobile, Giztop, Trading Shenzhen, The Mobile Marvel; Amazon/AliExpress planned).

## Operating Context
- Visitors mostly arrive on phones, often from shared links (forums, social).
- Index page: brand chips + search reveal the phone list; store payment/shipping terms table below. Phone pages: per-store prices with Pay with / Ship to selectors and totals. Header holds the currency switch (USD/EUR/GBP/AUD); ship-to regions EU/UK/US/AU.
- Data is rebuilt hourly by GitHub Actions and deployed to Cloudflare Pages (pricechecker-87q.pages.dev).

## Capabilities and Constraints
- Static HTML from Jinja2 templates (`templates/`), one stylesheet and one script (`static/`); no server at request time, so all interactivity is client-side over prebuilt data.
- Phones compared by model + edition (Global/China) + RAM/storage. Prices shown in store-native currency where the store has one, otherwise ECB-converted and marked ≈.
- Totals carry caveats when a store's price excludes import tax ("excl. import tax") or doesn't say ("import tax not stated").
- Store terms are re-checked daily; a changed terms page is flagged "terms need review".
- Stores can be stale or failed; the UI must show that state, not hide it.
- Price history (`data/history.csv`) is shown per RAM/storage on phone pages and in full on /history/<model> pages.
- Undecided: Amazon/AliExpress integration (API credentials pending) and which DoorPrice domain to buy.

## Brand Commitments
- Name is **DoorPrice** (chosen 2026-10-19, replacing "PriceChecker"): the price at your door. Domains doorprice.app / .co were open on that date; the site still runs at pricechecker-87q.pages.dev until one is bought.
- Logo: [D]oorPrice - IBM Plex Sans Bold's own D with a door-phone in its counter: a rounded door whose glass is a phone screen (brand blue), handle as a side button, letterbox slot as a home bar; the name says door, the picture says phone (templates/_brand.html, tools/door_logo.py, static/icons/). "oor" in text colour, "Price" in brand blue.
- Mobile-first: every surface must work well at phone width before desktop.

## Evidence on Hand
- Real, hourly-updated prices and store terms (`data/latest.json`, `config/stores.yaml`, `config/import_tax.yaml`).
- No reviews, ratings, testimonials, user counts or press. Never fabricate these, and never claim "best deal" or similar beyond what the price data shows.

## Product Principles
1. **The number must be true.** Show what the visitor will really pay, and say plainly when part of it is estimated or unknown.
2. **Explain for newcomers.** Editions, import tax and payment fees are unfamiliar to mainstream buyers; make them understandable without slowing down people who already know.
3. **Data over persuasion.** Trust comes from accurate, fresh, transparent data, never from invented social proof.
4. **Phone first.** Designed for the device the visitor is shopping on.
