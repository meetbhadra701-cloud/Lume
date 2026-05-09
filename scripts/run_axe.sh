#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Running axe-core accessibility audit ==="
echo "Ensure pnpm start is running on http://localhost:3000 before running this script."
echo ""

mkdir -p docs/a11y

pnpm dlx @axe-core/cli http://localhost:3000 --save docs/a11y/axe.json \
    || pnpm dlx @axe-core/cli http://localhost:3000 | tee docs/a11y/axe.txt

echo ""
echo "=== axe audit complete. Reports in docs/a11y/ ==="
