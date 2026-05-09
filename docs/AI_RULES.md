# AI Rules for Lume

This file governs all AI-assisted work on this codebase. It is the authoritative source; any generated `AGENTS.md` or `CLAUDE.md` files in subdirectories are deleted.

## §1 Scope

- AI assists with coding, copywriting, and analysis only
- **No AI in the live render path** — Anthropic API is used only in the optional EDA notebook stat-reviewer cell
- The stat-reviewer cell sends only regression diagnostics (numbers and summaries), never raw user text

## §2 Blocked Protocol (severity-gated)

If Claude Code is stuck >20 minutes, emit:

```
<blocked>
Step: PLAN §X.Y
Failing command: {exact command}
Stderr/stack: {paste}
Suspected cause: {hypothesis}
Smallest workaround: {proposal}
Severity: {core_demo_breaking | nice_to_have | destructive_or_security}
</blocked>
```

### Severity Actions

| Severity | Action |
|---|---|
| `nice_to_have` | Claude Code may apply the smallest safe workaround automatically; log in `CHANGELOG_RULES.md` |
| `core_demo_breaking` | Stop and wait (paste→render→rate loop down, frontend build broken, DB schema mismatch, notebook can't execute) |
| `destructive_or_security` | Always stop and wait — no auto-workaround (potential rm-rf, leaked secret, force-push, API key exposure) |

Every auto-applied workaround logged in `docs/CHANGELOG_RULES.md`.

## §2.1 Anthropic API Usage

- Model: from `ANTHROPIC_MODEL` env var (empty = skip)
- Default behavior: skip (never hardcode a model name as default)
- Only for EDA notebook stat-reviewer cell
- No raw text is ever sent — only diagnostic numbers and summaries

## §3 Conservative Language Rules

See `docs/PRD.md §B.1.7`.

## §4 Hard Lines (never cross)

1. Never claim a p-value you didn't compute
2. Never advance past the current PLAN.md step (exception: blocked-summary protocol with severity gating)
3. Never break the WCAG AA accessibility floor
4. Never put any AI in the live render path

## §5 Secret Hygiene

- `scripts/check_secrets.sh` uses `git grep` (tracked files only)
- Patterns checked: `sk-ant`, `ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*"`, `ANTHROPIC_API_KEY[[:space:]]*=[[:space:]]*'`
- `.env` is gitignored; `.env.example` contains only empty placeholders
