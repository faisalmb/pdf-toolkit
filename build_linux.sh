#!/usr/bin/env bash
# Builds the Linux app folder and a .tar.gz with an install script.
# Usage: ./build_linux.sh   (needs Python 3.10+; run it on Linux)
set -euo pipefail
cd "$(dirname "$0")"

VERSION="11.0.0"
PY="${PYTHON:-python3}"

echo "[1/4] Installing required packages..."
"$PY" -m pip install -r requirements.txt pyinstaller

echo "[2/4] Cleaning previous build folders..."
rm -rf build dist

echo "[3/4] Building dist/PDFMerger ..."
"$PY" -m PyInstaller --noconfirm PDFMerger.spec

echo "[4/4] Packaging the .tar.gz ..."
cp app_icon.png dist/PDFMerger/
cp packaging/linux/pdfmerger.desktop packaging/linux/install.sh packaging/linux/uninstall.sh dist/PDFMerger/
chmod +x dist/PDFMerger/install.sh dist/PDFMerger/uninstall.sh
mkdir -p installer_output
TARBALL="installer_output/PDFMerger-${VERSION}-linux-$(uname -m).tar.gz"
tar -C dist -czf "$TARBALL" PDFMerger

echo
echo "Done!"
echo "  App:     dist/PDFMerger/PDFMerger"
echo "  Package: $TARBALL  (extract, then run ./install.sh)"
