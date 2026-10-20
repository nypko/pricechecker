"""Telegram channel of price drops: after each deploy, post the phones whose cheapest delivered price (shipping to the EU,
paying by card, in EUR - the number in each phone page's title) has really dropped, and phones new on the site.
`python -m pricechecker.telegram [--dry]`

Reads build/deals.json (written by site.build) and keeps what the channel last saw in data/telegram.json:
  ref   - the price a drop is measured from: the price at the last post, raised whenever the price goes up since
  left  - what that price leaves out ("", "import tax", ...); when it changes the totals aren't comparable, so ref resets
A drop is posted when it is at least MIN_PCT and MIN_EUR below ref. At most MAX_POSTS messages per run; more drops go out
as one digest. The first run only records prices (no flood of "drops"). Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
(@channelname or its numeric id); without them it does nothing. Never fails the job: errors are only logged."""
import json
import os
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import requests
import yaml

DEALS = Path("build/deals.json")
STATE = Path("data/telegram.json")
MIN_PCT, MIN_EUR, MAX_POSTS = 0.03, 20, 5


def spec(storage: str) -> str:
    """'12/256' -> '12 GB + 256 GB', '16/1024' -> '16 GB + 1 TB'."""
    if "/" not in storage:
        return ""
    ram, rom = (int(x) for x in storage.split("/"))
    return f"{ram} GB + " + (f"{rom // 1024} TB" if rom >= 1024 else f"{rom} GB")


def price_line(d: dict) -> str:
    """"€987 delivered to the EU" / "€1,145 + import tax, delivered to the EU" / "€875 + shipping and import tax, to the EU"."""
    p = f"€{d['eur']:,.0f}"
    if not d["left"]:
        return f"<b>{p}</b> delivered to the EU"
    return f"<b>{p}</b> + {d['left']}, " + ("to the EU" if "shipping" in d["left"] else "delivered to the EU")


def what(d: dict) -> str:
    return " · ".join(x for x in (f"{d['edition']} version", spec(d["storage"]), d["store"]) if x)


def changes(deals: list[dict], state: dict) -> tuple[list[dict], list[dict], dict]:
    """(drops, new phones, next state). Pure: no network, so it can be tested."""
    first_run = not state
    drops, new, nxt = [], [], {}
    for d in deals:
        s = state.get(d["slug"])
        if s is None:
            nxt[d["slug"]] = {"ref": d["eur"], "left": d["left"]}
            if not first_run:
                new.append(d)
            continue
        ref = s["ref"]
        if s["left"] != d["left"]:          # what the total covers changed (e.g. shipping became known): start over
            nxt[d["slug"]] = {"ref": d["eur"], "left": d["left"]}
        elif ref - d["eur"] >= max(MIN_EUR, ref * MIN_PCT):
            drops.append({**d, "was": ref})
            nxt[d["slug"]] = {"ref": d["eur"], "left": d["left"]}
        else:                               # up: measure the next drop from the higher price; small dips keep ref
            nxt[d["slug"]] = {"ref": max(ref, d["eur"]), "left": d["left"]}
    for slug, s in state.items():           # a phone gone from the site (out of stock everywhere) keeps its last ref
        nxt.setdefault(slug, s)
    drops.sort(key=lambda d: (d["eur"] - d["was"]) / d["was"])   # biggest drop first
    return drops, new, nxt


def drop_message(d: dict, base: str) -> str:
    cut = round(d["was"]) - round(d["eur"])   # from the figures shown, so "was €1,213, now €1,145" says −€68
    return (f"📉 <b>{escape(d['name'])}</b>\n"
            f"Now from {price_line(d)}\n"
            f"was €{d['was']:,.0f}: −€{cut:,.0f} (−{cut / d['was'] * 100:.0f}%)\n"
            f"{escape(what(d))}\n"
            f"<a href=\"{base}/phones/{d['slug']}\">Compare {d['n_stores']} store{'s' if d['n_stores'] != 1 else ''} →</a>")


def new_message(d: dict, base: str) -> str:
    return (f"🆕 <b>{escape(d['name'])}</b> is now on DoorPrice\n"
            f"From {price_line(d)}\n"
            f"{escape(what(d))}\n"
            f"<a href=\"{base}/phones/{d['slug']}\">Compare {d['n_stores']} store{'s' if d['n_stores'] != 1 else ''} →</a>")


def digest_message(items: list[dict], base: str) -> str:
    lines = [f"📉 <b>{len(items)} more price drops</b>"]
    for d in items:
        lines.append(f"• <a href=\"{base}/phones/{d['slug']}\">{escape(d['name'])}</a>: €{d['eur']:,.0f} (was €{d['was']:,.0f})")
    return "\n".join(lines)


def send(token: str, chat: str, text: str, preview_url: str | None) -> None:
    body = {"chat_id": chat, "text": text, "parse_mode": "HTML"}
    # the phone page's share card as a large preview; a digest has no single page to preview
    body["link_preview_options"] = {"url": preview_url, "prefer_large_media": True} if preview_url else {"is_disabled": True}
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=body, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Telegram {r.status_code}: {r.text[:200]}")


def main(argv=None) -> int:
    dry = "--dry" in (argv if argv is not None else sys.argv[1:])
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat) and not dry:
        print("  [telegram] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set: skipped")
        return 0
    if not DEALS.exists():
        print("  [telegram] no build/deals.json: skipped")
        return 0
    site = yaml.safe_load(Path("config/site.yaml").read_text()) or {}
    base = (site.get("base_url") or "https://doorprice.app").rstrip("/")
    deals = json.loads(DEALS.read_text())["phones"]
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    old = state.get("phones", {})
    drops, new, nxt = changes(deals, old)
    # (text, preview page, phones it covers); new phones beyond MAX_POSTS are simply recorded
    posts = [(drop_message(d, base), f"{base}/phones/{d['slug']}", [d["slug"]]) for d in drops[:MAX_POSTS]]
    posts += [(new_message(d, base), f"{base}/phones/{d['slug']}", [d["slug"]]) for d in new[:MAX_POSTS]]
    if len(drops) > MAX_POSTS:
        posts.append((digest_message(drops[MAX_POSTS:], base), None, [d["slug"] for d in drops[MAX_POSTS:]]))
    print(f"  [telegram] {len(drops)} drops, {len(new)} new phones, {len(posts)} messages" + (" (first run: prices recorded)" if not state else ""))
    sent = 0
    for text, url, slugs in posts:
        if dry:
            print("---\n" + text)
            continue
        try:
            send(token, chat, text, url)
            sent += 1
        except Exception as e:   # keep going; the phones in a failed message keep their old state, so it goes out next run
            print(f"  [telegram] send failed: {e}")
            for slug in slugs:
                if slug in old:
                    nxt[slug] = old[slug]
                else:
                    nxt.pop(slug, None)
    if not dry:
        STATE.write_text(json.dumps({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "phones": nxt},
                                    indent=1, sort_keys=True))
        print(f"  [telegram] {sent} sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
