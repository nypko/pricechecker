import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from pricechecker import photos


def _png(size, box, mode="RGBA", bg=(0, 0, 0, 0)):
    img = Image.new(mode, size, bg if mode == "RGBA" else (255, 255, 255))
    ImageDraw.Draw(img).rectangle(box, fill=(20, 30, 40, 255) if mode == "RGBA" else (20, 30, 40))
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def test_process_trims_frames_and_sizes(tmp_path):
    for data in (_png((600, 900), (100, 100, 499, 799)), _png((600, 900), (100, 100, 499, 799), mode="RGB")):
        photos.process("x", data, tmp_path)
        for k, (w, h) in photos.SIZES.items():
            im = Image.open(tmp_path / f"x-{k}.webp")
            assert im.size == (w, h)
            l, t, r, b = im.getchannel("A").getbbox()
            assert b - t <= round(h * 0.92) + 1 and t >= round(h * 0.04) - 1   # 4 % margin, content centred
            assert abs((l + r) / 2 - w / 2) <= 1


def test_process_handles_palette_png_with_transparency(tmp_path):
    img = Image.new("P", (400, 500), 0)
    img.info["transparency"] = 0
    ImageDraw.Draw(img).rectangle((50, 50, 349, 449), fill=1)
    b = io.BytesIO()
    img.save(b, "PNG", transparency=0)
    assert set(photos.process("p", b.getvalue(), tmp_path)) == {"s", "m"}


def test_process_refuses_html_and_tiny_images(tmp_path):
    with pytest.raises(photos.PhotoError):
        photos.process("h", b"<!doctype html><title>403</title>", tmp_path)
    with pytest.raises(photos.PhotoError, match="300"):
        photos.process("t", _png((200, 250), (10, 10, 189, 239)), tmp_path)


def test_run_skips_unchanged_and_goes_on_after_an_error(tmp_path, monkeypatch):
    sheets = {i: {"id": i, "photo": {"url": f"https://img.example/{i}.png"}} for i in "abc"}
    sheets["d"] = {"id": "d"}   # no photo in the sheet: not an error, just none
    manifest = tmp_path / "photos.json"
    manifest.write_text(json.dumps({"a": {"url": "https://img.example/a.png", "src_sha256": "x", "files": {"s": "1", "m": "2"}}}))
    out = tmp_path / "phones"
    out.mkdir()
    for k in "sm":
        (out / f"a-{k}.webp").write_bytes(b"x")
    monkeypatch.setattr(photos, "MANIFEST", manifest)
    monkeypatch.setattr(photos, "PHOTOS_DIR", out)
    monkeypatch.setattr(photos.specs, "load", lambda: sheets)
    calls = []

    def fake_fetch(url):
        calls.append(url)
        if url.endswith("b.png"):
            raise photos.PhotoError("not an image")
        return _png((600, 900), (100, 100, 499, 799))

    monkeypatch.setattr(photos, "fetch", fake_fetch)
    msgs, failed = photos.run()
    assert calls == ["https://img.example/b.png", "https://img.example/c.png"]
    assert any(m.startswith("b:") and "not an image" in m for m in msgs) and failed == ["b"]
    assert "a: unchanged" in msgs and "d: no photo in the sheet" in msgs
    assert (out / "c-s.webp").exists() and (out / "c-m.webp").exists()
    assert msgs[-1] == "photos: 2 of 4 phones have none: b, d"
    assert json.loads(manifest.read_text())["c"]["url"] == "https://img.example/c.png"
    assert manifest.read_text().endswith("\n")


class _Resp:
    def __init__(self, body=b"", ctype="image/png", status=200):
        self.headers = {"Content-Type": ctype, "Content-Length": str(len(body))}
        self.status_code = status
        self._body = body

    @property
    def content(self):
        return self._content

    def iter_content(self, n):
        for i in range(0, len(self._body), n):
            yield self._body[i:i + n]

    def close(self):
        pass

    def raise_for_status(self):
        pass


def _stub_transport(monkeypatch, resp):
    from pricechecker import http
    seen = {}

    def fake_get(url, **kw):
        seen.update(kw)
        return resp

    monkeypatch.setattr(http._session, "get", fake_get)
    monkeypatch.setattr(http, "allowed", lambda url: True)
    monkeypatch.setattr(http, "_wait", lambda host: None)
    return seen


def test_fetch_goes_through_http_with_timeout_and_refuses_bad_responses(monkeypatch):
    png = _png((600, 900), (100, 100, 499, 799))
    seen = _stub_transport(monkeypatch, _Resp(png))
    assert photos.fetch("https://img.example/a.png") == png
    assert seen["timeout"] == 20 and seen["stream"] is True
    _stub_transport(monkeypatch, _Resp(b"<html>", "text/html"))
    with pytest.raises(photos.PhotoError, match="text/html"):
        photos.fetch("https://img.example/a.png")
    _stub_transport(monkeypatch, _Resp(b"x" * (photos.MAX_BYTES + 1)))
    with pytest.raises(photos.PhotoError, match="limit"):
        photos.fetch("https://img.example/a.png")
    _stub_transport(monkeypatch, _Resp(b"", status=403))
    with pytest.raises(photos.PhotoError, match="403"):
        photos.fetch("https://img.example/a.png")


def test_process_applies_exif_orientation_and_refuses_huge_images(tmp_path, monkeypatch):
    img = Image.new("RGB", (900, 600), (255, 255, 255))
    ImageDraw.Draw(img).rectangle((100, 100, 799, 499), fill=(20, 30, 40))
    exif = Image.Exif()
    exif[0x0112] = 6   # rotate 90 degrees: stored landscape, shown portrait
    b = io.BytesIO()
    img.save(b, "JPEG", exif=exif)
    photos.process("r", b.getvalue(), tmp_path)
    l, t, r, bt = Image.open(tmp_path / "r-m.webp").getchannel("A").getbbox()
    assert (bt - t) > (r - l)   # portrait content: the 700x400 landscape body was turned upright
    monkeypatch.setattr(photos, "MAX_PIXELS", 1000)
    with pytest.raises(photos.PhotoError, match="600"):
        photos.process("big", b.getvalue(), tmp_path)


def test_run_survives_unexpected_errors_and_saves_manifest_per_phone(tmp_path, monkeypatch):
    sheets = {i: {"id": i, "photo": {"url": f"https://img.example/{i}.png"}} for i in "ab"}
    monkeypatch.setattr(photos, "MANIFEST", tmp_path / "photos.json")
    monkeypatch.setattr(photos, "PHOTOS_DIR", tmp_path / "phones")
    monkeypatch.setattr(photos.specs, "load", lambda: sheets)

    def fake_fetch(url):
        if url.endswith("a.png"):
            raise OSError("disk on fire")
        return _png((600, 900), (100, 100, 499, 799))

    monkeypatch.setattr(photos, "fetch", fake_fetch)
    msgs, failed = photos.run()
    assert any(m.startswith("a:") and "disk on fire" in m for m in msgs) and failed == ["a"]
    assert list(json.loads(photos.MANIFEST.read_text())) == ["b"]
    assert not list((tmp_path / "phones").glob("*.tmp"))


def _photo_files(out, *pids):
    out.mkdir(exist_ok=True)
    for pid in pids:
        for k in photos.SIZES:
            (out / f"{pid}-{k}.webp").write_bytes(b"x")


def test_run_removes_the_photo_of_a_sheet_without_one(tmp_path, monkeypatch):
    """Taking `photo:` out of a sheet (a brand asked for its photo to go) and running the tool deletes the phone's two
    files and its manifest entry; a phone that never had one is just reported, and the others are left alone."""
    sheets = {"a": {"id": "a"}, "b": {"id": "b"}, "c": {"id": "c", "photo": {"url": "https://img.example/c.png"}}, "d": {"id": "d"}}
    out = tmp_path / "phones"
    _photo_files(out, "a", "c")
    manifest = tmp_path / "photos.json"
    manifest.write_text(json.dumps({p: {"url": f"https://img.example/{p}.png", "src_sha256": "x", "files": {"s": "1", "m": "2"}}
                                    for p in "acd"}))   # d: its files already deleted by hand, the entry left
    monkeypatch.setattr(photos, "MANIFEST", manifest)
    monkeypatch.setattr(photos, "PHOTOS_DIR", out)
    monkeypatch.setattr(photos.specs, "load", lambda: sheets)
    monkeypatch.setattr(photos, "fetch", lambda url: pytest.fail(f"nothing to download, asked for {url}"))
    msgs, failed = photos.run()
    assert msgs[:4] == ["a: photo removed (no photo in the sheet)", "b: no photo in the sheet", "c: unchanged",
                        "d: photo removed (no photo in the sheet)"]
    assert failed == [] and sorted(f.name for f in out.iterdir()) == ["c-m.webp", "c-s.webp"]
    assert list(json.loads(manifest.read_text())) == ["c"]
    assert msgs[-1] == "photos: 3 of 4 phones have none: a, b, d"
    msgs, failed = photos.run(["a"])   # already gone: nothing left to remove
    assert msgs[0] == "a: no photo in the sheet" and failed == []


def test_main_exits_1_when_a_phone_failed(tmp_path, monkeypatch, capsys):
    sheets = {"a": {"id": "a", "photo": {"url": "https://img.example/a.png"}}, "b": {"id": "b", "photo": {"url": "https://img.example/b.png"}},
              "n": {"id": "n"}}
    monkeypatch.setattr(photos, "MANIFEST", tmp_path / "photos.json")
    monkeypatch.setattr(photos, "PHOTOS_DIR", tmp_path / "phones")
    monkeypatch.setattr(photos.specs, "load", lambda: sheets)

    def fake_fetch(url):
        if url.endswith("b.png"):
            raise photos.PhotoError("not an image")
        return _png((600, 900), (100, 100, 499, 799))

    monkeypatch.setattr(photos, "fetch", fake_fetch)
    assert photos.main(["a", "n"]) == 0   # processed, and no photo in the sheet: fine
    assert photos.main(["a"]) == 0        # unchanged: fine
    assert photos.main([]) == 1           # b could not be processed
    assert photos.main(["typo"]) == 1     # no such phone
    out = capsys.readouterr().out
    assert "a: ok (" in out and "n: no photo in the sheet" in out and "a: unchanged" in out
    assert "b: not an image" in out and "typo: no spec sheet" in out


def test_write_atomic_leaves_no_tmp_file_when_a_write_fails(tmp_path, monkeypatch):
    """A failed write (disk full while writing, or at the rename) leaves the old file and no .tmp beside it: static/ is
    copied into the published site."""
    target = tmp_path / "x-s.webp"
    target.write_bytes(b"old")
    real_write = Path.write_bytes

    def half_written(self, data):
        real_write(self, data[:1])
        raise OSError(28, "No space left on device")

    with monkeypatch.context() as m:
        m.setattr(Path, "write_bytes", half_written)
        with pytest.raises(OSError, match="No space left"):
            photos._write_atomic(target, b"new")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["x-s.webp"] and target.read_bytes() == b"old"

    def no_rename(src, dst):
        raise OSError(28, "No space left on device")

    with monkeypatch.context() as m:
        m.setattr(photos.os, "replace", no_rename)
        with pytest.raises(OSError, match="No space left"):
            photos._write_atomic(target, b"new")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["x-s.webp"] and target.read_bytes() == b"old"
    photos._write_atomic(target, b"new")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["x-s.webp"] and target.read_bytes() == b"new"
