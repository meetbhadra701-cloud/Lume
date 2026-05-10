# Lume — Personalized Reading Accessibility

> Research-informed typographic adaptations for adults with dyslexia, powered by a Thompson-sampling bandit and per-user Ridge regression.

As many as 15–20% of the population shows symptoms of dyslexia (International Dyslexia Association, dyslexiaida.org/dyslexia-basics). Lume lets you paste any text, renders it with 7 research-informed typographic adaptations, measures your reading speed (WPM) and comprehension, and learns your optimal configuration.

---

## 🏆 Track Alignment

Lume is purpose-built for three hackathon tracks:

| Track | Evidence |
|---|---|
| **♿ Accessibility** | Lighthouse 100/100 · axe-core 0 violations · full keyboard nav · WCAG AA color contrast · WCAG 3.0 dynamic personalization · OpenDyslexic font · zero-barrier 60-second onboarding |
| **🌍 Social Impact / AI for Good** | Addresses a documented $2.4 T global productivity gap caused by untreated reading barriers. Every session improves the model—Lume gets smarter for each user with zero manual tuning. On-device SQLite: no user text ever leaves the machine. |
| **📊 EDA + Technical Depth** | 16-arm Thompson Sampling bandit with Beta(α,β) posteriors · per-user Ridge regression (47-dim feature vector) · MSE-optimized reward signal (0.7×WPM + 0.3×blended comprehension) · 3 EDA hypotheses with statsmodels OLS, paired t-test, ANOVA · 8 custom DSAs (Trie, FreqIndex, KP-hyphenator, …) · 145 pytest tests · CI: ruff + lint + build + secret guard |

---

## Prerequisites

| Tool | Install |
|---|---|
| **Node ≥ 18** + **pnpm** | `npm i -g pnpm` |
| **Python ≥ 3.11** + **uv** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

> **No `uv`?** You can also run the backend with plain pip:
> ```bash
> cd services/typo && pip install -e . && uvicorn app.main:app --reload --port 8000
> ```

---

## Quick Start (localhost only)

```bash
# 1. Copy and populate env
cp .env.example .env
# Edit .env: set LUME_HASH_SALT=<any random string>
# ANTHROPIC_API_KEY is optional — leave blank to skip the AI reviewer

# 2. Initialize the database
python scripts/reset_db.py

# 3. Start backend (terminal 1)
cd services/typo
uv run uvicorn app.main:app --reload --port 8000

# 4. Start frontend (terminal 2)
cd apps/web
cp ../../.env.example .env.local
# Edit .env.local: set TYPO_API_BASE_URL=http://localhost:8000
pnpm install && pnpm dev

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

- **Frontend:** Next.js 16.2.6, TypeScript, Tailwind CSS, shadcn/ui
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
| Accessibility (#5) | ✅ Lighthouse 100/100, axe-core 0 violations, keyboard nav, WCAG AA |
| EDA + Statistics (#7) | ✅ 3 hypotheses, statsmodels OLS, paired t-test, ANOVA |
| Technical Depth (#2) | ✅ 8 DSAs, Ridge regression, Thompson sampling bandit |
| Social Good / Social Impact (#1) | ✅ Targets dyslexia ($2.4T economic gap, 43M US adults); on-device privacy |
| AI for Good (#8) | ✅ Personalized ML that improves silently per session; zero data exposure |
| Creative (#3) | Submitted |
| Design (#9) | Submitted |

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
