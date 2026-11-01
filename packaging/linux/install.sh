#!/usr/bin/env bash
# Installs PDF Merger for the current user (no sudo needed).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/pdfmerger"
APPS="$HOME/.local/share/applications"

rm -rf "$DEST"
mkdir -p "$DEST" "$APPS"
cp -R "$SRC"/. "$DEST"/
sed "s|@INSTALL_DIR@|$DEST|g" "$SRC/pdfmerger.desktop" > "$APPS/pdfmerger.desktop"
chmod +x "$DEST/PDFMerger"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" || true

echo "Installed to $DEST"
echo "PDF Merger is now in your applications menu."
