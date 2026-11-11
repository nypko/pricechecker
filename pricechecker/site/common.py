"""Constants and small formatting helpers shared by the site modules: display currencies, edition labels, money in every
site currency, RAM/storage and spec text."""
import hashlib
import re
from pathlib import Path

import yaml

from .. import fx
from ..photos import PHOTOS_DIR

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
    """{"global": "Global", "china": "China", "means": ...} - "Asia" for brands whose model numbers cover China, Hong Kong
    and Taiwan; means: the price box's link to what the China version means."""
    b = _google()["brands"].get(brand.lower(), {})
    return {**EDITION_LABEL, "china": b.get("china_label", EDITION_LABEL["china"]),
            "means": b.get("means", "Chinese software, Google Play off at first")}


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


def spec_line(key: dict | None) -> str:
    """A sheet's `key` block -> "Dimensity 9600M · 6.59″ · up to 8,000 mAh" (chip, screen, battery; blanks and their
    separators dropped). A battery listing several values reads "up to" the largest; one without digits stays as is."""
    rows = dict(_specs(key))
    battery = rows.get("Battery")
    found = re.findall(r"\d[\d,]*(?= mAh)", battery or "")
    if len(found) > 1:
        battery = f"up to {max(found, key=lambda n: int(n.replace(',', '')))} mAh"
    return " · ".join(x for x in (rows.get("Chip"), rows.get("Screen"), battery) if x)


def photo_of(pid: str, sheet: dict | None, brand: str, photos_dir: Path | None = None) -> dict | None:
    """The phone's two processed photo files as site paths with a content hash (?v=), plus who to credit; None unless its
    sheet names a photo (photo.url) and both files exist, so taking `photo:` out of a sheet takes the photo off the site."""
    photo = (sheet or {}).get("photo") or {}
    if not photo.get("url"):
        return None
    d = photos_dir or PHOTOS_DIR
    out = {}
    for k in ("s", "m"):
        f = d / f"{pid}-{k}.webp"
        if not f.is_file():
            return None
        out[k] = f"static/phones/{pid}-{k}.webp?v={hashlib.sha256(f.read_bytes()).hexdigest()[:10]}"
    out["credit"] = photo.get("credit") or brand
    return out


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
