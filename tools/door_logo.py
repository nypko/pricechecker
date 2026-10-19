"""Draw the DoorPrice D: IBM Plex Sans Bold's own 'D' with the brand's panel door filling its counter.
The glyph outline was read from static/fonts/plex-sans-700.woff2 with fonttools; this script needs only Python.
The D is drawn solid; the door's surface is cut out of it (an SVG mask), so the page shows through the door and
the frame, mullions, panels and knob stay in the letter's ink. Glass panes are painted in brand blue on top.
Usage: python tools/door_logo.py <out-dir>   (writes full.svg and simple.svg previews)"""
OUTER = ("M77 698H340Q409 698 466 676Q523 654 563 610.5Q603 567 625 501.5Q647 436 647 349Q647 262 625 196.5Q603 131 563 87.5"
         "Q523 44 466 22Q409 0 340 0H77Z")
COUNTER = "M340 135Q408 135 447 173Q486 211 486 295V403Q486 487 447 525Q408 563 340 563H229V135Z"
ADV, CAP = 697, 698
# the door fills the counter's height and starts at its left edge; width from the reference door (169:365)
X0, Y0, H = 229, 135, 428
W = round(H * 169 / 365)                     # 198
FRAME = 16                                   # frame in the letter's ink, merges with the D's stem and bowl

def box(fx, fy, fw, fh):
    """Rectangle from fractions of the door (fy from the TOP), in glyph units with y up."""
    return X0 + fx * W, Y0 + H - (fy + fh) * H, fw * W, fh * H

def rect(x, y, w, h, **a):
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" {attrs}/>'

def mark(detail, uid, ink="currentColor", glass_attr='class="dp-glass"', extra=""):
    full = detail == "full"
    # mask: white = ink stays, black = cut through to the page
    m = [rect(0, 0, ADV, CAP, fill="white"),
         f'<clipPath id="{uid}c"><path d="{COUNTER}"/></clipPath>',
         f'<g clip-path="url(#{uid}c)">' + rect(X0 + FRAME, Y0 + FRAME, W - 2 * FRAME, H - 2 * FRAME, fill="black") + "</g>"]
    wx, wy, ww, wh = box(.15, .07, .70, .40)
    m.append(rect(wx, wy, ww, wh, fill="white"))                       # window frame and mullions stay ink
    panes = []
    if full:
        g = 12
        pw, ph = (ww - 3 * g) / 2, (wh - 3 * g) / 2
        panes = [rect(wx + g + i * (pw + g), wy + g + j * (ph + g), pw, ph) for i in range(2) for j in range(2)]
        px, py, pw2, ph2 = box(.15, .58, .70, .34)
        gap, sw = 14, 10
        cw, chh = (pw2 - gap) / 2, (ph2 - gap) / 2
        m += [rect(px + i * (cw + gap), py + j * (chh + gap), cw, chh, fill="none", stroke="white", stroke_width=sw) for i in range(2) for j in range(2)]
        kr = 14
    else:
        g = 14
        panes = [rect(wx + g, wy + g, ww - 2 * g, wh - 2 * g)]
        kr = 22
    kx, ky = X0 + .78 * W, Y0 + H - .50 * H
    m.append(f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="{kr}" fill="white"/>')
    glass = "".join(p.replace("/>", f" {glass_attr}/>") for p in panes)
    # everything lives in glyph space (y up) inside one flipped group; the mask uses the masked path's user space
    return (f'<svg viewBox="0 0 {ADV} {CAP}" {extra}><g transform="matrix(1 0 0 -1 0 {CAP})">'
            f'<mask id="{uid}m" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="0" y="0" width="{ADV}" height="{CAP}">'
            f'{"".join(m)}</mask><path d="{OUTER}" fill="{ink}" mask="url(#{uid}m)"/>{glass}</g></svg>')

if __name__ == "__main__":
    import sys
    out = sys.argv[1]
    for d in ("full", "simple"):
        with open(f"{out}/{d}.svg", "w") as f:
            f.write(mark(d, "p" + d, "#121821", 'fill="#1d4ed8"', 'xmlns="http://www.w3.org/2000/svg" width="697" height="698"'))
