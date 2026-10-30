"""The delivered-total rule: one phone offer plus the visitor's settings -> what it costs to get it.

This is the single definition. static/js/pricing.js has a line-for-line mirror (cost1, taxRule1, unknowns, better) and
tests/fixtures/pricing_cases.json holds the cases both must agree on. No I/O here: offers and tax config come in as
the dicts site.build already makes."""
from dataclasses import dataclass
from typing import NamedTuple


class Settings(NamedTuple):
    region: str   # EU, UK, US, CA, AU or Global
    area: str     # EU country code, CA province code, or "" when none is picked (the region's own rate applies)
    pay: str      # card, paypal or bank
    cur: str      # lowercase display currency, e.g. "eur"


class TaxRule(NamedTuple):
    rate: float | None   # percent; None = no estimate for this destination
    name: str
    fee: dict | None     # the courier's clearance fee {pct, min, by, min_m: {eur, gbp, ...}}, where published
    ship_taxed: bool


@dataclass
class Cost:
    list: float
    promo_amt: float
    promo_pct: float
    base: float
    adj: float | None        # payment adjustment in percent; None = the store's fee is unknown
    adj_amt: float
    ship: float | None       # None = the store doesn't list shipping to this region
    ship_min: bool
    tax_est: float | None
    tax_added: float
    total: float
    approx: bool
    complete: bool
    pay_ok: bool
    old: bool
    duties: bool | None


def tax_rule(tax_cfg: dict, s: Settings) -> TaxRule:
    """The import tax rule for the chosen destination. EU: the picked country's VAT and, where the courier publishes
    it, its clearance fee; no country picked: the EU average."""
    t = tax_cfg.get(s.region) or {}
    c = (t.get("countries") or {}).get(s.area) if s.region == "EU" else None
    ship_taxed = t.get("ship_taxed") is not False   # Canada taxes the phone only, not the international shipping
    if s.region == "CA" and (t.get("provinces") or {}).get(s.area):
        return TaxRule(t["provinces"][s.area]["rate"], t["provinces"][s.area]["tax"], None, ship_taxed)
    if not c:
        return TaxRule(t.get("rate_pct"), t.get("name") or "import tax", None, ship_taxed)
    return TaxRule(c["vat"], "import VAT", c.get("fee") or None, True)


def cost(o: dict, s: Settings, rule: TaxRule) -> Cost:
    """Total for one offer under the chosen currency / payment / region, as landed cost:
    store price +/- payment adjustment + shipping + estimated import VAT/GST when the store's price excludes it.
    pay% unknown -> treated as 0 but flagged; shipping unknown -> excluded from total but flagged;
    import tax not stated by the store -> shown as a possible amount but not added."""
    c = s.cur
    lst, adj, ship = o["money"][c], (o.get("pay") or {}).get(s.pay), (o.get("ship") or {}).get(s.region)
    # store-wide automatic discount (e.g. a summer sale); with bank transfer only the larger discount counts unless they combine
    pr = o.get("promo")   # the index's lean offers carry stacks_with_bank only when set: absent = doesn't combine
    bank_beats = s.pay == "bank" and adj is not None and adj < 0 and pr and not pr.get("stacks_with_bank")
    promo_pct = 0 if not pr else (0 if -adj >= pr["pct"] else pr["pct"]) if bank_beats else pr["pct"]
    if promo_pct and bank_beats:
        adj = 0
    promo_amt = lst * promo_pct / 100
    base = lst - promo_amt
    adj_amt = 0 if adj is None else base * adj / 100
    ship_amt = ship[c] if ship else 0
    duties = (o.get("duties") or {}).get(s.region)
    vat = None if rule.rate is None else (base + adj_amt + (ship_amt if rule.ship_taxed else 0)) * rule.rate / 100
    tax_fee = max(vat * rule.fee["pct"] / 100, rule.fee["min_m"][c]) if vat is not None and rule.fee else 0
    tax_est = None if vat is None else vat + tax_fee
    tax_added = tax_est if duties is False and tax_est is not None else 0
    approx_money = o["money"].get(c + "_approx") == 1
    return Cost(
        list=lst, promo_amt=promo_amt, promo_pct=promo_pct, base=base, adj=adj, adj_amt=adj_amt,
        ship=ship_amt if ship else None, ship_min=bool(ship and ship.get("min")),   # the store publishes only a starting price ("from EUR 10")
        tax_est=tax_est, tax_added=tax_added,
        total=base + adj_amt + ship_amt + tax_added,
        approx=approx_money or tax_added > 0 or bool(ship and ship.get("min")),
        complete=adj is not None and bool(ship),
        pay_ok=not o.get("pay_ok") or o["pay_ok"].get(s.pay) is not False,
        old=bool(o.get("old")),   # the store hasn't answered for days: its price ranks after current ones
        duties=duties,
    )


# What a total leaves out: shipping the store doesn't list, import tax that may still be due
def maybe_tax(c: Cost) -> bool:
    return c.duties is not True and not c.tax_added


def left_out(c: Cost) -> str:
    """What the total leaves out, in words: "", "shipping", "import tax" or "shipping and import tax"."""
    return " and ".join(x for x, gone in (("shipping", c.ship is None), ("import tax", maybe_tax(c))) if gone)


# Cheapest offer for the chosen settings. Stores that don't take the chosen payment method rank last, and a total we can
# fully work out leads over a lower one that leaves shipping or import tax open (that one is shown as "or €X + shipping").
# Among totals that leave something open, fewer unknowns lead: unlisted shipping weighs more than import tax that
# may be due, so €8 cheaper with shipping unknown doesn't beat free shipping. A "from €10" shipping floor is a
# known (≈) cost, not an unknown.
def unknowns(c: Cost) -> int:
    return (2 if c.ship is None else 0) + (1 if maybe_tax(c) else 0)


def better(a: Cost, b: Cost) -> bool:
    """True when a ranks ahead of b: payment accepted, then current over old, then fewer unknowns, then lower total."""
    if a.pay_ok != b.pay_ok:
        return a.pay_ok
    if a.old != b.old:
        return not a.old
    if unknowns(a) != unknowns(b):
        return unknowns(a) < unknowns(b)
    return a.total < b.total


def rank(offers: list[dict], s: Settings, rule: TaxRule, with_base: bool = False) -> list[tuple[dict, Cost]]:
    """In-stock offers with a known RAM/storage, best first. A store that doesn't deliver to the region is skipped.
    with_base: also offers whose RAM/storage the store doesn't list, as today's phone page ranks them (its "not
    listed" row) and so its title."""
    out = [(o, cost(o, s, rule)) for o in offers
           if o.get("available") and (with_base or o.get("storage") != "base") and (o.get("ship") or {}).get(s.region) is not False]
    # the same order better() gives, as a sort key (stable, so ties keep the input order)
    return sorted(out, key=lambda oc: (not oc[1].pay_ok, oc[1].old, unknowns(oc[1]), oc[1].total))
