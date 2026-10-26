from pricechecker import specpages

SHEETS = {"phone-a": {"sources": {"global": {"url": "https://brand.example/a"}}}}
LONG = "\n".join(f"<p>Spec line number {i} with a value</p>" for i in range(40))


def test_page_text_strips_scripts_and_blank_lines():
    html = "<html><head><style>p{}</style><script>var x=1;</script></head><body><p>  Chip </p>\n\n<div> </div><li>Snapdragon<b>8</b></li></body></html>"
    assert specpages.page_text(html) == "Chip\nSnapdragon\n8"


def _setup(tmp_path, old_html):
    snaps = tmp_path / "snaps"
    snaps.mkdir()
    (snaps / "phone-a-global.txt").write_text(specpages.page_text(old_html))
    return snaps, tmp_path / "report.md"


def test_watch_reports_changed_text_only(tmp_path):
    snaps, report = _setup(tmp_path, LONG + "<p>Updated 12</p>")
    # same text, only a counter digit line differs -> no report
    specpages.watch(snaps, report, SHEETS, lambda url: LONG + "<p>Updated 12</p><p>345</p>")
    assert not report.exists()
    # a changed spec line -> reported with the phone
    specpages.watch(snaps, report, SHEETS, lambda url: LONG.replace("number 3 ", "number three ") + "<p>Updated 12</p>")
    assert "phone-a" in report.read_text() and "number three" in report.read_text()


def test_watch_short_js_shell_is_check_by_hand(tmp_path):
    snaps, report = _setup(tmp_path, LONG)
    specpages.watch(snaps, report, SHEETS, lambda url: "<html><body><div id=app></div><script>x</script></body></html>")
    text = report.read_text()
    assert "check by hand" in text and "phone-a" in text


def test_fetch_saves_what_the_watch_will_see(tmp_path, monkeypatch):
    monkeypatch.setattr(specpages.shutil, "which", lambda n: "/usr/bin/chromium")
    monkeypatch.setattr(specpages.specs, "load", lambda: SHEETS)
    monkeypatch.setattr(specpages, "_get", lambda url: LONG)
    (path,) = specpages.fetch("phone-a", "global", tmp_path)
    assert path.read_text() == specpages.page_text(LONG) + "\n"
