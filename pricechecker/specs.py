"""Spec sheets: config/specs/<id>.yaml, one file per phone, and the EU band check (config/region_bands.yaml).

File: id; sources {china|global: {url, checked, lang?}}; key {chip, screen, battery, charging} (what every page shows);
groups {<group>: {<field>: value}}; bands {china|global: {lte: [int], nr: [int]}}.
A value is a string, null (not on the brand's page), {china: str|null, global: str|null} (the two pages disagree)
or {value: str, from: china|global} (only that page lists the same hardware fact).
A version with no `sources` entry or no `bands` entry has not been read yet."""
import datetime
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml

SPECS_DIR = Path("config/specs")
BANDS_FILE = Path("config/region_bands.yaml")
CATALOG_FILE = Path("config/catalog.yaml")

VERSIONS = ("china", "global")
KEY_FIELDS = ("chip", "screen", "battery", "charging")

# group -> {field key: label shown on the page}; adding a field means adding it here
FIELDS: dict[str, dict[str, str]] = {
    "display": {"size": "Size", "panel": "Panel", "resolution": "Resolution", "refresh_rate": "Refresh rate",
                "brightness": "Brightness", "colour": "Colour", "dimming": "Dimming"},
    "performance": {"chip": "Chip", "cpu": "CPU", "top_cpu_speed": "Top CPU speed", "gpu": "GPU", "ram": "RAM",
                    "storage": "Storage", "versions": "Versions"},
    "battery": {"battery": "Battery", "wired": "Wired", "wireless": "Wireless"},
    "cameras": {"main": "Main", "telephoto": "Telephoto", "periscope": "Periscope", "ultra_wide": "Ultra-wide",
                "colour_lens": "Colour lens", "front": "Front", "video": "Video"},
    "video": {},
    "build": {"size": "Size", "weight": "Weight", "colours": "Colours", "water_and_dust": "Water and dust", "frame": "Frame"},
    "connectivity": {"wi_fi": "Wi-Fi", "bluetooth": "Bluetooth", "le_audio": "LE Audio", "nfc": "NFC", "sim": "SIM",
                     "usb": "USB", "satellite_positioning": "Satellite positioning", "also": "Also",
                     "china_model_number": "China model number"},
    "software": {"system": "System", "updates": "Updates"},
    "other": {"speakers": "Speakers", "fingerprint": "Fingerprint", "face_unlock": "Face unlock",
              "infrared_remote": "Infrared remote", "sensors": "Sensors", "in_the_box": "In the box"},
}
GROUPS: tuple[str, ...] = tuple(FIELDS)

# brand (lowercase, as in the catalog) -> the brand's own domains; a source URL must be on one of them
BRAND_HOSTS: dict[str, tuple[str, ...]] = {
    "google": ("google.com",),
    "honor": ("honor.com",),
    "huawei": ("huawei.com",),
    "motorola": ("motorola.com",),
    "oneplus": ("oneplus.com",),
    "oppo": ("oppo.com",),
    "realme": ("realme.com",),
    "redmi": ("mi.com", "xiaomi.com"),
    "samsung": ("samsung.com",),
    "sony": ("sony.com",),
    "vivo": ("vivo.com",),
    "xiaomi": ("xiaomi.com", "mi.com"),
    "iqoo": ("iqoo.com",),
}


def load(dir: Path = SPECS_DIR) -> dict[str, dict]:
    """{phone id: sheet} for every <id>.yaml in dir."""
    return {p.stem: yaml.safe_load(p.read_text()) or {} for p in sorted(Path(dir).glob("*.yaml"))}


@lru_cache(maxsize=1)
def _catalog_brands() -> dict[str, str]:
    cat = yaml.safe_load(CATALOG_FILE.read_text())["phones"]
    return {p["id"]: (p.get("brand") or p["name"].split()[0]).lower() for p in cat}


def _is_date(x) -> bool:
    return isinstance(x, datetime.date) or (isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x) is not None)


def _value_problems(where: str, v) -> list[str]:
    if v is None or isinstance(v, str):
        return []
    if isinstance(v, dict) and set(v) == {"china", "global"}:
        return [f"{where}: {k} must be text or null" for k in v if not (v[k] is None or isinstance(v[k], str))]
    if isinstance(v, dict) and set(v) == {"value", "from"}:
        if not isinstance(v["value"], str) or v["from"] not in VERSIONS:
            return [f"{where}: expected {{value: text, from: china|global}}"]
        return []
    return [f"{where}: a value is text, null, {{china, global}} or {{value, from}}"]


def validate(sheet: dict, brand: str | None = None) -> list[str]:
    """Problems with one sheet (empty list = valid). The brand defaults to the catalog's brand for the sheet's id."""
    out: list[str] = []
    pid = sheet.get("id")
    if not pid:
        return ["id missing"]
    brand = (brand or _catalog_brands().get(pid) or "").lower()
    if brand not in BRAND_HOSTS:
        out.append(f"{pid}: not in the catalog (no brand)")
    for k in sheet:
        if k not in ("id", "sources", "key", "groups", "bands"):
            out.append(f"unknown top-level key {k}")
    for ver, s in (sheet.get("sources") or {}).items():
        if ver not in VERSIONS:
            out.append(f"sources.{ver}: not china/global")
            continue
        host = (urlparse(str((s or {}).get("url", ""))).hostname or "").lower()
        if not any(host == h or host.endswith("." + h) for h in BRAND_HOSTS.get(brand, ())):
            out.append(f"sources.{ver}: {host or 'no url'} is not one of {brand}'s own sites")
        if not _is_date((s or {}).get("checked")):
            out.append(f"sources.{ver}.checked must be YYYY-MM-DD")
    key = sheet.get("key")
    if not isinstance(key, dict):
        out.append("key missing")
    else:
        for k, v in key.items():
            if k not in KEY_FIELDS:
                out.append(f"key.{k}: unknown")
            elif not isinstance(v, (str, int, float)) or isinstance(v, bool):
                out.append(f"key.{k}: text or number")
    for g, fields in (sheet.get("groups") or {}).items():
        if g not in FIELDS:
            out.append(f"groups.{g}: unknown group")
            continue
        for f, v in (fields or {}).items():
            if f not in FIELDS[g]:
                out.append(f"groups.{g}.{f}: unknown field")
            else:
                out += _value_problems(f"groups.{g}.{f}", v)
    for ver, b in (sheet.get("bands") or {}).items():
        if ver not in VERSIONS:
            out.append(f"bands.{ver}: not china/global")
            continue
        for kind in ("lte", "nr"):
            xs = (b or {}).get(kind)
            if not isinstance(xs, list) or not all(isinstance(x, int) for x in xs):
                out.append(f"bands.{ver}.{kind}: list of band numbers")
    return out


@lru_cache(maxsize=1)
def _regions() -> dict:
    return yaml.safe_load(BANDS_FILE.read_text())


def band_check(sheet: dict, edition: str, region: str = "EU") -> dict | None:
    """Main bands of the region that this version lacks: {"lte": [...], "nr": [...], "why": {band: text}}.
    None when we have not read that version's bands."""
    have = (sheet.get("bands") or {}).get(edition)
    if not have:
        return None
    r = _regions()[region]
    lte = [b for b in r["lte"] if b not in have.get("lte", [])]
    nr = [b for b in r["nr"] if b not in have.get("nr", [])]
    why = {b: r["why"][b] for b in dict.fromkeys(lte + nr) if b in r.get("why", {})}
    return {"lte": lte, "nr": nr, "why": why}


def differences(sheet: dict) -> int:
    """Fields where both versions' pages give a value and the values differ (a one-sided value is not counted)."""
    n = 0
    for fields in (sheet.get("groups") or {}).values():
        for v in (fields or {}).values():
            if isinstance(v, dict) and set(v) == {"china", "global"} and v["china"] is not None \
                    and v["global"] is not None and v["china"] != v["global"]:
                n += 1
    return n
