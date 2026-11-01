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

COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia", "CY": "Cyprus", "CZ": "Czechia",
    "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France", "DE": "Germany", "GR": "Greece",
    "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg",
    "MT": "Malta", "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
    "SI": "Slovenia", "ES": "Spain", "SE": "Sweden", "GB": "United Kingdom", "US": "United States",
    "CA": "Canada", "AU": "Australia"}


def load(dir: Path = CARRIERS_DIR) -> dict[str, dict]:
    """{country code: file} for every <CC>.yaml in dir (none if the folder does not exist)."""
    return {p.stem: yaml.safe_load(p.read_text()) or {} for p in sorted(Path(dir).glob("*.yaml"))}


@lru_cache(maxsize=1)
def band_table() -> dict:
    """{"lte": {n: {mhz, class, use}}, "nr": {...}, "covers": {"lte": {n: [bands n contains]}, "nr": {...}}}."""
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


# ---- verdict: one phone version on one network (mirrored by static/js/carriers.js) ----

def _held(kind: str, have: list, table: dict) -> set:
    """The phone's bands plus every band they contain, following `covers` chains."""
    covers = (table.get("covers") or {}).get(kind) or {}
    held, todo = set(have), list(have)
    while todo:
        for s in covers.get(todo.pop()) or []:
            if s not in held:
                held.add(s)
                todo.append(s)
    return held


def _missing(kind: str, have: list, want: list, table: dict) -> list[dict]:
    """The network bands (`want`) the phone lacks; a phone band that contains the network band (table covers) counts."""
    held = _held(kind, have, table)
    return [{"kind": kind, "n": n, "mhz": table[kind][n]["mhz"], "use": table[kind][n]["use"]}
            for n in want if n not in held]


def _label(m: dict) -> str:
    return f"no band {m['n']}" if m["kind"] == "lte" else f"no 5G band n{m['n']}"


def _unknown(why: str) -> dict:
    return {"kind": "unknown", "missing": [], "text": f"Bands not published for this {why}"}


def _judge(phone: dict | None, network: dict, table: dict) -> tuple[dict, str]:
    """(verdict, the first reason in short words, e.g. "no band 20"); see verdict()."""
    if phone is None or (phone.get("lte") is None and phone.get("nr") is None):
        return _unknown("version"), ""
    used = network.get("basis") != "licensed"   # mmWave counts only where the network is known to use it
    keep = lambda kind, xs: None if xs is None else [n for n in xs if used or table[kind][n]["class"] != "mmwave"]
    wlte, wnr = keep("lte", network.get("lte")), keep("nr", network.get("nr"))
    plte, pnr = phone.get("lte"), phone.get("nr")
    lte_known, nr_known = wlte is not None and plte is not None, wnr is not None and pnr is not None
    if not ((lte_known and wlte) or (nr_known and wnr)):   # nothing left to compare
        phone_side = (wlte is not None and plte is None) or (wnr is not None and pnr is None)
        return _unknown("version" if phone_side else "network"), ""
    m_lte = _missing("lte", plte, wlte, table) if lte_known else []
    m_nr = _missing("nr", pnr, wnr, table) if nr_known else []
    missing = m_lte + m_nr
    low = [m for m in missing if table[m["kind"]][m["n"]]["class"] == "low"]
    who = f"which {network['name']} {'holds' if network.get('basis') == 'licensed' else 'uses'}"
    say = lambda m: f"{_label(m)}, {who} ({m['use']})"
    complete = bool(network.get("complete")) and lte_known and nr_known
    if low:
        return {"kind": "risk", "missing": missing, "text": "Coverage risk: " + "; ".join(say(m) for m in low)}, _label(low[0])
    if nr_known and wnr and lte_known and not m_lte and len(m_nr) == len(wnr):
        return {"kind": "4g", "missing": missing, "text": "4G works; no 5G on this network"}, "no 5G"
    if missing:
        no5g = bool(m_nr) and len(m_nr) == len(wnr)   # all the network's 5G bands: one clause
        clauses = [(_label(m), say(m)) for m in m_lte] + (
            [("no 5G on this network",) * 2] if no5g else [(_label(m), say(m)) for m in m_nr])
        return {"kind": "minor", "missing": missing, "text": "Works; " + "; ".join(c[1] for c in clauses)}, clauses[0][0]
    if not complete:
        return {"kind": "nogaps", "missing": [], "text": "No gaps on the bands we could confirm"}, ""
    return {"kind": "full", "missing": [], "text": "Works fully on 4G and 5G" if wnr else "Works fully on 4G"}, ""


def verdict(phone: dict | None, network: dict, table: dict) -> dict:
    """{kind: unknown|risk|4g|minor|nogaps|full, missing: [{kind, n, mhz, use}], text}; first matching row wins.
    A null lte or nr on the network or on the phone is left out of the judgement and the result can then never be "full";
    if no band is left to compare the verdict is unknown. mmWave bands of a licensed network are ignored."""
    return _judge(phone, network, table)[0]


KINDS_ORDER = ("unknown", "risk", "4g", "minor", "nogaps", "full")
GROUPS = ("risk", "4g", "minor", "nogaps", "full", "unknown")   # the order the summary names them in


def _names(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def summary(phone: dict | None, country_doc: dict, table: dict, country_name: str) -> dict:
    """{counts: {kind: n}, text}, networks grouped by verdict:
    "In Germany: works fully on 2 of 3 networks; coverage risk on O2 (no band 20)"."""
    nets = country_doc.get("networks") or []
    counts = {k: 0 for k in KINDS_ORDER}
    groups: dict[str, list[str]] = {k: [] for k in KINDS_ORDER}
    for n in nets:
        v, first = _judge(phone, n, table)
        counts[v["kind"]] += 1
        groups[v["kind"]].append(f"{n['name']} ({first})" if v["kind"] in ("risk", "minor") else n["name"])
    if phone is None or (phone.get("lte") is None and phone.get("nr") is None):
        return {"counts": counts, "text": f"In {country_name}: bands not published for this version"}
    total, full = len(nets), counts["full"]
    parts = {
        "full": "" if not full else "works fully on its only network" if total == 1 else
        f"works fully on all {total} networks" if full == total else f"works fully on {full} of {total} networks",
        "nogaps": f"no gaps found on {_names(groups['nogaps'])}" if groups["nogaps"] else "",
        "minor": f"minor gaps on {_names(groups['minor'])}" if groups["minor"] else "",
        "4g": f"4G only on {_names(groups['4g'])} (no 5G)" if groups["4g"] else "",
        "risk": f"coverage risk on {_names(groups['risk'])}" if groups["risk"] else "",
        "unknown": f"bands unknown on {_names(groups['unknown'])}" if groups["unknown"] else "",
    }
    return {"counts": counts, "text": f"In {country_name}: " + "; ".join(parts[k] for k in GROUPS if parts[k])}
