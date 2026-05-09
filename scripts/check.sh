#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="$HOME/.local/bin:$PATH"

echo "=== Lume Final Pre-Submit Check ==="
FAILS=0

# 1. Backend lint
echo "[1/7] Backend lint (ruff)..."
cd services/typo
uv run ruff check app/ tests/ && echo "  OK: ruff passed" || {
    echo "  FAIL: ruff found errors"
    FAILS=$((FAILS + 1))
}
cd ../..

# 2. Backend tests
echo "[2/7] Backend tests (pytest)..."
cd services/typo
uv run pytest -q tests/ && echo "  OK: pytest passed" || {
    echo "  FAIL: pytest failed"
    FAILS=$((FAILS + 1))
}
cd ../..

# 3. Frontend lint
echo "[3/7] Frontend lint..."
cd apps/web
pnpm run lint && echo "  OK: pnpm lint passed" || {
    echo "  FAIL: pnpm lint failed"
    FAILS=$((FAILS + 1))
}
cd ../..

# 4. Frontend build
echo "[4/7] Frontend build..."
cd apps/web
pnpm build && echo "  OK: pnpm build passed" || {
    echo "  FAIL: pnpm build failed"
    FAILS=$((FAILS + 1))
}
cd ../..

# 5. Notebook smoke (--output _executed.ipynb; delete on success)
echo "[5/7] Notebook execution smoke..."
cd services/typo
if uv run jupyter nbconvert --execute app/eda/eda.ipynb \
        --to notebook \
        --output _executed.ipynb \
        --ExecutePreprocessor.timeout=300 2>/dev/null; then
    rm -f _executed.ipynb
    echo "  OK: notebook executed and _executed.ipynb cleaned up"
else
    echo "  FAIL: notebook execution failed"
    rm -f _executed.ipynb
    FAILS=$((FAILS + 1))
fi
cd ../..

# 6. Secret guard
echo "[6/7] Secret guard..."
bash scripts/check_secrets.sh && echo "  OK: no secrets" || {
    FAILS=$((FAILS + 1))
}

# 7. Public-base guard
echo "[7/7] Public-base guard..."
bash scripts/check_no_public_base.sh && echo "  OK: TYPO_API_BASE_URL server-side only" || {
    FAILS=$((FAILS + 1))
}

echo ""
if [ "$FAILS" -eq 0 ]; then
    echo "=== ALL CHECKS PASSED ==="
    exit 0
else
    echo "=== FAILED: $FAILS check(s) failed ==="
    exit 1
fi

# NOTE: This script does NOT start pnpm start or any long-running server.
# For a11y audit, start prod server manually:
#   cd apps/web && pnpm build && pnpm start
# Then run: bash scripts/run_axe.sh
