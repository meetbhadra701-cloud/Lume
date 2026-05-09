# Lume — Personalized Reading Accessibility

> Research-informed typographic adaptations for adults with dyslexia, powered by a Thompson-sampling bandit and per-user Ridge regression.

As many as 15–20% of the population shows symptoms of dyslexia (International Dyslexia Association, dyslexiaida.org/dyslexia-basics). Lume lets you paste any text, renders it with 7 research-informed typographic adaptations, measures your reading speed (WPM) and comprehension, and learns your optimal configuration.

## Quick Start (localhost only)

```bash
# 1. Copy and populate env
cp .env.example .env
# Edit .env: set LUME_HASH_SALT=<any random string>

# 2. Initialize the database
python scripts/reset_db.py

# 3. Start backend (terminal 1)
cd services/typo
uv run uvicorn app.main:app --reload --port 8000

# 4. Start frontend (terminal 2)
cd apps/web
cp ../../.env.example .env.local
# Edit .env.local: set TYPO_API_BASE_URL=http://localhost:8000
pnpm dev

# 5. Open browser
open http://localhost:3000
# Click "Load demo passage" and start reading
```

## Port Conflict Troubleshooting

```bash
lsof -i :3000   # find frontend conflict
lsof -i :8000   # find backend conflict

# Frontend fallback
PORT=3001 pnpm dev

# Backend fallback (then update TYPO_API_BASE_URL in .env.local)
cd services/typo && uv run uvicorn app.main:app --port 8001
```

## Tech Stack

- **Frontend:** Next.js (see `docs/ARCHITECTURE.md` for scaffolded version), TypeScript, Tailwind CSS, shadcn/ui
- **Backend:** FastAPI, Python 3.11, SQLite, scikit-learn Ridge, scipy, statsmodels
- **Package managers:** pnpm (frontend), uv (backend)

## Adaptations

| # | Toggle | Effect |
|---|---|---|
| 1 | Letter spacing | +0.04em between letters |
| 2 | Word spacing | +0.16em between words |
| 3 | Hyphenation | Knuth-Plass-inspired DP break selection |
| 4 | Reading emphasis | Frequency-aware word emphasis |
| 5 | Warm color overlay | WCAG-AA-tested parchment background |
| 6 | Chunked reading | ~80-word chunks with pagination |
| 7 | OpenDyslexic font | Locally-bundled SIL-OFL font |

## Prize Tracks

| Track | Operationalized |
|---|---|
| Accessibility (#5) | ✅ Lighthouse ≥95, axe-core 0 violations, keyboard nav |
| EDA + Statistics (#7) | ✅ 3 hypotheses, statsmodels OLS, paired t-test, ANOVA |
| Technical Depth (#2) | ✅ 8 DSAs, Ridge regression, Thompson sampling bandit |
| Social Good (#1) | Submitted only |
| Creative (#3) | Submitted only |
| AI/ML (#8) | Submitted only |
| Design (#9) | Submitted only |

## Repo Layout

```
Lume/
├── apps/web/               # Next.js frontend
├── services/typo/          # FastAPI backend
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── adaptations/    # Spacing, hyphenation, chunking, emphasis
│   │   ├── data_structures/ # Trie, freq index, heap
│   │   ├── ml/             # Bandit, Ridge, recommender, reward
│   │   ├── eda/            # Notebook + corpus fetcher
│   │   └── store/          # DB + paths
│   ├── schema.sql
│   └── pyproject.toml
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── PLAN.md
│   ├── DSA_INVENTORY.md
│   ├── references.md
│   ├── data_sources.md
│   ├── figures/            # EDA notebook output figures
│   └── a11y/               # Lighthouse + axe reports
├── scripts/
│   ├── reset_db.py
│   ├── check.sh
│   ├── check_fast.sh
│   ├── check_secrets.sh
│   └── check_no_public_base.sh
├── .env.example
└── pnpm-workspace.yaml
```

## Privacy

Pasted text and reading events are stored locally in SQLite for the demo. **No pasted text is sent to any third-party AI API.** Internal text identifiers use HMAC-SHA-256 with a per-machine salt — they are not claimed to be one-way against brute-force dictionary attacks. The optional Anthropic API call is offline-only and reviews regression diagnostics (numbers + summaries) from the EDA notebook, never raw text. Run `python scripts/reset_db.py` to delete all local data.

## References

See [`docs/references.md`](docs/references.md) for citations.
