"""Draw the DoorPrice D: IBM Plex Sans Bold's own 'D' outline with the brand's panel door in its counter.
The glyph path below was read from static/fonts/plex-sans-700.woff2 with fonttools; this script needs only Python.
Usage: python tools/door_logo.py <out-dir>   (writes full.svg and simple.svg previews)"""
GLYPH = ("M77 698H340Q409 698 466 676Q523 654 563 610.5Q603 567 625 501.5Q647 436 647 349Q647 262 625 196.5Q603 131 563 87.5"
         "Q523 44 466 22Q409 0 340 0H77ZM340 135Q408 135 447 173Q486 211 486 295V403Q486 487 447 525Q408 563 340 563H229V135Z")
ADV, CAP = 697, 698
# door in font units (y-up), inside the counter (x 229-486, y 135-563); proportions from the reference (w:h = 169:365)
X0, Y0, W, H = 253, 162, 170, 368          # left, bottom, width, height

def door(detail, ink, glass):
    """SVG elements in y-down coordinates (the outer <g> flips the glyph space)."""
    def r(x, y, w, h):   # rect from fractions of the door box, y measured from the TOP of the door
        return X0 + x * W, (Y0 + H) - (y + h) * H, w * W, h * H   # -> font units, y-up bottom-left
    out = []
    sw = 16 if detail == "full" else 30
    out.append(f'<rect x="{X0}" y="{Y0}" width="{W}" height="{H}" fill="none" stroke="{ink}" stroke-width="{sw}"/>')
    wx, wy, ww, wh = r(.15, .07, .70, .40)        # window
    if detail == "full":
        g = 9                                    # mullions: 2x2 panes
        pw, ph = (ww - 3 * g) / 2, (wh - 3 * g) / 2
        for i in range(2):
            for j in range(2):
                out.append(f'<rect x="{wx + g + i * (pw + g):.1f}" y="{wy + g + j * (ph + g):.1f}" width="{pw:.1f}" height="{ph:.1f}" fill="{glass}"/>')
        out.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="none" stroke="{ink}" stroke-width="7"/>')
        px, py, pw2, ph2 = r(.15, .58, .70, .34)  # lower panels: 2x2
        gap = 12
        cw, chh = (pw2 - gap) / 2, (ph2 - gap) / 2
        for i in range(2):
            for j in range(2):
                out.append(f'<rect x="{px + i * (cw + gap):.1f}" y="{py + j * (chh + gap):.1f}" width="{cw:.1f}" height="{chh:.1f}" fill="none" stroke="{ink}" stroke-width="9"/>')
        kr = 13
    else:
        out.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" fill="{glass}"/>')
        kr = 20
    kx, ky = X0 + .86 * W, (Y0 + H) - .50 * H
    out.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="{kr}" fill="{ink}"/>')
    return "".join(out)

def svg(detail, ink, glass, extra=""):
    # glyph space is y-up; flip into the SVG's y-down box of width ADV and height CAP
    return (f'<svg viewBox="0 0 {ADV} {CAP}" {extra}><g transform="matrix(1 0 0 -1 0 {CAP})">'
            f'<path d="{GLYPH}" fill="{ink}"/>{door(detail, ink, glass)}</g></svg>')

if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    with open(f"{out}/full.svg", "w") as f: f.write(svg("full", "#121821", "#1d4ed8", 'xmlns="http://www.w3.org/2000/svg" width="697" height="698"'))
    with open(f"{out}/simple.svg", "w") as f: f.write(svg("simple", "#121821", "#1d4ed8", 'xmlns="http://www.w3.org/2000/svg" width="697" height="698"'))
