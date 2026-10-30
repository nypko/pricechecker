"""Scraped text in GitHub issue bodies stays inside its code fence and mentions nobody (pricechecker/issue_text.py)."""
from pricechecker import issue_text, promos, specpages

ZW = issue_text.ZWSP


def test_fence_is_longer_than_any_backtick_run_inside():
    assert issue_text.fence(["plain"]) == ["```", "plain", "```"]
    out = issue_text.fence(["a", "```", "![x](https://evil.example/i.png)", "`````"], "diff")
    assert out[0] == "``````diff" and out[-1] == "``````"
    inner = out[1:-1]
    assert not any(ln.startswith("``````") for ln in inner)   # nothing inside can close it


def test_mentions_are_defused_inside_and_outside_fences():
    assert issue_text.defuse("ask @nypko and @github/security") == f"ask @{ZW}nypko and @{ZW}github/security"
    assert issue_text.fence("mail me@x.example\n@all")[1:-1] == [f"mail me@{ZW}x.example", f"@{ZW}all"]


def test_spec_page_diff_with_backticks_and_mentions_stays_fenced(tmp_path):
    snaps = tmp_path / "snaps"
    snaps.mkdir()
    long = "\n".join(f"<p>Spec line number {i} with a value</p>" for i in range(40))
    (snaps / "phone-a-global.txt").write_text(specpages.page_text(long))
    report = tmp_path / "report.md"
    sheets = {"phone-a": {"sources": {"global": {"url": "https://brand.example/a"}}}}
    specpages.watch(snaps, report, sheets, lambda url: long.replace("number 3 ", "number 3 ```\n@nypko [click](https://evil.example) "))
    text = report.read_text()
    assert "````diff" in text and "@nypko" not in text and f"@{ZW}nypko" in text


def test_promo_lines_go_in_a_fence(tmp_path, monkeypatch):
    monkeypatch.setattr(promos, "REPORT", tmp_path / "promo.md")
    monkeypatch.setattr(promos, "pages", lambda name, cfg: ["https://shop.example/"])
    promos.write_report({"shop": ["10% off ```", "ping @someone"]}, [], [], {"shop": {"label": "Shop"}}, False)
    text = (tmp_path / "promo.md").read_text()
    assert "````\n10% off ```\nping @" + ZW + "someone\n````" in text and "- 10% off" not in text
