#!/usr/bin/env bash
# bundle-a2ui.sh — Ensures a2ui assets directory exists.
# The a2ui consists of a single index.html; no bundling is needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
A2UI_SRC="$ROOT/src/canvas-host/a2ui"

if [[ -d "$A2UI_SRC" ]]; then
  echo "[a2ui] Assets found at $A2UI_SRC"
else
  echo "[a2ui] No a2ui assets found — skipping"
fi
