"""Turn store product titles into comparable keys: model id, edition and storage."""
import re

BRAND_ALIASES = {"hw": "huawei", "moto": "motorola"}
_NOISE = [
    r"\b5g\b", r"\b4g\b", r"\bdual[\s-]*sim\b", r"\bsmart\s*phone\b", r"\bsmartphone\b",
    r"\b(sm|xq)-[a-z0-9]+\b",                     # Samsung / Sony model numbers
    r"\bglobal\s*(version|rom|edition)\b", r"\b(china|chinese)\s*(version|rom|edition)\b", r"\bcn\s*version\b",
    r"\bglobal\b",                               # Giztop: "Vivo X300 Ultra Global"
]
# "12GB+256GB", "16GB 1TB", "12+512GB" (Wonda), "16GB RAM / 512GB", "12GB - 256GB" (Giztop)
_STORAGE = re.compile(r"(\d{1,2})\s*(?:gb\s*(?:ram)?\s*[+/,\s-]|\+|/)\s*-?\s*(\d{2,4}\s*(?:gb|tb)|[12]\s*tb)", re.IGNORECASE)


# Brands with no China edition: their phones are "global" even when a listing doesn't say so
# (Pixels are sold as US/JP/EU models, never as a China version).
_NO_CHINA_EDITION = re.compile(r"\b(?:google|pixel)\b", re.IGNORECASE)


# Not the Global version, even though the title says "global": China hardware with global software flashed on it
# ("Oneplus 15 (Global Rom)"; the site shows it as "China (Global ROM)"), or a variant marked China inside a Global listing
# ("Huawei Pura 80 Ultra (GLOBAL) - 16GB/1TB (China Version)").
_CHINA_UNIT = re.compile(r"global\s*rom|\b(?:china|chinese|cn)\s*(?:version|edition|rom)\b", re.IGNORECASE)
GLOBAL_ROM = re.compile(r"global\s*rom", re.IGNORECASE)


def edition_of(title: str) -> str:
    if _CHINA_UNIT.search(title):
        return "china"
    return "global" if re.search(r"global", title, re.IGNORECASE) or _NO_CHINA_EDITION.search(title) else "china"


def model_id(title: str) -> str:
    t = _STORAGE.sub(" ", title.lower())         # before '+' -> 'plus', or "16GB+512GB" leaks into the id
    t = t.replace("+", " plus ")
    for pat in _NOISE:
        t = re.sub(pat, " ", t)
    t = re.sub(r"[()\[\]]", " ", t)               # keep words like "leica edition", drop brackets
    words = re.sub(r"[^a-z0-9 ]+", " ", t).split()
    if words and words[0] in BRAND_ALIASES:
        words[0] = BRAND_ALIASES[words[0]]
    if words[:2] == ["motorola", "moto"]:          # "Motorola Moto Razr 70 Ultra"
        del words[1]
    if words[:1] == ["iphone"]:                    # "iPhone Duo" (Mobile Marvel) = "Apple iPhone Duo"
        words.insert(0, "apple")
    if words[:2] in (["vivo", "iqoo"], ["xiaomi", "redmi"]):   # sub-brands: "vivo iQOO 15" = "iQOO 15", "Xiaomi Redmi K90" = "Redmi K90"
        del words[0]
    if words[:1] == ["realme"]:                    # "Realme GT8 Pro" (Trading Shenzhen) = "Realme GT 8 Pro" (Giztop)
        words = [w2 for w in words for w2 in (re.match(r"(gt)(\d+)$", w).groups() if re.match(r"gt\d+$", w) else (w,))]
    if len(words) > 1 and words[0] == "samsung" and words[1] != "galaxy":
        words.insert(1, "galaxy")
    return "-".join(words)


_ROM_ONLY = re.compile(r"\b(\d{2,4}\s*gb|[12]\s*tb)\b", re.IGNORECASE)


def storage_of(text: str, ram: int | None = None) -> str:
    """'12GB+256GB' -> '12/256', '16GB 1TB' -> '16/1024'; 'base' if not found.
    ram: the model's one RAM size (catalog `ram`), for a listing that gives storage only: '256GB' -> '12/256'."""
    m = _STORAGE.search(text or "") or (_ROM_ONLY.search(text or "") if ram else None)
    if not m:
        return "base"
    ram, rom = (m.group(1), m.group(2)) if m.re is _STORAGE else (ram, m.group(1))
    rom = rom.lower().replace(" ", "")
    rom_gb = int(rom[:-2]) * 1024 if rom.endswith("tb") else int(rom[:-2])
    return f"{int(ram)}/{rom_gb}"
