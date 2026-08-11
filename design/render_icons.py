#!/usr/bin/env python3
"""Icons: app icon and menu-bar icon (template).

    python3 render_icons.py      # writes PNGs to ../build_assets/

Requires cairosvg (and libcairo). build.sh creates the .icns file with iconutil,
which is available only on macOS.
"""
import os
import subprocess

import cairosvg

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build_assets"))
os.makedirs(OUT, exist_ok=True)


def app_icon_svg():
    """The pad in silhouette: knob and keys, recognizable at 32 px."""
    # Simplified body: round lobe at top right, keys below.
    return '''<svg width="1024" height="1024" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">
    <stop offset="0" stop-color="#3B82F6"/><stop offset="1" stop-color="#0057C8"/>
  </linearGradient>
  <linearGradient id="knob" x1="0" y1="0" x2="0.3" y2="1">
    <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#DDE9FB"/>
  </linearGradient>
  <filter id="sh" x="-30%" y="-30%" width="160%" height="160%">
    <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#00204D" flood-opacity="0.30"/>
  </filter>
</defs>
<rect x="72" y="72" width="880" height="880" rx="200" fill="url(#bg)"/>
<g filter="url(#sh)">
  <circle cx="672" cy="352" r="150" fill="url(#knob)"/>
  <circle cx="672" cy="352" r="150" fill="none" stroke="#0B4FA8" stroke-width="6" opacity=".25"/>
  <circle cx="620" cy="300" r="17" fill="#7BA7DE"/>
  <circle cx="340" cy="300" r="74" fill="url(#knob)" opacity=".95"/>
  <circle cx="314" cy="274" r="10" fill="#7BA7DE"/>
</g>
<g fill="#FFFFFF" opacity="0.96">
  <rect x="268" y="512" width="150" height="150" rx="38"/>
  <rect x="446" y="512" width="150" height="150" rx="38"/>
  <rect x="624" y="512" width="150" height="150" rx="38"/>
  <rect x="268" y="690" width="150" height="150" rx="38"/>
  <rect x="446" y="690" width="150" height="150" rx="38"/>
  <rect x="624" y="690" width="150" height="150" rx="38"/>
</g>
</svg>'''


def menubar_svg():
    """Template icon: black and alpha only. macOS colors it for each mode."""
    return '''<svg width="44" height="44" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">
<g fill="#000000">
  <circle cx="30" cy="13" r="8.5"/>
  <circle cx="12.5" cy="13" r="4"/>
  <rect x="7"  y="26" width="9" height="9" rx="2.6"/>
  <rect x="18.5" y="26" width="9" height="9" rx="2.6"/>
  <rect x="30" y="26" width="9" height="9" rx="2.6"/>
</g>
</svg>'''


# ── menu-bar icon: 1x and 2x template ───────────────────────────────────
mb = menubar_svg().encode()
cairosvg.svg2png(bytestring=mb, write_to=f"{OUT}/MenubarIconTemplate.png",
                 output_width=22, output_height=22)
cairosvg.svg2png(bytestring=mb, write_to=f"{OUT}/MenubarIconTemplate@2x.png",
                 output_width=44, output_height=44)

# ── app icon: .iconset → .icns ──────────────────────────────────────────
ico = app_icon_svg().encode()
iconset = f"{OUT}/Makropad.iconset"
os.makedirs(iconset, exist_ok=True)
# Use only the names accepted by iconutil.
for size in (16, 32, 128, 256, 512):
    cairosvg.svg2png(bytestring=ico, write_to=f"{iconset}/icon_{size}x{size}.png",
                     output_width=size, output_height=size)
    cairosvg.svg2png(bytestring=ico, write_to=f"{iconset}/icon_{size}x{size}@2x.png",
                     output_width=size * 2, output_height=size * 2)

cairosvg.svg2png(bytestring=ico, write_to=f"{OUT}/icon_preview.png",
                 output_width=512, output_height=512)

# The .icns file is created only where iconutil is available (macOS); build.sh does this either way.
if subprocess.run(["which", "iconutil"], capture_output=True).returncode == 0:
    r = subprocess.run(["iconutil", "-c", "icns", iconset, "-o", f"{OUT}/Makropad.icns"],
                       capture_output=True, text=True)
    print(r.stderr.strip() or f"wrote {OUT}/Makropad.icns")
else:
    print("iconutil is not available here — build.sh creates the .icns file on macOS")

print("done:", sorted(os.listdir(OUT)))
