"""static/js/settings.js against tests/js/settings_cases.mjs (pure functions: storage, time zone and language are passed in)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_settings_cases():
    r = subprocess.run(["node", str(ROOT / "tests/js/settings_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
