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
_STORAGE = re.compile(r"(\d{1,2})\s*(?:gb\s*(?:ram)?\s*[+/,\s-]|\+|/)\s*-?\s*(\d{2,4}\s*(?:gb|tb)|[12]\s*tb)", re.I)


# Brands with no China edition: their phones are "global" even when a listing doesn't say so
# (Pixels are sold as US/JP/EU models, never as a China version).
_NO_CHINA_EDITION = re.compile(r"\b(?:google|pixel)\b", re.I)


def edition_of(title: str) -> str:
    return "global" if re.search(r"global", title, re.I) or _NO_CHINA_EDITION.search(title) else "china"


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
    if words[:2] in (["vivo", "iqoo"], ["xiaomi", "redmi"]):   # sub-brands: "vivo iQOO 15" = "iQOO 15", "Xiaomi Redmi K90" = "Redmi K90"
        del words[0]
    if words[:1] == ["realme"]:                    # "Realme GT8 Pro" (Trading Shenzhen) = "Realme GT 8 Pro" (Giztop)
        words = [w2 for w in words for w2 in (re.match(r"(gt)(\d+)$", w).groups() if re.match(r"gt\d+$", w) else (w,))]
    if len(words) > 1 and words[0] == "samsung" and words[1] != "galaxy":
        words.insert(1, "galaxy")
    return "-".join(words)


def storage_of(text: str) -> str:
    """'12GB+256GB' -> '12/256', '16GB 1TB' -> '16/1024'; 'base' if not found."""
    m = _STORAGE.search(text or "")
    if not m:
        return "base"
    ram, rom = m.group(1), m.group(2).lower().replace(" ", "")
    rom_gb = int(rom[:-2]) * 1024 if rom.endswith("tb") else int(rom[:-2])
    return f"{int(ram)}/{rom_gb}"
