#!/usr/bin/env bash
# Removes PDF Merger installed by install.sh.
set -euo pipefail
rm -rf "$HOME/.local/share/pdfmerger"
rm -f "$HOME/.local/share/applications/pdfmerger.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" || true
echo "PDF Merger was removed."
