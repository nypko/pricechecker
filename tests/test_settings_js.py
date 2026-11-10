"""static/js/settings.js against tests/js/settings_cases.mjs (pure functions: storage, time zone and language are passed in)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _js(module, fn, arg_lists, now_ms=False):
    """Call `fn` from static/js/<module> once per argument list in node; with now_ms the second argument (an ISO time) becomes epoch ms."""
    script = (
        f"import {{ {fn} as f }} from {json.dumps((ROOT / 'static/js' / module).as_uri())};"
        f"const now = {json.dumps(now_ms)};"
        f"console.log(JSON.stringify({json.dumps(arg_lists)}.map(a => f(a[0], now ? Date.parse(a[1]) : a[1]))));"
    )
    r = subprocess.run(["node", "--input-type=module", "-e", script], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


@needs_node
def test_settings_cases():
    r = subprocess.run(["node", str(ROOT / "tests/js/settings_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


@needs_node
def test_ago_text_boundaries():
    now = "2026-11-10T20:00:00Z"
    cases = [("2026-11-10T19:58:30Z", "just now"), ("2026-11-10T19:58:00Z", "2 min ago"), ("2026-11-10T19:00:01Z", "59 min ago"),
             ("2026-11-10T19:00:00Z", "1 h ago"), ("2026-11-09T20:00:01Z", "23 h ago"), ("2026-11-09T20:00:00Z", "on 9 Nov"),
             ("2026-11-10T20:05:00Z", "just now"),   # visitor's clock behind the build
             ("not a date", None)]
    assert _js("ago.js", "agoText", [[iso, now] for iso, _ in cases], now_ms=True) == [w for _, w in cases]


@needs_node
def test_place_and_lower_for_line():
    names = {"countries": {"BG": "Bulgaria"}, "provinces": {"QC": "Quebec"}}
    cases = [({"region": "EU", "area": "BG", "pay": "card"}, "Bulgaria"), ({"region": "EU", "area": "", "pay": "card"}, "the EU"),
             ({"region": "Global", "area": "", "pay": "paypal"}, "your country"), ({"region": "CA", "area": "QC", "pay": "card"}, "Quebec"),
             ({"region": "CA", "area": "", "pay": "card"}, "Canada"), ({"region": "UK", "area": "", "pay": "bank"}, "the UK")]
    assert _js("settings.js", "placeOf", [[s, names] for s, _ in cases]) == [p for _, p in cases]
