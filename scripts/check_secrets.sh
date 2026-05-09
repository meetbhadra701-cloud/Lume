#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Checking for secrets in tracked files ==="

HITS=0

# Check for raw Anthropic API keys
if git grep -nE 'sk-ant' -- . ':!.env.example' 2>/dev/null | grep -v '.env.example'; then
    echo "ERROR: Found 'sk-ant' pattern in tracked files!"
    HITS=$((HITS + 1))
fi

# Check for hardcoded ANTHROPIC_API_KEY assignments
if git grep -nE 'ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*"[^"]' -- . ':!.env.example' 2>/dev/null; then
    echo "ERROR: Found hardcoded ANTHROPIC_API_KEY (double-quoted) in tracked files!"
    HITS=$((HITS + 1))
fi

if git grep -nE "ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*'[^']" -- . ':!.env.example' 2>/dev/null; then
    echo "ERROR: Found hardcoded ANTHROPIC_API_KEY (single-quoted) in tracked files!"
    HITS=$((HITS + 1))
fi

if [ "$HITS" -eq 0 ]; then
    echo "OK: No secrets found in tracked files."
    exit 0
else
    echo "FAIL: $HITS secret pattern(s) found."
    exit 1
fi
