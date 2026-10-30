"""static/js/compare.js against tests/js/compare_cases.mjs (pure helpers: closest memory, winners, hash, differences)."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_compare_cases():
    r = subprocess.run(["node", str(ROOT / "tests/js/compare_cases.mjs")], check=False, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
