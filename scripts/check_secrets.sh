#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Checking for secrets in tracked files ==="

HITS=0

# Check for raw Anthropic API keys
# Exclude .env.example, this script itself, and docs that describe the pattern
if git grep -nE 'sk-ant' -- . ':!.env.example' ':!scripts/check_secrets.sh' ':!docs/AI_RULES.md' ':!docs/PLAN.md' 2>/dev/null; then
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
