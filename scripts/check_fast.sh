#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"

echo "=== Lume Fast Check ==="

# 1. Backend lint
echo "[1/4] Backend lint (ruff)..."
cd services/typo
uv run ruff check app/ tests/ 2>/dev/null && echo "  OK: ruff passed" || {
    echo "  WARN: ruff found issues (non-blocking in fast check)"
}
cd ../..

# 2. Backend tests
echo "[2/4] Backend tests (pytest)..."
cd services/typo
uv run pytest -q tests/ && echo "  OK: pytest passed"
cd ../..

# 3. Frontend lint
echo "[3/4] Frontend lint..."
cd apps/web
if pnpm run lint --if-present 2>/dev/null; then
    echo "  OK: pnpm lint passed"
else
    echo "  WARN: pnpm lint skipped or had issues"
fi
cd ../..

# 4. Frontend build smoke
echo "[4/4] Frontend build..."
cd apps/web
pnpm build && echo "  OK: pnpm build passed"
cd ../..

echo ""
echo "=== Fast check complete ==="
