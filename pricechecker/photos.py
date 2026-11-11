"""Product photos: the brand's own photo of each phone (picked by hand, recorded in the phone's spec sheet as
`photo: {url, page, checked, credit?}`), processed once, locally, into two WebP files the site serves itself:
static/phones/<id>-s.webp and -m.webp. data/photos.json remembers which source each phone's files came from. A sheet
without `photo:` has no files: taking it out of a sheet (a brand asked for the photo to go) and running this removes them.

    python -m pricechecker.photos [ids…] [--force]      (exit status 1 when a phone failed or an id has no sheet)

Downloaded bytes are untrusted: they are only ever opened with Pillow, never executed."""
import argparse
import hashlib
import io
import json
import os
import sys
import warnings
from pathlib import Path

import requests
from PIL import Image, ImageChops, ImageOps

from . import http, specs

PHOTOS_DIR = Path("static/phones")
MANIFEST = Path("data/photos.json")
SIZES = {"s": (128, 160), "m": (368, 460)}
QUALITY = {"s": 82, "m": 85}
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
MIN_HEIGHT = 300      # source height after trimming
CONTENT = 0.92        # the phone fills at most this share of each side of the 4:5 frame (4 % margin all round)


class PhotoError(ValueError):
    pass


def _trim_box(img: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] < 255:
        return alpha.point(lambda a: 255 if a > 8 else 0).getbbox()
    rgb = img.convert("RGB")
    diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, rgb.getpixel((0, 0))))
    r, g, b = (c.point(lambda v: 255 if v > 12 else 0) for c in diff.split())
    return ImageChops.lighter(ImageChops.lighter(r, g), b).getbbox()


def frame(img: Image.Image) -> Image.Image:
    """RGBA, trimmed to the phone, centred on a transparent 4:5 canvas with a 4 % margin."""
    img = img.convert("RGBA")
    box = _trim_box(img)
    if box is None:
        raise PhotoError("the image is empty (nothing but background)")
    img = img.crop(box)
    w, h = img.size
    if h < MIN_HEIGHT:
        raise PhotoError(f"the photo is {h} px tall after trimming, under {MIN_HEIGHT} px")
    ch = max(h / CONTENT, w / CONTENT / 0.8)
    cw = round(ch * 0.8)
    ch = round(ch)
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    canvas.paste(img, ((cw - w) // 2, (ch - h) // 2))
    return canvas


def process(pid: str, data: bytes, out_dir: Path = PHOTOS_DIR) -> dict[str, str]:
    """Write <pid>-s.webp and <pid>-m.webp; return {size key: sha256[:10] of the file}."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")   # Pillow's DecompressionBombWarning must not slip through as a warning
            img = Image.open(io.BytesIO(data))
            if img.width * img.height > MAX_PIXELS:
                raise PhotoError(f"the image is {img.width}x{img.height} px, over the {MAX_PIXELS:,}-pixel limit")
            img.load()
            img = ImageOps.exif_transpose(img)
    except PhotoError:
        raise
    except Exception as e:   # anything that is not a decodable image
        raise PhotoError(f"not an image Pillow can read ({type(e).__name__})") from e
    framed = frame(img)
    bufs = {}
    for k, size in SIZES.items():
        small = framed.resize(size, Image.LANCZOS)
        small.putalpha(small.getchannel("A").point(lambda a: 0 if a <= 8 else a))   # LANCZOS ringing leaves faint halos
        buf = io.BytesIO()
        small.save(buf, "WEBP", quality=QUALITY[k], method=6)
        bufs[k] = buf.getvalue()
    out_dir.mkdir(parents=True, exist_ok=True)
    for k, b in bufs.items():   # both encoded before anything is written; each file replaced atomically
        _write_atomic(out_dir / f"{pid}-{k}.webp", b)
    return {k: hashlib.sha256(b).hexdigest()[:10] for k, b in bufs.items()}


def _write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)   # gone after the replace; after a failed write it must not stay (static/ is published)


def fetch(url: str) -> bytes:
    try:
        r = http.get(url, respect_robots=True, timeout=20, max_bytes=MAX_BYTES)
    except http.Blocked as e:
        raise PhotoError(str(e)) from e
    except requests.RequestException as e:
        raise PhotoError(f"download failed: {e}") from e
    ctype = r.headers.get("Content-Type", "")
    if not ctype.lower().startswith("image/"):
        raise PhotoError(f"not an image (Content-Type {ctype or 'missing'})")
    return r.content


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(MANIFEST, (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode())


def _sync(pid: str, sheet: dict, manifest: dict, force: bool) -> str:
    """Make one phone's files and manifest entry match its sheet; returns what was done (raises when that fails)."""
    url = (sheet.get("photo") or {}).get("url")
    paths = [PHOTOS_DIR / f"{pid}-{k}.webp" for k in SIZES]
    if not url:   # no photo, or one taken out of the sheet: its files and manifest entry go too (the site shows none either)
        if not any(p.exists() for p in paths) and pid not in manifest:
            return "no photo in the sheet"
        for p in paths:
            p.unlink(missing_ok=True)
        if manifest.pop(pid, None) is not None:
            _save_manifest(manifest)
        return "photo removed (no photo in the sheet)"
    if not force and all(p.exists() for p in paths) and manifest.get(pid, {}).get("url") == url:
        return "unchanged"
    data = fetch(url)
    files = process(pid, data, PHOTOS_DIR)
    manifest[pid] = {"url": url, "src_sha256": hashlib.sha256(data).hexdigest(), "files": files}
    _save_manifest(manifest)
    return "ok (" + ", ".join(f"{k} {round(p.stat().st_size / 1024)} KB" for k, p in zip(SIZES, paths, strict=True)) + ")"


def run(ids: list[str] | None = None, force: bool = False) -> tuple[list[str], list[str]]:
    """Each phone's photo brought in line with its sheet (all sheets without ids): (one message per phone and a closing
    count, the ids that failed - an id without a sheet included)."""
    sheets = specs.load()
    manifest = _load_manifest()
    msgs, failed = [], []
    for pid in ids or sorted(sheets):
        if pid not in sheets:
            msgs.append(f"{pid}: no spec sheet")
            failed.append(pid)
            continue
        try:
            msgs.append(f"{pid}: {_sync(pid, sheets[pid], manifest, force)}")
        except Exception as e:   # noqa: BLE001  one phone's failure (PhotoError, a full disk, ...) never stops the others
            msgs.append(f"{pid}: {e}" if isinstance(e, PhotoError) else f"{pid}: {type(e).__name__}: {e}")
            failed.append(pid)
    none = [p for p in sorted(sheets) if not all((PHOTOS_DIR / f"{p}-{k}.webp").exists() for k in SIZES)]
    msgs.append(f"photos: {len(none)} of {len(sheets)} phones have none: {', '.join(none)}")
    return msgs, failed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*", help="phone ids (default: every phone with a spec sheet)")
    ap.add_argument("--force", action="store_true", help="download and process again even when the photo url is unchanged")
    a = ap.parse_args(argv)
    msgs, failed = run(a.ids or None, a.force)
    print("\n".join(msgs))
    return 1 if failed else 0   # skipped (unchanged, no photo) and removed photos are fine


if __name__ == "__main__":
    sys.exit(main())
