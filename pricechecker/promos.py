"""Daily promotion watch.

Layer 1 - detect: read each store's public pages (homepage banner by default) and pick out promotion wording
("2% summer sale", "use code X", "voucher"...). Text that wasn't there before is reported for a person to review;
nothing is applied automatically, because conditions (minimum order, which phones, stacking) need reading.

Layer 2 - expire: a promotion in stores.yaml (`terms.promo`) only counts while its `watch` text is still on the
store's pages and its optional `until` date hasn't passed. When the banner goes, the discount stops being applied.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import http

STATE = Path("data/promos.json")
REPORT = Path(".promo_report.md")   # picked up by the workflow and filed as a GitHub issue; not committed

PROMO = re.compile(r"\b\d{1,2}(?:[.,]\d+)?\s?%\s?(?:off|discount|rabatt)\b|\b(?:summer|winter|black friday|cyber|flash|mega|"
                   r"anniversary|holiday|singles'? day|11\.11|double 11)\s+(?:sale|deal|offer)s?\b|\bsale\b|\bdiscount\b|"
                   r"\bcoupons?\b|\bvouchers?\b|\bpromo(?:tion)? ?codes?\b|\buse (?:the )?code\b|\bcode\s*:?\s*[A-Z0-9]{4,}\b", re.I)


def pages(name: str, cfg: dict) -> list[str]:
    """Where a store announces promotions: `promo_pages` in stores.yaml, else its homepage."""
    if cfg.get("promo_pages"):
        return list(cfg["promo_pages"])
    return [cfg["base_url"].rstrip("/") + "/"] if cfg.get("base_url") else []


def text_of(html: str) -> list[str]:
    """Visible text of a page as short lines (scripts, styles and tags removed)."""
    html = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|span|a|section|header|footer|button)>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;|&#160;", " ", text).replace("&amp;", "&")
    lines = (re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n"))
    return [ln for ln in lines if ln]


def snippets(lines: list[str]) -> list[str]:
    """Lines that read like a promotion, shortened to 160 characters, without duplicates."""
    out = []
    for ln in lines:
        # menu items ("SALE", "Vouchers") are noise: keep lines of 3+ words, or any line with a % or a code
        if 3 <= len(ln) <= 300 and PROMO.search(ln) and (len(ln.split()) >= 3 or re.search(r"%|\bcode\b", ln, re.I)):
            s = ln if len(ln) <= 160 else ln[:157] + "..."
            if s not in out:
                out.append(s)
    return out[:25]


def promo_active(promo: dict, text: str | None, today: date) -> bool | None:
    """Is a configured promotion still running? None = couldn't tell (page not read) - keep the last answer."""
    until = promo.get("until")
    if until and today > (until if isinstance(until, date) else date.fromisoformat(str(until))):
        return False
    if not promo.get("watch"):
        return True          # no banner to watch: trust the config (and `until`)
    if text is None:
        return None
    return re.search(promo["watch"], text, re.I) is not None


def scan(stores_cfg: dict, force: bool = False) -> dict:
    """Once a day: read promotion pages, record what's there, decide which configured promotions still run,
    and write a report of anything new or ended. Returns the saved state."""
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = datetime.now(timezone.utc)
    last = state.get("_checked")
    if not force and last and now - datetime.fromisoformat(last) < timedelta(hours=20):
        return state
    first_run = not any(k for k in state if not k.startswith("_"))
    new_found, ended, started = {}, [], []
    for name, cfg in stores_cfg.items():
        if not cfg.get("enabled", True) or cfg.get("part_of"):
            continue
        urls = pages(name, cfg)
        if not urls:
            continue
        if cfg.get("type") == "shopify":
            from .stores.shopify import _space_requests
            _space_requests(cfg["base_url"].rstrip("/"))
        texts, errors = [], []
        for u in urls:
            try:
                texts.append("\n".join(text_of(http.get(u).text)))
            except Exception as e:
                errors.append(f"{u}: {type(e).__name__}")
        prev = state.get(name, {})
        found = snippets("\n".join(texts).split("\n")) if texts else []
        seen = set(prev.get("seen", []))
        fresh = [s for s in found if s not in seen]
        if fresh:
            new_found[name] = fresh
        rec = {"seen": sorted(seen | set(found)), "current": found if texts else prev.get("current", []),
               "checked": now.isoformat(timespec="seconds"), "errors": errors}
        promo = (cfg.get("terms") or {}).get("promo")
        if promo:
            active = promo_active(promo, "\n".join(texts) if texts else None, now.date())
            was = prev.get("promo_active")
            rec["promo_active"] = was if active is None else active
            if was is not None and active is not None and was != active:
                (started if active else ended).append(f"{cfg.get('label', name)}: {promo.get('label', 'promotion')} "
                                                      f"({promo.get('pct')}%) {'is back' if active else 'has ended'}")
        state[name] = rec
        print(f"  [promos] {name}: {len(found)} promotion lines, {len(fresh)} new"
              + (f", promo {'active' if rec.get('promo_active') else 'inactive'}" if promo else "")
              + (f", errors: {'; '.join(errors)}" if errors else ""))
    state["_checked"] = now.isoformat(timespec="seconds")
    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False))
    write_report(new_found, ended, started, stores_cfg, first_run)
    return state


def write_report(new_found: dict, ended: list, started: list, stores_cfg: dict, first_run: bool) -> None:
    if not (new_found or ended or started):
        if REPORT.exists():
            REPORT.unlink()
        return
    out = []
    if first_run:
        out += ["Promotion watch started. This is the promotion wording on each store's pages right now - "
                "from now on only changes are reported.", ""]
    if ended or started:
        out += ["## Configured promotions", ""] + [f"- {x}" for x in ended + started] + [
            "", "Totals already follow this. If the promotion is over for good, remove `promo:` from the store "
                "in `config/stores.yaml`.", ""]
    if new_found:
        out += ["## New promotion text", ""]
        for name, lines in new_found.items():
            cfg = stores_cfg[name]
            out += [f"**{cfg.get('label', name)}** ({', '.join(pages(name, cfg))})", ""] + [f"- {s}" for s in lines] + [""]
        out += ["To count an automatic store-wide discount in totals, add it to the store in `config/stores.yaml`:",
                "", "```yaml", "      promo: {pct: 2, label: \"Summer sale\", watch: \"2% summer sale\", until: 2026-10-31,",
                "              stacks_with_bank: false, note: \"Applied automatically at checkout.\"}", "```", "",
                "Codes the shopper has to type, minimum orders or single-product deals are better left out of totals."]
    REPORT.write_text("\n".join(out) + "\n")


def active(name: str, cfg: dict, state: dict | None = None) -> bool:
    """Should this store's configured promotion count in totals right now? Past its `until` date: no.
    Otherwise the last scan's answer; never scanned yet: trust the config."""
    promo = (cfg.get("terms") or {}).get("promo")
    if not promo or promo_active({**promo, "watch": None}, None, date.today()) is False:
        return False
    if state is None:
        state = json.loads(STATE.read_text()) if STATE.exists() else {}
    known = (state.get(name) or {}).get("promo_active")
    return True if known is None else bool(known)
