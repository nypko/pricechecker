"""Draw the DoorPrice D: IBM Plex Sans Bold's own 'D' with the door-phone filling its counter.
The glyph outline was read from static/fonts/plex-sans-700.woff2 with fonttools; this script needs only Python.
The D is drawn solid; the door's surface is cut out of it (an SVG mask), so the page shows through the door and
the frame, screen bezel, handle and slot stay in the letter's ink. The screen glass is painted in brand blue on top.
Usage: python tools/door_logo.py <out-dir>   (writes full.svg and simple.svg previews)"""
OUTER = ("M77 698H340Q409 698 466 676Q523 654 563 610.5Q603 567 625 501.5Q647 436 647 349Q647 262 625 196.5Q603 131 563 87.5"
         "Q523 44 466 22Q409 0 340 0H77Z")
COUNTER = "M340 135Q408 135 447 173Q486 211 486 295V403Q486 487 447 525Q408 563 340 563H229V135Z"
ADV, CAP = 697, 698
# the door fills the counter's height and starts at its left edge; width from the reference door (169:365)
X0, Y0, H = 229, 135, 428
W = round(H * 169 / 365 * 1.15)              # 228: the reference proportions, 15% wider (left edge unchanged)
FRAME = 16                                   # frame in the letter's ink, merges with the D's stem and bowl

def box(fx, fy, fw, fh):
    """Rectangle from fractions of the door (fy from the TOP), in glyph units with y up."""
    return X0 + fx * W, Y0 + H - (fy + fh) * H, fw * W, fh * H

def rect(x, y, w, h, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" {attrs}/>'

def mark(detail, uid, ink="currentColor", glass_attr='class="dp-glass"', extra=""):
    """The door-phone: a rounded door whose glass is a phone screen, its handle a side button and its letterbox slot
    a home bar. Cut out of the solid D (mask) so the page shows through; drawn whole, on top of the D's bowl.
    One drawing reads at every size, so `detail` is accepted for compatibility and ignored."""
    R = 40                                         # phone-like corner radius of the door
    ix, iy, iw, ih = X0 + FRAME, Y0 + FRAME, W - 2 * FRAME, H - 2 * FRAME
    m = [rect(0, 0, ADV, CAP, fill="white"),
         rect(ix, iy, iw, ih, rx=R - FRAME, fill="black")]                       # door surface, cut through the letter
    g = 20                                         # screen = the door's glass, top two thirds, bezel in ink
    sx, sw, sh = ix + g, iw - 2 * g, ih * .64
    sy = iy + ih - g - sh
    m.append(rect(sx, sy, sw, sh, rx=16, fill="white"))
    m.append(rect(ix + iw - 30, Y0 + H * .40, 16, 74, rx=8, fill="white"))       # handle = side button
    m.append(rect(X0 + W / 2 - 40, iy + 34, 80, 16, rx=8, fill="white"))         # letterbox slot = home bar
    glass = rect(sx + 10, sy + 10, sw - 20, sh - 20, rx=10).replace("/>", f" {glass_attr}/>")
    return (f'<svg viewBox="0 0 {ADV} {CAP}" {extra}><g transform="matrix(1 0 0 -1 0 {CAP})">'
            f'<mask id="{uid}m" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="0" y="0" width="{ADV}" height="{CAP}">'
            f'{"".join(m)}</mask><path d="{OUTER}" fill="{ink}" mask="url(#{uid}m)"/>{glass}</g></svg>')

if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    for d in ("full",):
        with open(f"{out}/{d}.svg", "w") as f:
            f.write(mark(d, "p" + d, "#121821", 'fill="#1d4ed8"', 'xmlns="http://www.w3.org/2000/svg" width="697" height="698"'))
