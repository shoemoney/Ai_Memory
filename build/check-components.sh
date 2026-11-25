#!/usr/bin/env bash
# Render every snippet in COMPONENTS.md and fail if any breaks the rules. Add --keep to keep the PDF.
set -euo pipefail
cd "$(dirname "$0")"
exec python3 check-components.py "$@"
