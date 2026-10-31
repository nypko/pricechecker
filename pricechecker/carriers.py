"""Mobile networks: config/carriers/<CC>.yaml, one file per country, and the band table (config/bands.yaml).

File: country (ISO code, the file name); networks [{id, name, lte: [int]|null, nr: [int]|null, basis: used|licensed,
complete: bool, mvnos: [str], sources [{url (https), kind: regulator|carrier|brand|other, checked: YYYY-MM-DD}]}].
lte/nr list the bands the network uses (basis used) or the regulator says it holds (basis licensed); complete = a
source gives the full list; null = not researched. Band numbers must be in
the band table, whose `class` (low <1 GHz, mid 1-2.7 GHz, high 3-7 GHz, mmwave >24 GHz) is the only place classes live."""
import calendar
import datetime
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import yaml

CARRIERS_DIR = Path("config/carriers")
BANDS_FILE = Path("config/bands.yaml")

# the 27 EU member states, then GB, US, CA, AU
COUNTRIES: tuple[str, ...] = (
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU",
    "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GB", "US", "CA", "AU")
BASES = ("used", "licensed")
KINDS = ("regulator", "carrier", "brand", "other")
CLASSES = ("low", "mid", "high", "mmwave")


def load(dir: Path = CARRIERS_DIR) -> dict[str, dict]:
    """{country code: file} for every <CC>.yaml in dir (none if the folder does not exist)."""
    return {p.stem: yaml.safe_load(p.read_text()) or {} for p in sorted(Path(dir).glob("*.yaml"))}


@lru_cache(maxsize=1)
def band_table() -> dict:
    """{"lte": {n: {mhz, class, use}}, "nr": {...}}."""
    return yaml.safe_load(BANDS_FILE.read_text())


def band_class(kind: str, n: int) -> str:
    return band_table()[kind][n]["class"]


def _date(x) -> datetime.date | None:
    if isinstance(x, datetime.datetime):
        return x.date()
    if isinstance(x, datetime.date):
        return x
    if isinstance(x, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
        try:
            return datetime.date.fromisoformat(x)
        except ValueError:
            return None
    return None


def _network_problems(n, table: dict) -> list[str]:
    if not isinstance(n, dict):
        return ["a network must be a mapping"]
    nid = n.get("id")
    who = nid if isinstance(nid, str) and nid else "network (no id)"
    out: list[str] = []
    if not isinstance(nid, str) or not nid:
        out.append(f"{who}: id missing")
    if not isinstance(n.get("name"), str) or not n["name"].strip():
        out.append(f"{who}: name missing")
    for kind in ("lte", "nr"):
        xs = n.get(kind)
        if xs is None:
            continue
        if not isinstance(xs, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in xs):
            out.append(f"{who}: {kind} must be a list of band numbers or null")
            continue
        out += [f"{who}: {kind} band {x} is not in config/bands.yaml" for x in xs if x not in table[kind]]
    if n.get("basis") not in BASES:
        out.append(f"{who}: basis must be one of {'|'.join(BASES)} ({n.get('basis')})")
    if not isinstance(n.get("complete"), bool):
        out.append(f"{who}: complete must be true or false ({n.get('complete')})")
    if n.get("complete") is True and (n.get("lte") is None or n.get("nr") is None):
        out.append(f"{who}: complete cannot be true while lte or nr is null")
    mv = n.get("mvnos", [])
    if not isinstance(mv, list) or not all(isinstance(x, str) and x for x in mv):
        out.append(f"{who}: mvnos must be a list of names")
    srcs = n.get("sources")
    if not isinstance(srcs, list) or not srcs:
        out.append(f"{who}: needs at least one source")
        return out
    for s in srcs:
        s = s if isinstance(s, dict) else {}
        url = urlparse(str(s.get("url", "")))
        if url.scheme != "https" or not url.hostname:
            out.append(f"{who}: source url must be https ({s.get('url')})")
        if s.get("kind") not in KINDS:
            out.append(f"{who}: source kind must be one of {'|'.join(KINDS)} ({s.get('kind')})")
        if _date(s.get("checked")) is None:
            out.append(f"{who}: source checked must be YYYY-MM-DD ({s.get('checked')})")
    if n.get("basis") == "licensed" and not any(isinstance(s, dict) and s.get("kind") == "regulator" for s in srcs):
        out.append(f"{who}: basis licensed needs a regulator source")
    if all(isinstance(s, dict) and s.get("kind") == "other" for s in srcs):
        out.append(f"{who}: needs a regulator, carrier or brand source, not only 'other'")
    return out


def validate(doc: dict, table: dict) -> list[str]:
    """Problems with one country file (empty list = valid); ids are checked unique within the file."""
    out: list[str] = []
    cc = doc.get("country")
    if cc not in COUNTRIES:
        out.append(f"country {cc} is not one of the {len(COUNTRIES)} countries")
    nets = doc.get("networks")
    if not isinstance(nets, list) or not nets:
        return out + [f"{cc}: networks missing"]
    seen: set = set()
    for n in nets:
        out += _network_problems(n, table)
        nid = n.get("id") if isinstance(n, dict) else None
        if nid and nid in seen:
            out.append(f"{nid}: id used twice")
        seen.add(nid)
    return out


def validate_all(docs: dict[str, dict], table: dict) -> list[str]:
    """validate() every file, then: the file name equals `country`, and network ids are unique across files."""
    out: list[str] = []
    owner: dict[str, str] = {}
    for cc, doc in docs.items():
        out += [f"{cc}.yaml: {e}" for e in validate(doc, table)]
        if doc.get("country") != cc:
            out.append(f"{cc}.yaml: country is {doc.get('country')}, the file name says {cc}")
        for n in doc.get("networks") or []:
            nid = n.get("id") if isinstance(n, dict) else None
            if nid and nid in owner and owner[nid] != cc:
                out.append(f"{nid}: id is in both {owner[nid]}.yaml and {cc}.yaml")
            owner.setdefault(nid, cc)
    return out


def stale(doc: dict, today: datetime.date, months: int = 12) -> list[str]:
    """Ids of networks whose newest source was checked more than `months` months before today."""
    y, m = divmod(today.year * 12 + today.month - 1 - months, 12)
    cutoff = datetime.date(y, m + 1, min(today.day, calendar.monthrange(y, m + 1)[1]))
    out = []
    for n in doc.get("networks") or []:
        ds = [d for s in n.get("sources") or [] if (d := _date(s.get("checked")))]
        if not ds or max(ds) < cutoff:
            out.append(n["id"])
    return out
