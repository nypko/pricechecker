# DoorPrice

(Repository and Cloudflare project are still named `pricechecker`; the checker identifies itself to stores as `PriceCheckerBot`.)

Static website that compares prices of flagship phones across stores, refreshed every hour, with affiliate links.

## How it works

```
GitHub Actions (hourly, .github/workflows/hourly.yml)
  └─ python -m pricechecker.run
       ├─ each store in config/stores.yaml  → current prices (Offer: model + edition + storage)
       ├─ data/latest.json   current prices per store (a failed store keeps its last prices, marked stale)
       ├─ data/history.csv   one row per price/stock CHANGE (committed to git = price history)
       ├─ data/*cache*.json  store exchange rates, robots.txt, Giztop product pages (committed, so runs stay light)
       └─ build/             static site (index + one page per phone, Global vs China side by side)
  └─ commit data/ → deploy build/ to Cloudflare Pages
```

Phones are compared like for like: **model + edition (Global / China version) + storage** (e.g. `16/512`).
Prices are shown in USD / EUR / GBP / AUD using **each store's own price in that currency** where it has one
(the same number a shopper sees after switching currency on the store), otherwise ECB rates, marked ≈.

## Store types

| Type | Used for | How |
|---|---|---|
| `shopify` | Wonda Mobile, The Mobile Marvel | public `/products.json`, asked once per currency (`?currency=`). Shopify allows ~1 request/min per IP across all shops, so requests are 2 min apart and a 429 is not retried until the next hour |
| `magento` | Giztop | walks the phone category (`?p=N`), reads per-variant prices from tracked phones' product pages; store currency rates via its header currency switch, once a day |
| `feed` | Trading Shenzhen (blocks scripts with HTTP 403) | an affiliate product feed URL (CSV or XML) – ask your affiliate contact |
| `official_api` | Amazon, AliExpress | API credentials (placeholders; client not written yet) |
| `webpage` | stores without a feed | product page URLs per phone in `config/catalog.yaml` (schema.org / price meta tags) |

The checker identifies itself honestly (`PriceCheckerBot`), obeys robots.txt and backs off when rate-limited.
It does not try to get around bot protection – for stores that block it, use the affiliate feed or API instead.

## Config

- `config/catalog.yaml` – phones on the site. Stores are matched by model id, any edition they sell is shown.
  `data/untracked.txt` lists models stores carry that aren't in the catalog.
- `config/stores.yaml` – stores, affiliate link templates (`{url}{sep}ref={id}`), payment/shipping terms per
  destination (`duties_included` = price already covers import tax), and pages re-checked daily for changes.
- `config/import_tax.yaml` – estimated VAT/GST per destination, added (≈) to totals when a store's price excludes it.

## Local use

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m pricechecker.run                  # all stores (exit 3 = no store answered)
.venv/bin/python -m pricechecker.run --only giztop
.venv/bin/python -m pricechecker.run --build-only     # rebuild the site from saved data
.venv/bin/python -m pricechecker.serve           # preview at http://127.0.0.1:8765, same URLs as Cloudflare
```

## Deploy (GitHub Actions + Cloudflare Pages)

GitHub Pages isn't used: its terms exclude sites "primarily directed at facilitating commercial transactions",
which an affiliate site is. Cloudflare Pages allows commercial use on the free plan.

1. Push this repo to GitHub (public: Actions minutes are free; a run takes ~15-20 min, ~12,000 min/month).
2. Cloudflare dashboard → My Profile → API Tokens → Create Token → *Custom token* with permission
   **Account · Cloudflare Pages · Edit**. Copy the token and your **Account ID** (Workers & Pages overview page).
3. GitHub repo → Settings → Secrets and variables → Actions → New repository secret:
   `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` (and later `TSZ_FEED_URL`).
   Optional repository *variable* `CF_PAGES_PROJECT` if the name `pricechecker` is taken on pages.dev.
4. Actions → "Hourly price check" → Run workflow. The first run creates the Pages project; the site is at
   `https://<project>.pages.dev`. A custom domain can be added in Cloudflare → Workers & Pages → the project → Custom domains.

## Buyer reports (delivery time and import tax, from real orders)

Two sources, each reviewed by hand before it counts (`pricechecker/buyer_reports.py`, weekly workflow `buyer-reports.yml`):

- **Reddit, official Data API only** (Reddit's robots.txt blocks crawlers, so no scraping). Create a "script" app at
  https://www.reddit.com/prefs/apps and request API access; then add repository secrets `REDDIT_CLIENT_ID`,
  `REDDIT_CLIENT_SECRET` and the variable `REDDIT_USERNAME`. First run: Actions → Weekly buyer reports → Run workflow
  with days = 62 to look two months back.
- **The form on each phone page** (`functions/api/report.js`, deployed with the site). In Cloudflare: Workers & Pages →
  KV → create a namespace (e.g. `doorprice-reports`); pricechecker → Settings → Bindings → add KV namespace binding
  `REPORTS`; Settings → Variables and secrets → add secret `REPORTS_ADMIN_KEY` (any long random string). Add the same
  value as the GitHub secret `REPORTS_ADMIN_KEY`.

New reports land in one GitHub issue, "Buyer reports to review". Open the links, then:

    python -m pricechecker.buyer_reports approve t1_abc123 f_1792...   # -> config/buyer_reports.yaml, shown on the site
    python -m pricechecker.buyer_reports reject t3_xyz789

and commit `config/buyer_reports.yaml` and `data/buyer_reports_*.json`. Only links, dates and the facts (country, days,
tax, amount, courier) are kept, never a post's text.

## Telegram price-drop channel

After each deploy, `python -m pricechecker.telegram` posts to a Telegram channel when a phone's cheapest delivered price
(shipping to the EU, card, in EUR: the number in its page title) drops by at least 3% and €20 from what the channel last
saw, and when a phone is new on the site. At most 5 messages per run; further drops go out as one digest. Each post links
the phone page, whose share card becomes the large preview. The first run only records prices.
`--dry` prints the messages instead of sending them. State: `data/telegram.json`.

Setup (once):
1. In Telegram, message **@BotFather** → `/newbot` → pick a name and a username ending in `bot`. Copy the token.
2. Create a **public channel** (e.g. `@doorprice`), open its settings → Administrators → add the bot, with "Post messages".
3. GitHub → repository Settings → Secrets and variables → Actions:
   - **Secret** `TELEGRAM_BOT_TOKEN` = the token
   - **Variable** `TELEGRAM_CHAT_ID` = `@yourchannel` (the channel's @username)

Until both are set the step does nothing.

## Still to do

1. **Affiliate links** – Wonda (`ref=`) and Trading Shenzhen (`affp=`) are set; The Mobile Marvel and Giztop still
   have `YOUR_..._ID` placeholders in `config/stores.yaml`. Until an id is set, the site uses plain links.
2. **Trading Shenzhen feed** – product feed URL from the affiliate account → GitHub secret `TSZ_FEED_URL`.
3. **Amazon / AliExpress** – API credentials as GitHub secrets, then implement `pricechecker/stores/official_api.py`.
