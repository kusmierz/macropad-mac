#!/bin/bash
# Build Makropad.app and Makropad.dmg — standalone, with embedded Python.
#
#   ./build.sh
#
# Output: dist/Makropad.dmg
set -euo pipefail
cd "$(dirname "$0")"

APP="Makropad"
VENV=".venv"
PY="$VENV/bin/python"

echo "▸ Dependencies"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r requirements.txt pyinstaller rumps

echo "▸ Icons"
if [ ! -f build_assets/Makropad.icns ]; then
  if "$PY" -c "import cairosvg" 2>/dev/null; then
    (cd design && "../$PY" render_icons.py >/dev/null)
  fi
  if [ -d build_assets/Makropad.iconset ]; then
    rm -f build_assets/Makropad.iconset/icon_64x64*.png \
          build_assets/Makropad.iconset/icon_1024x1024.png
    iconutil -c icns build_assets/Makropad.iconset -o build_assets/Makropad.icns
  else
    echo "  (no icons — building without them. Run design/render_icons.py with cairosvg installed.)"
  fi
fi

echo "▸ Cleaning"
rm -rf build dist "$APP.spec"

echo "▸ PyInstaller"
ICON_ARG=()
[ -f build_assets/Makropad.icns ] && ICON_ARG=(--icon build_assets/Makropad.icns)
MB_ARG=()
[ -f build_assets/MenubarIconTemplate.png ] && \
  MB_ARG=(--add-data "build_assets/MenubarIconTemplate.png:." \
          --add-data "build_assets/MenubarIconTemplate@2x.png:.")

"$VENV/bin/pyinstaller" \
  --name "$APP" \
  --windowed \
  --noconfirm \
  --clean \
  --log-level WARN \
  "${ICON_ARG[@]}" \
  "${MB_ARG[@]}" \
  --add-data "ui.html:." \
  --hidden-import paths \
  --hidden-import access \
  --hidden-import keys \
  --hidden-import store \
  --add-data "profiles.example.yaml:." \
  --osx-bundle-identifier no.macropad.app \
  --hidden-import hid \
  --hidden-import yaml \
  --hidden-import rumps \
  --hidden-import Quartz \
  --hidden-import AppKit \
  --collect-submodules objc \
  --collect-all rumps \
  menubar.py

PLIST="dist/$APP.app/Contents/Info.plist"
echo "▸ Info.plist"
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 1.0" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string 'MIT'" "$PLIST" 2>/dev/null || true

echo "▸ Signing"
# A real Developer ID lets macOS recognize the app across builds. Accessibility is
# tied to bundle ID + team ID, not a hash that changes every time. Without it
# (ad-hoc), permission must be enabled again for every build.
IDENTITY=$(security find-identity -v -p codesigning 2>/dev/null \
  | grep "Developer ID Application" | head -1 | sed 's/.*"\(.*\)"/\1/')
if [ -z "$IDENTITY" ]; then
  IDENTITY="-"
  echo "  No Developer ID found — signing ad-hoc."
  echo "  Note: Accessibility must be enabled again after every build."
else
  echo "  $IDENTITY"
fi
codesign --force --deep --sign "$IDENTITY" --timestamp=none "dist/$APP.app" 2>&1 \
  | grep -v "replacing existing signature" || true
codesign --verify --strict "dist/$APP.app" && echo "  signature OK"

echo "▸ DMG"
STAGE=$(mktemp -d)
cp -R "dist/$APP.app" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cat > "$STAGE/Read Me.txt" <<'EOF'
Makropad — configurator for the XZKJ 12-key/4-knob macropad

1. Drag Makropad to Applications.
2. Start it. The first time: right-click → Open (the app is not signed by Apple).
3. Grant Accessibility permission when prompted — the app needs to read the pad
   to translate its key presses.
4. Choose “Prepare pad” in the menu bar. Once is all it takes.

https://github.com/GaimsDevSoftware/macropad-mac
EOF
rm -f "dist/$APP.dmg"
hdiutil create -volname "$APP" -srcfolder "$STAGE" -ov -format UDZO \
  -quiet "dist/$APP.dmg"
rm -rf "$STAGE"

echo
echo "✓ dist/$APP.app"
echo "✓ dist/$APP.dmg   ($(du -h "dist/$APP.dmg" | cut -f1))"
