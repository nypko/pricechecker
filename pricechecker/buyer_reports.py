"""Buyer reports: how long orders really took to arrive and whether import tax was charged.

Two sources, both reviewed by hand before anything reaches the site:
  - Reddit, through the official Data API only (app credentials in REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / REDDIT_USERNAME).
    No page scraping: Reddit's robots.txt disallows crawlers.
  - The "How did your order arrive?" form on DoorPrice (functions/api/report.js stores them in Cloudflare KV;
    REPORTS_URL + REPORTS_ADMIN_KEY let this module read them back).

    python -m pricechecker.buyer_reports collect [--days 62]   # find new reports -> data/buyer_reports_pending.json + .buyer_report.md
    python -m pricechecker.buyer_reports approve ID [ID ...]    # move to config/buyer_reports.yaml (shown on the site)
    python -m pricechecker.buyer_reports reject ID [ID ...]     # drop, and never suggest again

Only links, dates and the parsed facts are kept, never the text of a post, so we don't republish anyone's words.
"""
import base64
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

PENDING = Path("data/buyer_reports_pending.json")
SEEN = Path("data/buyer_reports_seen.json")       # approved or rejected ids: never suggested again
APPROVED = Path("config/buyer_reports.yaml")
REPORT = Path(".buyer_report.md")
UA = "PriceCheckerBot/1.0 (DoorPrice buyer reports; https://doorprice.app/about)"

EU = {"AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia", "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark",
      "EE": "Estonia", "FI": "Finland", "FR": "France", "DE": "Germany", "GR": "Greece", "HU": "Hungary", "IE": "Ireland",
      "IT": "Italy", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands", "PL": "Poland",
      "PT": "Portugal", "RO": "Romania", "SK": "Slovakia", "SI": "Slovenia", "ES": "Spain", "SE": "Sweden"}
OTHER = {"GB": "United Kingdom", "US": "United States", "AU": "Australia", "CA": "Canada", "CH": "Switzerland", "NO": "Norway",
         "NZ": "New Zealand", "IN": "India", "SG": "Singapore", "AE": "United Arab Emirates", "IL": "Israel", "TR": "Turkey",
         "UA": "Ukraine", "RS": "Serbia", "JP": "Japan", "BR": "Brazil", "MX": "Mexico", "ZA": "South Africa", "XX": "Other country"}
COUNTRIES = {**EU, **OTHER}
COURIERS = ["Global Priority", "EU warehouse", "DHL", "UPS", "FedEx", "Royal Mail", "USPS", "PostNL", "Aramex", "SF Express", "EMS"]


def region_of(code: str) -> str:
    return "EU" if code in EU else {"GB": "UK", "US": "US", "CA": "CA", "AU": "AU"}.get(code, "Global")


# ---------- reading a post ----------
_ALIASES = {"uk": "GB", "britain": "GB", "england": "GB", "scotland": "GB", "usa": "US", "u.s.": "US", "america": "US",
            "states": "US", "holland": "NL", "czech republic": "CZ", "aussie": "AU", "deutschland": "DE"}
_NAMES = sorted([(n.lower(), c) for c, n in COUNTRIES.items() if c != "XX"] + list(_ALIASES.items()), key=lambda x: -len(x[0]))
_TAXWORD = r"(?:customs|import (?:tax|vat|fees?|duty)|vat|duty|duties|taxes|tax|gst)"
_NO_TAX = re.compile(rf"\b(?:no|didn'?t (?:have to )?pay|did not (?:have to )?pay|without|zero|0)\b[^.!?\n]{{0,25}}\b{_TAXWORD}\b"
                     rf"|\b{_TAXWORD}\b[^.!?\n]{{0,20}}\b(?:free|included|covered|paid by (?:the )?(?:seller|store)|none)\b", re.I)
_TAX = re.compile(rf"\b(?:paid|pay|charged|had to pay|got hit|billed|asked (?:me )?(?:to pay|for))\b[^.!?\n]{{0,40}}\b{_TAXWORD}\b"
                  rf"|\b{_TAXWORD}\b[^.!?\n]{{0,25}}\b(?:of|was|were|cost|came to)\b[^.!?\n]{{0,10}}\d", re.I)
_MONEY = re.compile(r"(€|eur|euros?|£|gbp|c\$|cad|\$|usd|aud|a\$)\s?(\d{1,4}(?:[.,]\d{1,2})?)|(\d{1,4}(?:[.,]\d{1,2})?)\s?(€|eur\b|euros?\b|£|gbp\b|cad\b|usd\b|aud\b|\$)", re.I)
_DAYS = re.compile(r"\b(\d{1,2})\s*(?:business |working |calendar )?(days?|weeks?)\b", re.I)
_DELIVERY = re.compile(r"\b(?:arriv|deliver|receiv|took|got it|got my|came|shipping|shipped|transit|to get here|door)", re.I)


def _currency(sym: str) -> str:
    s = sym.lower()
    return "EUR" if s in ("€", "eur", "euro", "euros") else "GBP" if s in ("£", "gbp") else "AUD" if s in ("aud", "a$") else "CAD" if s in ("cad", "c$") else "USD"


def parse(text: str) -> dict:
    """The facts a buyer's post gives, if any: days to arrive, import tax charged (True/False) and how much,
    destination country and courier. Fields it can't find are left out. Every result is checked by a person."""
    out: dict = {}
    low = f" {text.lower()} "
    for name, code in _NAMES:
        if re.search(rf"\b{re.escape(name)}\b", low):
            out["country"] = code
            break
    for c in COURIERS:
        if re.search(rf"\b{re.escape(c)}\b", text, re.I):
            out["courier"] = c
            break
    for m in _DAYS.finditer(text):   # "arrived in 9 days", "took 3 weeks to get here"
        window = text[max(0, m.start() - 60): m.end() + 40]
        if _DELIVERY.search(window):
            n = int(m.group(1)) * (7 if m.group(2).lower().startswith("week") else 1)
            if 1 <= n <= 90:
                out["days"] = n
                break
    if _NO_TAX.search(text):
        out["tax"] = False
    elif (t := _TAX.search(text)):
        out["tax"] = True
        near = text[max(0, t.start() - 40): t.end() + 50]
        if (m := _MONEY.search(near)):
            sym, num = (m.group(1), m.group(2)) if m.group(2) else (m.group(4), m.group(3))
            out["amount"], out["currency"] = float(num.replace(",", ".")), _currency(sym)
    return out


def useful(facts: dict) -> bool:
    return "days" in facts or "tax" in facts


# ---------- Reddit (official Data API) ----------
def _reddit_token() -> str | None:
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        return None
    req = urllib.request.Request("https://www.reddit.com/api/v1/access_token", data=b"grant_type=client_credentials",
                                 headers={"User-Agent": _reddit_ua(), "Authorization": "Basic " + base64.b64encode(f"{cid}:{secret}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("access_token")


def _reddit_ua() -> str:
    user = os.environ.get("REDDIT_USERNAME", "")
    return UA + (f" by u/{user}" if user else "")   # Reddit asks for the app owner's username in the user agent


def _reddit_get(token: str, path: str, params: dict) -> dict | list:
    url = "https://oauth.reddit.com" + path + "?" + urllib.parse.urlencode({**params, "raw_json": 1})
    req = urllib.request.Request(url, headers={"User-Agent": _reddit_ua(), "Authorization": f"bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        left = r.headers.get("X-Ratelimit-Remaining")
        out = json.load(r)
    time.sleep(1.0 if left is None or float(left) > 10 else 10)   # stay well inside the API's per-minute allowance
    return out


def reddit_reports(stores_cfg: dict, since: datetime) -> list[dict]:
    """Posts that name one of our stores (search, newest first, back to `since`), plus the replies in those threads,
    kept when they report delivery time or import tax."""
    token = _reddit_token()
    if not token:
        print("  buyer reports: no Reddit API credentials, skipping Reddit")
        return []
    found = []
    for store, cfg in stores_cfg.items():
        for name in cfg.get("mentions") or []:
            after = None
            while True:
                page = _reddit_get(token, "/search", {"q": f'"{name}"', "sort": "new", "t": "year", "limit": 100, "type": "link",
                                                      **({"after": after} if after else {})})
                posts = [c["data"] for c in page["data"]["children"]]
                for p in posts:
                    when = datetime.fromtimestamp(p["created_utc"], timezone.utc)
                    if when < since:
                        continue
                    text = f"{p.get('title', '')}\n{p.get('selftext', '')}"
                    if name.lower() not in text.lower():
                        continue
                    base = {"store": store, "source": "reddit", "subreddit": p.get("subreddit"), "thread": "https://www.reddit.com" + p["permalink"]}
                    facts = parse(text)
                    if useful(facts):
                        found.append({**base, **facts, "id": "t3_" + p["id"], "url": base["thread"], "date": f"{when:%Y-%m-%d}"})
                    found += _replies(token, p, base, since)
                after = page["data"].get("after")
                if not after or not posts or datetime.fromtimestamp(posts[-1]["created_utc"], timezone.utc) < since:
                    break
    return found


def _replies(token: str, post: dict, base: dict, since: datetime) -> list[dict]:
    out = []
    listing = _reddit_get(token, f"/comments/{post['id']}", {"limit": 200, "depth": 3, "sort": "new"})
    stack = [c for c in listing[1]["data"]["children"]] if isinstance(listing, list) and len(listing) > 1 else []
    while stack:
        c = stack.pop()
        if c.get("kind") != "t1":
            continue
        d = c["data"]
        when = datetime.fromtimestamp(d.get("created_utc", 0), timezone.utc)
        facts = parse(d.get("body", ""))
        if when >= since and useful(facts):
            out.append({**base, **facts, "id": "t1_" + d["id"], "url": "https://www.reddit.com" + d.get("permalink", ""), "date": f"{when:%Y-%m-%d}"})
        replies = d.get("replies")
        if isinstance(replies, dict):
            stack += replies["data"]["children"]
    return out


# ---------- the DoorPrice form ----------
def form_reports(since: datetime) -> list[dict]:
    url, key = os.environ.get("REPORTS_URL"), os.environ.get("REPORTS_ADMIN_KEY")
    if not (url and key):
        print("  buyer reports: REPORTS_URL / REPORTS_ADMIN_KEY not set, skipping form reports")
        return []
    req = urllib.request.Request(f"{url.rstrip('/')}/api/reports?since={int(since.timestamp() * 1000)}",
                                 headers={"Authorization": f"Bearer {key}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        rows = json.load(r).get("reports", [])
    out = []
    for r in rows:
        facts = {k: r[k] for k in ("country", "days", "tax", "amount", "currency", "courier") if r.get(k) not in (None, "")}
        out.append({"id": "f_" + r["key"], "store": r["store"], "source": "form", "phone": r.get("phone"), **facts,
                    "date": datetime.fromtimestamp(r["ts"] / 1000, timezone.utc).strftime("%Y-%m-%d")})
    return out


# ---------- review queue ----------
def _load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def collect(stores_cfg: dict, days: int = 7) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    pending, seen = _load(PENDING, {}), set(_load(SEEN, []))
    new = [r for r in reddit_reports(stores_cfg, since) + form_reports(since) if r["id"] not in pending and r["id"] not in seen]
    for r in new:
        if r.get("courier") == "EU warehouse" and r["store"] == "tradingshenzhen":
            r["store"] = "tradingshenzhen_eu"
        pending[r["id"]] = r
    PENDING.parent.mkdir(exist_ok=True)
    PENDING.write_text(json.dumps(pending, indent=1, sort_keys=True) + "\n")
    if new:
        REPORT.write_text(_markdown(new, stores_cfg))
    elif REPORT.exists():
        REPORT.unlink()
    print(f"  buyer reports: {len(new)} new, {len(pending)} waiting for review")
    return len(new)


def _markdown(rows: list[dict], stores_cfg: dict) -> str:
    lines = ["New buyer reports. Open each link, check the facts below match what the buyer said, then run",
             "`python -m pricechecker.buyer_reports approve <id> ...` (or `reject`). Approved reports appear on the site as",
             "counts and ranges next to the store's own delivery promise.", "",
             "| id | store | date | where | days | import tax | courier | source |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["store"], r["date"])):
        tax = "" if "tax" not in r else ("yes" + (f" {r['amount']:g} {r['currency']}" if r.get("amount") else "") if r["tax"] else "no")
        where = COUNTRIES.get(r.get("country", ""), "")
        src = f"[r/{r['subreddit']}]({r['url']})" if r["source"] == "reddit" else f"form ({r.get('phone') or 'phone not given'})"
        lines.append(f"| `{r['id']}` | {stores_cfg.get(r['store'], {}).get('label', r['store'])} | {r['date']} | {where} | "
                     f"{r.get('days', '')} | {tax} | {r.get('courier', '')} | {src} |")
    return "\n".join(lines) + "\n"


def decide(ids: list[str], approve: bool) -> None:
    pending, seen = _load(PENDING, {}), set(_load(SEEN, []))
    approved = (yaml.safe_load(APPROVED.read_text()) or {}).get("reports", []) if APPROVED.exists() else []
    for i in ids:
        r = pending.pop(i, None)
        if r is None:
            print(f"  {i}: not in the review queue")
            continue
        seen.add(i)
        if approve:
            approved.append({k: r[k] for k in ("id", "store", "date", "country", "days", "tax", "amount", "currency", "courier", "source", "url")
                             if r.get(k) is not None})
            print(f"  {i}: approved")
        else:
            print(f"  {i}: rejected")
    PENDING.write_text(json.dumps(pending, indent=1, sort_keys=True) + "\n")
    SEEN.write_text(json.dumps(sorted(seen), indent=0) + "\n")
    APPROVED.write_text(_HEADER + yaml.safe_dump({"reports": approved}, sort_keys=False, allow_unicode=True, width=200))


_HEADER = """# Buyer reports approved for the site (python -m pricechecker.buyer_reports approve ...). Each is one order:
# store, date reported, destination country (ISO code), days to arrive, import tax charged on delivery, courier, source.
# The site shows them per store and Ship-to region as counts and ranges (reports from the last 12 months).
"""


# ---------- for the site ----------
def summary(now: datetime | None = None) -> dict:
    """{store: {region: {"n": 12, "dmin": 8, "dmax": 21, "dmed": 11, "tk": 10, "tx": 3}}} from approved reports in the last
    12 months: n reports, delivery days range and median, how many said whether tax was charged (tk) and how many paid (tx)."""
    if not APPROVED.exists():
        return {}
    now = now or datetime.now(timezone.utc)
    groups: dict = {}
    for r in (yaml.safe_load(APPROVED.read_text()) or {}).get("reports", []):
        when = datetime.strptime(str(r["date"]), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if now - when > timedelta(days=365) or not r.get("country"):
            continue
        groups.setdefault(r["store"], {}).setdefault(region_of(r["country"]), []).append(r)
    out: dict = {}
    for store, by_region in groups.items():
        for region, rs in by_region.items():
            days = [r["days"] for r in rs if r.get("days")]
            known = [r for r in rs if r.get("tax") is not None]
            out.setdefault(store, {})[region] = {"n": len(rs), "dmin": min(days) if days else None, "dmax": max(days) if days else None,
                                                 "dmed": round(statistics.median(days)) if days else None, "nd": len(days),
                                                 "tk": len(known), "tx": sum(1 for r in known if r["tax"])}
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["collect"]:
        n = int(args[args.index("--days") + 1]) if "--days" in args else 7
        stores = yaml.safe_load(Path("config/stores.yaml").read_text())["stores"]
        collect({k: v for k, v in stores.items() if v.get("enabled", True)}, n)
    elif args[:1] in (["approve"], ["reject"]) and len(args) > 1:
        decide(args[1:], args[0] == "approve")
    else:
        print(__doc__)
        sys.exit(2)
