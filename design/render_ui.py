#!/usr/bin/env python3
"""Tactile Silence — Makropad configurator design study. SVG -> PNG."""
import cairosvg

W, H = 2560, 1600
BLUE = "#0071E3"
INK = "#1D1D1F"
GRAY2 = "#3A3A3C"
GRAY5 = "#86868B"
GRAY6 = "#AEAEB2"
HAIR = "#E8E8EC"
SANS = "Instrument Sans"
THIN = "Jura Light"
MED = "Jura Medium"
MONO = "Geist Mono"
SYM = "DejaVu Sans"

svg = []
svg.append(f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">')

# ---------- defs ----------
svg.append(f'''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#F7F7F9"/><stop offset="1" stop-color="#EFEFF2"/>
</linearGradient>
<linearGradient id="alu" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#EDEDEF"/><stop offset="1" stop-color="#DFDFE3"/>
</linearGradient>
<radialGradient id="knobface" cx="0.42" cy="0.36" r="0.85">
  <stop offset="0" stop-color="#FBFBFC"/><stop offset="1" stop-color="#DCDCE0"/>
</radialGradient>
<linearGradient id="knobrim" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#C9C9CE"/><stop offset="1" stop-color="#9C9CA3"/>
</linearGradient>
<linearGradient id="keyface" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#FEFEFE"/><stop offset="1" stop-color="#F4F4F6"/>
</linearGradient>
<linearGradient id="btn" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#1482EB"/><stop offset="1" stop-color="#0068D6"/>
</linearGradient>
</defs>''')

svg.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

# ---------- window shadow (layered soft) ----------
wx, wy, ww, wh = 200, 116, 2160, 1368
for i in range(12, 0, -1):
    a = 0.016
    svg.append(f'<rect x="{wx-i*1.6}" y="{wy-i*1.2+i*2.2}" width="{ww+i*3.2}" height="{wh+i*2.4}" rx="{30+i*1.6}" fill="#1D1D1F" opacity="{a}"/>')

# ---------- window ----------
svg.append(f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="28" fill="#FFFFFF" stroke="#E2E2E6" stroke-width="1.5"/>')

# titlebar
for cx, c, sc in ((wx+52, "#FF5F57", "#E0443E"), (wx+92, "#FEBC2E", "#D89E24"), (wx+132, "#28C840", "#1FA331")):
    svg.append(f'<circle cx="{cx}" cy="{wy+46}" r="11" fill="{c}" stroke="{sc}" stroke-width="1"/>')
svg.append(f'<text x="{wx+ww/2}" y="{wy+56}" font-family="{SANS}" font-size="27" fill="{INK}" text-anchor="middle" font-weight="bold">Makropad</text>')
svg.append(f'<text x="{wx+ww-48}" y="{wy+54}" font-family="{MONO}" font-size="19" fill="#C7C7CC" text-anchor="end" letter-spacing="2">514C:8850</text>')
svg.append(f'<line x1="{wx}" y1="{wy+92}" x2="{wx+ww}" y2="{wy+92}" stroke="{HAIR}" stroke-width="1.5"/>')

# vertical divider between panes
divx = wx + 1020
svg.append(f'<line x1="{divx}" y1="{wy+92}" x2="{divx}" y2="{wy+wh}" stroke="{HAIR}" stroke-width="1.5"/>')
# left pane wash
svg.append(f'<path d="M {wx} {wy+92} H {divx} V {wy+wh-28} Q {divx} {wy+wh} {divx-28} {wy+wh} H {wx+28} Q {wx} {wy+wh} {wx} {wy+wh-28} Z" fill="#FAFAFB"/>')
svg.append(f'<line x1="{divx}" y1="{wy+92}" x2="{divx}" y2="{wy+wh}" stroke="{HAIR}" stroke-width="1.5"/>')

# ---------- device ----------
dx, dy, dw, dh = wx+170, wy+180, 680, 1050
svg.append(f'<rect x="{dx+3}" y="{dy+7}" width="{dw}" height="{dh}" rx="40" fill="#B9B9BF" opacity="0.55"/>')
svg.append(f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="40" fill="url(#alu)" stroke="#CFCFD4" stroke-width="1.5"/>')
svg.append(f'<rect x="{dx+1.5}" y="{dy+1.5}" width="{dw-3}" height="{dh-3}" rx="38" fill="none" stroke="#FFFFFF" stroke-width="1.5" opacity="0.7"/>')

# knobs: two small, one medium, one large (as on the physical device)
knob_y = dy + 128
knobs = [(dx+105, 46), (dx+235, 46), (dx+390, 60), (dx+565, 80)]
for i, (kx, r) in enumerate(knobs):
    svg.append(f'<circle cx="{kx}" cy="{knob_y+4}" r="{r}" fill="#A8A8AE" opacity="0.5"/>')
    svg.append(f'<circle cx="{kx}" cy="{knob_y}" r="{r}" fill="url(#knobrim)"/>')
    svg.append(f'<circle cx="{kx}" cy="{knob_y}" r="{r-5}" fill="url(#knobface)"/>')
    # indicator dot at 315 degrees
    ind_r = r - 16
    svg.append(f'<circle cx="{kx - ind_r*0.7071:.1f}" cy="{knob_y - ind_r*0.7071:.1f}" r="4.5" fill="{GRAY5}"/>')

# keys 4 rows x 3 cols; real bindings from config
labels = [
    [("⌘", "C"), ("⌘", "V"), ("⌘", "X")],
    [("⌘", "Z"), ("⇧⌘", "Z"), ("⌘", "A")],
    [("⌘", "Tab"), ("", "F13"), ("⌘", "W")],
    [("⇧⌘", "4"), ("", "F14"), ("", "F15")],
]
kw, kh, gap = 176, 158, 26
gx = dx + (dw - 3*kw - 2*gap)/2
gy = knob_y + 118
for r in range(4):
    for c in range(3):
        x, y = gx + c*(kw+gap), gy + r*(kh+gap)
        sel = (r == 0 and c == 0)
        svg.append(f'<rect x="{x}" y="{y+3}" width="{kw}" height="{kh}" rx="22" fill="#C4C4C9"/>')
        face = "#F0F7FF" if sel else "url(#keyface)"
        edge = BLUE if sel else "#D6D6DA"
        swid = 3 if sel else 1.5
        svg.append(f'<rect x="{x}" y="{y}" width="{kw}" height="{kh}" rx="22" fill="{face}" stroke="{edge}" stroke-width="{swid}"/>')
        if sel:
            svg.append(f'<rect x="{x-6}" y="{y-6}" width="{kw+12}" height="{kh+12}" rx="27" fill="none" stroke="{BLUE}" stroke-width="2" opacity="0.25"/>')
        mod, key = labels[r][c]
        color = BLUE if sel else GRAY2
        cxm, cym = x + kw/2, y + kh/2 + 13
        if mod:
            fs = 32 if len(mod) + len(key) > 3 else 38
            svg.append(f'<text x="{cxm}" y="{cym}" text-anchor="middle" font-size="{fs}">'
                       f'<tspan font-family="{SYM}" fill="{color}">{mod}</tspan>'
                       f'<tspan font-family="{SANS}" fill="{color}" dx="6">{key}</tspan></text>')
        else:
            fs = 30 if len(key) > 2 else 38
            svg.append(f'<text x="{cxm}" y="{cym}" text-anchor="middle" font-family="{SANS}" font-size="{fs}" fill="{color}">{key}</text>')

# caption under device
svg.append(f'<text x="{dx+dw/2}" y="{dy+dh+52}" text-anchor="middle" font-family="{MONO}" font-size="18" fill="#C0C0C5" letter-spacing="3">@XZKJ-12key_4knob</text>')

# ---------- inspector ----------
ix = divx + 96
iw = wx + ww - 96 - ix

svg.append(f'<text x="{ix}" y="{wy+205}" font-family="{MED}" font-size="22" fill="{GRAY5}" letter-spacing="5">KEY 1 · ROW 1 · COLUMN 1</text>')

# big binding display
svg.append(f'<text x="{ix-4}" y="{wy+345}" font-size="112">'
           f'<tspan font-family="{SYM}" fill="{INK}">⌘</tspan>'
           f'<tspan font-family="{THIN}" fill="{INK}" dx="14">C</tspan></text>')
svg.append(f'<text x="{ix}" y="{wy+400}" font-family="{SANS}" font-size="23" fill="{GRAY6}">Copy — sends Cmd + C</text>')

svg.append(f'<line x1="{ix}" y1="{wy+470}" x2="{ix+iw}" y2="{wy+470}" stroke="{HAIR}" stroke-width="1.5"/>')

# segmented control
seg_y = wy + 520
seg_w, seg_h = 620, 68
svg.append(f'<rect x="{ix}" y="{seg_y}" width="{seg_w}" height="{seg_h}" rx="17" fill="#F1F1F4"/>')
svg.append(f'<rect x="{ix+5}" y="{seg_y+5}" width="{seg_w/3-10}" height="{seg_h-10}" rx="13" fill="#FFFFFF" stroke="#E0E0E4" stroke-width="1"/>')
for i, t in enumerate(("Keyboard", "Media", "Mouse")):
    fill = INK if i == 0 else GRAY5
    weight = ' font-weight="bold"' if i == 0 else ""
    svg.append(f'<text x="{ix + seg_w/6 + i*seg_w/3}" y="{seg_y+seg_h/2+9}" text-anchor="middle" font-family="{SANS}" font-size="25" fill="{fill}"{weight}>{t}</text>')

# sequence section
sq_y = seg_y + 150
svg.append(f'<text x="{ix}" y="{sq_y}" font-family="{MED}" font-size="20" fill="{GRAY5}" letter-spacing="5">SEKVENS</text>')
chip_y = sq_y + 32
def chip(x, sym, fam, w=92):
    svg.append(f'<rect x="{x}" y="{chip_y}" width="{w}" height="{92}" rx="20" fill="#FFFFFF" stroke="#DCDCE0" stroke-width="1.5"/>')
    svg.append(f'<rect x="{x}" y="{chip_y+2}" width="{w}" height="{90}" rx="20" fill="none" stroke="#F2F2F4" stroke-width="1"/>')
    svg.append(f'<text x="{x+w/2}" y="{chip_y+60}" text-anchor="middle" font-family="{fam}" font-size="40" fill="{GRAY2}">{sym}</text>')
    return x + w
nx = chip(ix, "⌘", SYM)
svg.append(f'<text x="{nx+30}" y="{chip_y+60}" font-family="{THIN}" font-size="36" fill="#C7C7CC">+</text>')
nx = chip(nx+72, "C", SANS)
svg.append(f'<rect x="{nx+40}" y="{chip_y}" width="92" height="92" rx="20" fill="none" stroke="#D6D6DA" stroke-width="1.5" stroke-dasharray="7 8"/>')
svg.append(f'<text x="{nx+86}" y="{chip_y+58}" text-anchor="middle" font-family="{THIN}" font-size="42" fill="#B9B9BF">+</text>')

svg.append(f'<line x1="{ix}" y1="{chip_y+170}" x2="{ix+iw}" y2="{chip_y+170}" stroke="{HAIR}" stroke-width="1.5"/>')

# layer section
ly = chip_y + 245
svg.append(f'<text x="{ix}" y="{ly}" font-family="{MED}" font-size="20" fill="{GRAY5}" letter-spacing="5">LAYER</text>')
for i in range(3):
    cx = ix + 30 + i*104
    cy = ly + 62
    if i == 0:
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="30" fill="{BLUE}"/>')
        svg.append(f'<text x="{cx}" y="{cy+9}" text-anchor="middle" font-family="{SANS}" font-size="26" fill="#FFFFFF" font-weight="bold">1</text>')
    else:
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="30" fill="#FFFFFF" stroke="#D6D6DA" stroke-width="1.5"/>')
        svg.append(f'<text x="{cx}" y="{cy+9}" text-anchor="middle" font-family="{SANS}" font-size="26" fill="{GRAY6}">{i+1}</text>')

# buttons bottom
by = wy + wh - 150
svg.append(f'<text x="{ix}" y="{by+47}" font-family="{MONO}" font-size="17" fill="#C7C7CC" letter-spacing="2">ID 04 · 24 BINDINGS</text>')
bw, bh = 400, 78
bx = ix + iw - bw
svg.append(f'<rect x="{bx}" y="{by+6}" width="{bw}" height="{bh}" rx="18" fill="{BLUE}" opacity="0.25"/>')
svg.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="18" fill="url(#btn)"/>')
svg.append(f'<text x="{bx+bw/2}" y="{by+bh/2+9}" text-anchor="middle" font-family="{SANS}" font-size="27" fill="#FFFFFF" font-weight="bold">Write to keyboard</text>')
gx2 = bx - 250
svg.append(f'<rect x="{gx2}" y="{by}" width="220" height="{bh}" rx="18" fill="#FFFFFF" stroke="#D6D6DA" stroke-width="1.5"/>')
svg.append(f'<text x="{gx2+110}" y="{by+bh/2+9}" text-anchor="middle" font-family="{SANS}" font-size="26" fill="{GRAY2}">Reset</text>')

# signature
svg.append(f'<text x="{W-64}" y="{H-40}" text-anchor="end" font-family="{THIN}" font-size="20" fill="#C4C4C9" letter-spacing="6">TACTILE SILENCE</text>')

svg.append('</svg>')
doc = "\n".join(svg)

with open("ui.svg", "w") as f:
    f.write(doc)
cairosvg.svg2png(bytestring=doc.encode(), write_to="taktil_stillhet_makropad.png",
                 output_width=W, output_height=H)
print("rendered")
