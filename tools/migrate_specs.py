"""One-off: split config/specs.yaml into config/specs/<id>.yaml (key specs, with each phone's note kept as a comment) and
add the three full sheets transcribed from the redesign mock (window.DPS in mock/specs.js, copied from the brands' own
spec pages on 2026-10-26). Run from the repo root:
  python tools/migrate_specs.py [old specs.yaml] [mock/specs.js]   (config/specs.yaml is deleted now: git show HEAD~1:config/specs.yaml)"""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pricechecker import specs  # noqa: E402

OUT = Path("config/specs")
HEADER = [
    "Key specs shown on the phone page. Entered by hand, checked 2026-10-19/20 against GSMArena, brand announcements and",
    "Android Authority. 'brand' = the brand's own spec page; otherwise launch coverage where at least two sources agree.",
    "A field sources disagree on is left out rather than guessed. Battery is the typical (advertised) capacity.",
]
GROUP_OF = {"Display": "display", "Performance": "performance", "Battery and charging": "battery", "Cameras": "cameras",
            "Build": "build", "Connectivity": "connectivity", "Software": "software", "Other": "other"}


def _q(v) -> str:
    return json.dumps(v, ensure_ascii=False) if isinstance(v, str) else ("null" if v is None else str(v))


def _val(v) -> str:
    if isinstance(v, dict) and "v" in v:
        return f"{{value: {_q(v['v'])}, from: {v['from']}}}"
    if isinstance(v, dict):
        return f"{{china: {_q(v['china'])}, global: {_q(v['global'])}}}"
    return _q(v)


def _field_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _full(pid: str, mock: dict) -> list[str]:
    out = ["sources:"]
    for ver, s in mock["sources"].items():
        lang = f", lang: {s['lang']}" if s.get("lang") else ""
        out.append(f"  {ver}: {{url: {s['url']}, checked: {s['checked']}{lang}}}")
    return out


def _tail(mock: dict) -> list[str]:
    out = ["groups:"]
    for gname, rows in mock["groups"]:
        g = GROUP_OF[gname]
        out.append(f"  {g}:")
        for label, v in rows:
            k = _field_key(label)
            assert specs.FIELDS[g].get(k) == label, (g, k, label)
            out.append(f"    {k}: {_val(v)}")
    out.append("bands:")
    for ver, b in mock["bands"].items():
        out += [f"  {ver}:", f"    lte: {json.dumps(b['lte'])}", f"    nr: {json.dumps(b['nr'])}"]
    return out


def main(old: Path, mock_js: Path) -> int:
    src = old.read_text().splitlines()
    entries = yaml.safe_load(old.read_text())["phones"]
    notes: dict[str, list[str]] = {}
    section = ""   # a "  # ..." line above a block of phones applies to each phone below it
    for line in src:
        m = re.match(r"^  ([a-z0-9-]+):\s*\{.*\}\s*(?:#\s*(.*))?$", line)
        if m:
            notes[m[1]] = ([section] if section else []) + ([m[2]] if m[2] else [])
        elif line.startswith("  #"):
            section = line.strip("# ").strip()
    node = ("global.window=global;" + mock_js.read_text() + ";console.log(JSON.stringify(DPS.phones))")
    mocks = json.loads(subprocess.run(["node", "-e", node], capture_output=True, text=True, check=True).stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    for pid, sp in entries.items():
        lines = [f"# {h}" for h in HEADER]
        if sp.get("source") == "brand":
            lines.append("# source: brand (the brand's own spec page)")
        lines += [f"# {n}" for n in dict.fromkeys(notes.get(pid, []))]
        lines.append(f"id: {pid}")
        if pid in mocks:
            lines += _full(pid, mocks[pid])
        lines.append("key:")
        for k in specs.KEY_FIELDS:
            if sp.get(k) is not None:
                lines.append(f"  {k}: {_q(sp[k])}")
        if pid in mocks:
            lines += _tail(mocks[pid])
        (OUT / f"{pid}.yaml").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(entries)} files to {OUT}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(Path(a[0] if a else "config/specs.yaml"), Path(a[1] if len(a) > 1 else "/home/db/Work/doorprice-redesign/mock/specs.js")))
