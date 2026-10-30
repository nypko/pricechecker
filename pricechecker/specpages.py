"""Brand spec pages kept as text (data/spec_pages/<id>-<edition>.txt) and watched weekly for changes.

  python -m pricechecker.specpages fetch <id> [--edition china|global]   local only: saves the page text (JavaScript pages: rendered with chromium)
  python -m pricechecker.specpages watch                                 plain GET of each saved page; changes go to .spec_report.md

The watch never works around bot protection or JavaScript: a page that answers with (almost) no text is listed
as "check by hand". Nothing is applied automatically; a person re-reads the page and updates config/specs."""
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

from . import http, specs
from .issue_text import fence

SNAP_DIR = Path("data/spec_pages")
REPORT = Path(".spec_report.md")   # filed as a GitHub issue by the workflow; not committed
MIN_TEXT = 500                      # less text than this = the page is built by JavaScript
MAX_DIFF = 40


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            line = re.sub(r"\s+", " ", data).strip()
            if line:
                self.lines.append(line)


def page_text(html: str) -> str:
    """Visible text, one trimmed line per text node, scripts and styles removed, empty lines dropped."""
    p = _Text()
    p.feed(html)
    p.close()
    return "\n".join(p.lines)


def _lines(text: str) -> list[str]:
    """Lines that matter for comparison: counters and other digit-only lines are ignored."""
    return [ln for ln in text.splitlines() if re.search(r"[^\d\s]", ln)]


def _get(url: str) -> str:
    r = http.capped_get(url)   # the scraper's session (same User-Agent), body capped at http.MAX_BYTES
    r.raise_for_status()
    return r.text


def watch(snap_dir: Path = SNAP_DIR, report: Path = REPORT, sheets: dict | None = None, fetch=_get) -> int:
    """Compare each saved snapshot with the live page; write changes to `report`. Returns the number reported."""
    import difflib
    sheets = specs.load() if sheets is None else sheets
    changed, by_hand = [], []
    for f in sorted(snap_dir.glob("*.txt")):
        pid, _, edition = f.stem.rpartition("-")
        url = ((sheets.get(pid) or {}).get("sources") or {}).get(edition, {}).get("url")
        if not url:
            by_hand.append(f"- `{pid}` ({edition}): no source URL in config/specs any more")
            continue
        try:
            new = page_text(fetch(url))
        except Exception as e:   # blocked, down, timeout: never a failed run
            by_hand.append(f"- `{pid}` ({edition}): {url} could not be fetched ({type(e).__name__}); check by hand")
            continue
        if len(new) < MIN_TEXT:
            by_hand.append(f"- `{pid}` ({edition}): {url} needs JavaScript or blocks plain requests; check by hand")
            continue
        old_l, new_l = _lines(f.read_text()), _lines(new)
        if old_l == new_l:
            continue
        diff = [ln for ln in difflib.unified_diff(old_l, new_l, lineterm="", n=0) if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
        shown = diff[:MAX_DIFF] + ([f"... {len(diff) - MAX_DIFF} more changed lines"] if len(diff) > MAX_DIFF else [])
        changed.append(f"### `{pid}` ({edition})\n{url}\n\n" + "\n".join(fence(shown, "diff")))
    if not changed:   # pages to check by hand alone never raise a report (no weekly issue); they ride along with a real change
        for ln in by_hand:
            print(ln)
        return 0
    out = []
    if changed:
        out.append("Spec pages whose text changed since the saved copy. Re-read the page and update config/specs, "
                   "Snapshots are not updated automatically: after checking the change, re-fetch locally with "
                   "`python -m pricechecker.specpages fetch <id> --edition <edition>` and commit the snapshot, "
                   "or this is reported again next Monday.\n\n"
                   + "\n\n".join(changed))
    if by_hand:
        out.append("Pages to check by hand:\n\n" + "\n".join(by_hand))
    with report.open("a") as fh:
        fh.write("\n\n".join(out) + "\n")
    return len(changed)


def fetch(pid: str, edition: str | None = None, snap_dir: Path = SNAP_DIR) -> list[Path]:
    """Render the brand page(s) of one phone with local chromium and save the text."""
    chromium = shutil.which("chromium") or shutil.which("chromium-browser")
    if not chromium:
        sys.exit("chromium not found: `fetch` renders JavaScript pages and runs only on a machine with chromium installed")
    sheet = specs.load().get(pid)
    if not sheet:
        sys.exit(f"unknown phone id: {pid}")
    src = sheet.get("sources") or {}
    editions = [edition] if edition else list(src)
    snap_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for ed in editions:
        if ed not in src:
            sys.exit(f"{pid} has no {ed} source in config/specs")
        # the weekly watch compares with a plain GET, so a page that answers one is saved as that answer; only a page
        # built by JavaScript is rendered (the watch then lists it as "check by hand")
        try:
            text = page_text(_get(src[ed]["url"]))
        except Exception:
            text = ""
        if len(text) < MIN_TEXT:
            try:
                r = subprocess.run([chromium, "--headless=new", "--disable-gpu", "--virtual-time-budget=15000", "--dump-dom", src[ed]["url"]],
                                   capture_output=True, text=True, timeout=180)
                text = page_text(r.stdout)
            except subprocess.TimeoutExpired:
                text = ""
        if len(text) < MIN_TEXT:
            sys.exit(f"{pid} {ed}: only {len(text)} characters of text came back; not saved")
        path = snap_dir / f"{pid}-{ed}.txt"
        path.write_text(text + "\n")
        print(f"{path}: {len(text)} characters")
        out.append(path)
    return out


def main(argv: list[str]) -> int:
    if argv[:1] == ["fetch"] and len(argv) >= 2:
        ed = argv[argv.index("--edition") + 1] if "--edition" in argv else None
        fetch(argv[1], ed)
        return 0
    if argv[:1] == ["watch"]:
        n = watch()
        print(f"{n} spec page(s) changed")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
