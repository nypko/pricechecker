"""Share images (1200 x 630 PNG) for link previews on Reddit, Facebook, X, Telegram, WhatsApp: one per phone with its
cheapest delivered price, and one for the rest of the site. Drawn with Pillow in the site's own type (IBM Plex Sans,
read straight from static/fonts) and colours; the DoorPrice D comes from static/icons/icon-512.png."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, PAD = 1200, 630, 72
INK, MUTED, BRAND, BG, LINE = "#121821", "#556170", "#1d4ed8", "#ffffff", "#dfe4ea"
SAVE = "#0b7a43"
BADGE = {"global": ("#e6efff", "#1e3fa8"), "china": ("#fdf0e1", "#8a4208")}
FONTS = Path("static/fonts")
_D = None


def _font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"plex-sans-{weight}.woff2"), size)


def _mark() -> Image.Image:
    """The D with the door-phone, cropped from the 512 px icon (white around it, so it sits on the white card)."""
    global _D
    if _D is None:
        icon = Image.open("static/icons/icon-512.png").convert("RGB")
        _D = icon.crop(icon.convert("L").point(lambda v: 255 if v < 128 else 0).getbbox())
    return _D


def _lockup(img: Image.Image, d: ImageDraw.ImageDraw, x: int, y: int, cap: int) -> None:
    """[D]oorPrice: the D mark at cap height, then "oor" in ink and "Price" in brand blue, on one baseline."""
    mark = _mark()
    mw = round(mark.width * cap / mark.height)
    img.paste(mark.resize((mw, cap), Image.LANCZOS), (x, y))
    f = _font(700, round(cap / 0.698))   # Plex cap height is 0.698 em
    base = y + cap
    x += mw + round(cap * 0.04)
    d.text((x, base), "oor", font=f, fill=INK, anchor="ls")
    d.text((x + d.textlength("oor", font=f), base), "Price", font=f, fill=BRAND, anchor="ls")


def _fit(d: ImageDraw.ImageDraw, text: str, weight: int, size: int, width: int) -> ImageFont.FreeTypeFont:
    """The largest font up to `size` that fits `text` on one line in `width`."""
    while size > 28 and d.textlength(text, font=_font(weight, size)) > width:
        size -= 2
    return _font(weight, size)


def _base(footer: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _lockup(img, d, PAD, PAD - 8, 46)
    d.text((W - PAD, PAD + 38), "doorprice.app", font=_font(600, 28), fill=MUTED, anchor="rs")
    d.line([(PAD, H - 104), (W - PAD, H - 104)], fill=LINE, width=2)
    d.text((PAD, H - 56), footer, font=_font(400, 28), fill=MUTED, anchor="ls")
    return img, d


def phone_card(path: Path, name: str, editions: list[tuple[str, str]], price: str | None, note: str, n_stores: int) -> None:
    """name, its versions [("global", "Global"), ("china", "China")], the headline ("from €987") and what it covers
    ("delivered to the EU" or "+ import tax, delivered to the EU")."""
    img, d = _base(f"{n_stores} import store{'s' if n_stores != 1 else ''} compared · prices checked every hour")
    d.text((PAD, 236), name, font=_fit(d, name, 700, 76, W - 2 * PAD), fill=INK, anchor="ls")
    x, bf = PAD, _font(700, 26)
    for ed, label in editions:   # version badges, as on the site
        bg, fg = BADGE.get(ed, BADGE["global"])
        w = d.textlength(label + " version", font=bf) + 32
        d.rounded_rectangle([x, 262, x + w, 304], radius=21, fill=bg)
        d.text((x + 16, 292), label + " version", font=bf, fill=fg, anchor="ls")
        x += w + 12
    if price:
        pf = _font(700, 112)
        d.text((PAD, 446), price, font=pf, fill=INK, anchor="ls")
        d.text((PAD, 494), note, font=_font(600, 34), fill=SAVE if note.startswith("delivered") else INK, anchor="ls")
    else:
        d.text((PAD, 420), "Out of stock at every store right now", font=_font(600, 44), fill=MUTED, anchor="ls")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.quantize(64).save(path)   # 64 colours: text antialiasing survives, files are ~3x smaller and quick to write


def site_card(path: Path, n_phones: int, n_stores: int) -> None:
    img, d = _base(f"{n_phones} phones · {n_stores} import stores · checked every hour")
    f = _font(700, 64)
    d.text((PAD, 236), "What a flagship phone", font=f, fill=INK, anchor="ls")
    d.text((PAD, 312), "really costs, delivered", font=f, fill=INK, anchor="ls")
    d.text((PAD, 388), "to your door", font=f, fill=BRAND, anchor="ls")
    d.text((PAD, 448), "Shipping, payment fees and import tax worked in.", font=_font(400, 30), fill=MUTED, anchor="ls")
    d.text((PAD, 488), "Global and China versions side by side.", font=_font(400, 30), fill=MUTED, anchor="ls")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.quantize(64).save(path)   # 64 colours: text antialiasing survives, files are ~3x smaller and quick to write
