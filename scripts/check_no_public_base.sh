#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Checking TYPO_API_BASE_URL is not in browser-side code ==="

# Check that TYPO_API_BASE_URL and NEXT_PUBLIC_TYPO are not in browser-side files
# git grep exits 1 when no matches found — use || true so pipefail/set -e don't abort the check
HITS=$(git grep -nE 'TYPO_API_BASE_URL|NEXT_PUBLIC_TYPO' \
    -- 'apps/web/components/**' 'apps/web/app/**' \
    ':!apps/web/app/api/**' 2>/dev/null || true)

if [ -z "$HITS" ]; then
    echo "OK: TYPO_API_BASE_URL only appears in server-side route handlers."
    exit 0
else
    COUNT=$(echo "$HITS" | wc -l | tr -d ' ')
    echo "FAIL: TYPO_API_BASE_URL or NEXT_PUBLIC_TYPO found in browser-side code ($COUNT hits):"
    echo "$HITS"
    exit 1
fi
