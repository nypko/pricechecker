"""Constants and small formatting helpers shared by the site modules: display currencies, edition labels, money in every
site currency, RAM/storage and spec text."""
import re
from pathlib import Path

import yaml

from .. import fx

CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]   # CAD: always an ECB conversion (marked ≈)
EDITIONS = ["global", "china"]
EDITION_LABEL = {"global": "Global", "china": "China"}
STORE_COLORS = ["#2a78d6", "#e3742c", "#1fa37a", "#b0479c", "#c9a227", "#6d4c41", "#d64545", "#3fa7b5"]
SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "C$", "AUD": "A$"}
_GOOGLE: dict = {}


def _google() -> dict:
    """config/google.yaml: Google Play on each brand's China version, and what we call that version."""
    if not _GOOGLE:
        _GOOGLE.update(yaml.safe_load(Path("config/google.yaml").read_text()))
    return _GOOGLE


def ed_labels(brand: str) -> dict:
    """{"global": "Global", "china": "China"} - or "Asia" for brands whose model numbers cover China, Hong Kong and Taiwan."""
    b = _google()["brands"].get(brand.lower(), {})
    return {**EDITION_LABEL, "china": b.get("china_label", EDITION_LABEL["china"])}


def _money(offer: dict, rates: dict) -> dict:
    """Per site currency: the store's own price if it sets one, else an ECB conversion (flagged approximate)."""
    own = offer.get("prices") or {offer["currency"]: offer["price"]}
    m = {}
    for c in CURRENCIES:
        if c in own:
            m[c.lower()], m[c.lower() + "_approx"] = own[c], 0
        else:
            m[c.lower()], m[c.lower() + "_approx"] = round(fx.convert(offer["price"], offer["currency"], c, rates), 2), 1
    return m


def _usd_money(usd: float | None, rates: dict) -> dict | None:
    return _money({"price": usd, "currency": "USD"}, rates) if usd else None


def _specs(sp: dict | None) -> list[tuple[str, str]]:
    """a sheet's `key` block -> [("Chip", "Dimensity 9500"), ("Screen", "6.78″"), ...] in a fixed order, skipping blanks."""
    if not sp:
        return []
    screen = sp.get("screen")
    if screen is not None:
        size, _, rest = str(screen).partition(" ")
        screen = f"{size}″" + (f" {rest}" if rest else "")
    rows = [("Chip", sp.get("chip")), ("Screen", screen), ("Battery", sp.get("battery")), ("Charging", sp.get("charging"))]
    return [(k, str(v)) for k, v in rows if v]


def _spec_parts(v: str) -> list[tuple[str, str]]:
    """One spec value -> [(value, tag)] for display on separate lines: "7,200 mAh (China) / 7,100 mAh (Global)" ->
    [("7,200 mAh", "China"), ("7,100 mAh", "Global")]; "7.95″ inside" -> [("7.95″", "inner screen")]; else [(v, "")]."""
    out = []
    for part in v.split(" / "):
        m = re.match(r"^(.*?)\s*\((China|Global|US|EU)\)$", part)
        if m:
            out.append((m[1], m[2]))
        elif part.endswith(" inside"):
            out.append((part[:-7], "inner screen"))
        else:
            out.append((part, ""))
    return out


def spec(storage: str) -> str:
    """'12/256' -> '12 GB RAM · 256 GB storage', '16/1024' -> '16 GB RAM · 1 TB storage'; '' when unknown."""
    if "/" not in storage:
        return ""
    ram, rom = (int(x) for x in storage.split("/"))
    return f"{ram} GB RAM · " + (f"{rom // 1024} TB" if rom >= 1024 and rom % 1024 == 0 else f"{rom} GB") + " storage"


def _storage_key(s: str) -> tuple:
    return tuple(int(x) for x in s.split("/")) if "/" in s else (0, 0)
