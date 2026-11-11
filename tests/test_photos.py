import io
import json

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
    msgs = photos.run()
    assert calls == ["https://img.example/b.png", "https://img.example/c.png"]
    assert any(m.startswith("b:") and "not an image" in m for m in msgs)
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
    msgs = photos.run()
    assert any(m.startswith("a:") and "disk on fire" in m for m in msgs)
    assert list(json.loads(photos.MANIFEST.read_text())) == ["b"]
    assert not list((tmp_path / "phones").glob("*.tmp"))
