#!/usr/bin/env bash
# Regenerate type stubs for third-party packages that lack py.typed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source venv/bin/activate

PACKAGES=(apscheduler)

for pkg in "${PACKAGES[@]}"; do
  echo "Generating stubs for ${pkg}..."
  stubgen -p "$pkg" -o typings
done

python scripts/patch_stubs.py
echo "Done. Stubs written to typings/"
