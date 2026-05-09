#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Checking TYPO_API_BASE_URL is not in browser-side code ==="

# Check that TYPO_API_BASE_URL and NEXT_PUBLIC_TYPO are not in browser-side files
HITS=$(git grep -nE 'TYPO_API_BASE_URL|NEXT_PUBLIC_TYPO' \
    -- 'apps/web/components/**' 'apps/web/app/**' \
    ':!apps/web/app/api/**' 2>/dev/null | wc -l | tr -d ' ')

if [ "$HITS" -eq 0 ]; then
    echo "OK: TYPO_API_BASE_URL only appears in server-side route handlers."
    exit 0
else
    echo "FAIL: TYPO_API_BASE_URL or NEXT_PUBLIC_TYPO found in browser-side code ($HITS hits):"
    git grep -nE 'TYPO_API_BASE_URL|NEXT_PUBLIC_TYPO' \
        -- 'apps/web/components/**' 'apps/web/app/**' \
        ':!apps/web/app/api/**' 2>/dev/null || true
    exit 1
fi
