"""The GitHub workflows: actions pinned to commits, least-privilege tokens, and which tests gate which deploy."""
import re
from pathlib import Path

import yaml

FLOWS = {f.name: f.read_text() for f in Path(".github/workflows").glob("*.yml")}


def test_every_action_is_pinned_to_a_commit_with_its_version():
    for name, text in FLOWS.items():
        for line in re.findall(r"uses: *(\S+.*)", text):
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+", line.strip()), (name, line)
        assert text.count("cloudflare/wrangler-action@") == len(re.findall(r'wranglerVersion: "\d+\.\d+\.\d+"', text)), name


def test_every_workflow_declares_its_token_permissions():
    for name, text in FLOWS.items():
        perms = yaml.safe_load(text).get("permissions")
        assert isinstance(perms, dict) and perms, name
        writes = {k for k, v in perms.items() if v == "write"}
        pushes = "git push" in text
        assert ("contents" in writes) == pushes, name
        assert ("issues" in writes) == ("gh issue" in text), name
        if not pushes:   # the token isn't left in .git/config
            assert text.count("persist-credentials: false") == text.count("actions/checkout@"), name


def test_review_issues_are_only_the_bots_own():
    for name, text in FLOWS.items():
        for line in re.findall(r"gh issue list[^\n]*", text):
            assert re.search(r"--search 'in:title \"[^\"]+\" author:app/github-actions'", line) and "--author" not in line, (name, line)


def test_hourly_production_skips_live_data_tests_and_previews_run_them_all():
    assert re.search(r'run: python -m pytest -q -m "not live"', FLOWS["hourly.yml"])
    for name in ("newsite.yml", "testing.yml"):
        assert re.search(r"run: python -m pytest -q\n", FLOWS[name]) and "not live" not in FLOWS[name], name
        assert 'DOORPRICE_CHECK_BUDGETS: "1"' in FLOWS[name], name


def test_requirements_are_exact():
    for line in Path("requirements.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            assert re.fullmatch(r"[A-Za-z0-9_.-]+==[\w.]+", line.strip()), line
