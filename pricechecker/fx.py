"""Daily reference exchange rates from the European Central Bank (free, no key)."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from . import http

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
CACHE = Path("data/fx.json")


def rates() -> dict:
    """Units of each currency per 1 EUR, e.g. {'EUR': 1.0, 'USD': 1.16, 'GBP': 0.87, ...}."""
    try:
        root = ET.fromstring(http.get(ECB_URL, respect_robots=False).content)
        r = {"EUR": 1.0}
        date = None
        for el in root.iter():
            if el.get("time"):
                date = el.get("time")
            if el.get("currency"):
                r[el.get("currency")] = float(el.get("rate"))
        CACHE.write_text(json.dumps({"date": date, "rates": r}, indent=1))
        return {"date": date, "rates": r}
    except Exception as e:
        if CACHE.exists():
            print(f"  [fx] ECB unavailable ({e}); using cached rates")
            return json.loads(CACHE.read_text())
        raise


def cached() -> dict:
    """The last saved ECB rates, without asking the ECB (offline builds)."""
    return json.loads(CACHE.read_text())


def convert(amount: float, frm: str, to: str, r: dict) -> float:
    return amount / r[frm] * r[to]
