#!/usr/bin/env bash
# Builds PDFMerger.app and a .dmg on macOS.
# Usage: ./build_mac.sh   (needs Python 3.10+; run it on a Mac)
set -euo pipefail
cd "$(dirname "$0")"

VERSION="11.0.0"
PY="${PYTHON:-python3}"

echo "[1/4] Installing required packages..."
"$PY" -m pip install -r requirements.txt pyinstaller pillow

echo "[2/4] Cleaning previous build folders..."
rm -rf build dist

echo "[3/4] Building dist/PDFMerger.app ..."
"$PY" -m PyInstaller --noconfirm PDFMerger.spec

echo "[4/4] Building the .dmg ..."
mkdir -p installer_output
DMG="installer_output/PDFMerger-${VERSION}-macOS-$(uname -m).dmg"
STAGE="$(mktemp -d)"
cp -R dist/PDFMerger.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "PDF Merger" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"

echo
echo "Done!"
echo "  App: dist/PDFMerger.app"
echo "  DMG: $DMG"
