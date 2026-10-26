"""What search engines and feed readers get: robots.txt, sitemap.xml, Atom feeds of price changes, schema.org Product
data, and the cheapest delivered price used in page titles. Files come back as {relative path: text}; build() writes them."""
import json
from datetime import datetime
from xml.sax.saxutils import escape

from .. import pricing
from .common import spec


def _feeds(site_cfg: dict, phones: list[dict], rows: list[dict], stores_cfg: dict, updated_at: datetime | None) -> dict[str, str]:
    """Atom feeds of price changes, so people can follow a phone without an account: feeds/<slug>.xml per phone and
    feeds/all.xml for every phone. Each entry is one store price change, in the store's own currency, with the price before."""
    base = (site_cfg.get("base_url") or "https://doorprice.app").rstrip("/")
    names = {p["id"]: p["name"] for p in phones}
    labels = {p["id"]: p["ed_label"] for p in phones}
    sym = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "C$", "AUD": "A$", "HKD": "HK$"}
    money = lambda v, c: f"{sym.get(c, c + ' ')}{v:,.0f}"
    last: dict[tuple, dict] = {}
    entries = []
    for r in rows:   # oldest first: each change knows the price before it
        if r["model_id"] not in names:
            continue
        key = (r["store"], r["model_id"], r["edition"], r["storage"])
        prev = last.get(key)
        if prev is None or (r["available"] == prev["available"] and abs(r["price"] - prev["price"]) < prev["price"] * 0.005):
            last.setdefault(key, r)   # currency-rounding moves (a store re-converting its prices) aren't news
            continue
        last[key] = r
        label = stores_cfg.get(r["store"], {}).get("label", r["store"])
        what = f"{names[r['model_id']]} {labels[r['model_id']][r['edition']]}" + (f" {spec(r['storage'])}" if "/" in r["storage"] else "")
        if r["available"] and not prev["available"]:
            change = f"back in stock at {money(r['price'], r['currency'])}"
        elif not r["available"]:
            change = "out of stock"
        elif r["price"] < prev["price"]:
            change = f"down to {money(r['price'], r['currency'])} (was {money(prev['price'], prev['currency'])})"
        else:
            change = f"up to {money(r['price'], r['currency'])} (was {money(prev['price'], prev['currency'])})"
        entries.append({"model": r["model_id"], "time": r["time"], "title": f"{what} at {label}: {change}",
                        "id": f"{base}/history/{r['model_id']}#{r['time']}-{r['store']}-{r['edition']}-{r['storage']}"})
    entries.reverse()   # newest first

    def feed(title: str, link: str, items: list[dict]) -> str:
        stamp = items[0]["time"] if items else (f"{updated_at:%Y-%m-%dT%H:%M:%SZ}" if updated_at else "2026-01-01T00:00:00Z")
        body = "".join(f"<entry><title>{escape(e['title'])}</title><id>{escape(e['id'])}</id><updated>{e['time']}</updated>"
                       f'<link href="{escape(base)}/history/{e["model"]}"/></entry>' for e in items[:50])
        return ('<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">'
                f"<title>{escape(title)}</title><id>{escape(link)}</id><updated>{stamp}</updated>"
                f'<link href="{escape(link)}"/><author><name>DoorPrice</name></author>{body}</feed>\n')
    out = {}
    for ph in phones:
        out[f"feeds/{ph['slug']}.xml"] = feed(f"{ph['name']} price changes – DoorPrice", f"{base}/phones/{ph['slug']}",
                                              [e for e in entries if e["model"] == ph["id"]])
    out["feeds/all.xml"] = feed("Phone price changes – DoorPrice", f"{base}/", entries)
    return out


def _seo_files(site_cfg: dict, phones: list[dict], store_names: list[str] = ()) -> dict[str, str]:
    """robots.txt and sitemap.xml for search engines; the sitemap lists absolute URLs, so only once the domain is live."""
    base = (site_cfg.get("base_url") or "").rstrip("/")
    live = bool(site_cfg.get("domain_live") and base)
    if site_cfg.get("testing"):   # the testing copy must never be indexed
        return {"robots.txt": "User-agent: *\nDisallow: /\n"}
    # AI crawlers that collect pages to train models (and send no visitors) are asked to stay out; search engines,
    # AI search assistants that link their sources (OAI-SearchBot, ChatGPT-User, PerplexityBot, Claude-SearchBot...)
    # and link-preview fetchers (Telegram, Reddit, WhatsApp, Facebook) keep full access under "*".
    training = ["GPTBot", "ClaudeBot", "anthropic-ai", "CCBot", "Google-Extended", "Applebot-Extended", "Bytespider",
                "meta-externalagent", "cohere-training-data-crawler", "Diffbot", "Omgilibot", "ImagesiftBot"]
    robots = ("".join(f"User-agent: {b}\n" for b in training) + "Disallow: /\n\n"
              "User-agent: *\nAllow: /\n" + (f"\nSitemap: {base}/sitemap.xml\n" if live else ""))
    out = {"robots.txt": robots}
    if not live:
        return out
    paths = ["", "compare", "stores", "methodology", "about", "privacy"] + [f"stores/{n}" for n in store_names] + [f"phones/{p['slug']}" for p in phones] + [f"history/{p['slug']}" for p in phones]
    urls = "".join(f"<url><loc>{base}/{p}</loc></url>" for p in paths)
    out["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    return out


def _product_ld(model: dict, in_stock: list[dict], site_cfg: dict) -> str:
    """schema.org Product + AggregateOffer for search results ("from €X · N offers"): the stores' own prices in EUR
    (what the store charges, as search engines expect), not our delivered totals. Empty when nothing is in stock."""
    if not in_stock:
        return ""
    eur = [o["money"]["eur"] for o in in_stock]
    ld = {"@context": "https://schema.org", "@type": "Product", "name": model["name"], "brand": {"@type": "Brand", "name": model["brand"]},
          "offers": {"@type": "AggregateOffer", "priceCurrency": "EUR", "lowPrice": f"{min(eur):.2f}", "highPrice": f"{max(eur):.2f}",
                     "offerCount": len(in_stock)}}
    base = (site_cfg.get("base_url") or "").rstrip("/")
    if site_cfg.get("domain_live") and base:
        ld["url"] = f"{base}/phones/{model['id']}"
        ld["image"] = f'{base}/cards/{model["id"]}.png'   # the phone's share card (name, versions, delivered price)
    return json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _title_price(offers: list[dict], tax_cfg: dict, with_offer: bool = False) -> tuple | None:
    """Cheapest total for the page title and search snippet: what the phone page puts first for shipping to the EU,
    paying by card, in EUR, at the EU-average import VAT (pricing.rank, the page's own ranking - a complete total
    first, then fewer unknowns, then the lower total). Returns (total, complete, left out): complete = shipping known
    and import tax settled either way, left out = "shipping", "import tax" or "shipping and import tax" when it isn't.
    An old price or a store that refuses card never leads it (None when only such offers are left).
    with_offer: (total, complete, left out, the offer) - for the deals list the Telegram channel posts from."""
    s = pricing.Settings("EU", "", "card", "eur")
    ranked = pricing.rank(offers, s, pricing.tax_rule(tax_cfg, s), with_base=True)   # the page has a "not listed" row
    o, k = next(((o, k) for o, k in ranked if k.pay_ok and not k.old), (None, None))   # ranked first when present
    if o is None:
        return None
    left = pricing.left_out(k)
    return (k.total, not left, left) + ((o,) if with_offer else ())
