# Lume — Personalized Reading Accessibility

> Research-informed typographic adaptations for adults with dyslexia, powered by a Thompson-sampling bandit and per-user Ridge regression.

As many as 15–20% of the population shows symptoms of dyslexia (International Dyslexia Association, dyslexiaida.org/dyslexia-basics). Lume lets you paste any text, renders it with 7 research-informed typographic adaptations, measures your reading speed (WPM) and comprehension, and learns your optimal configuration.

---

## 🎬 Demo

**[▶ Watch the Lume Demo Video](https://youtu.be/YOUR_VIDEO_ID)**  
**[📊 View the Pitch Deck](https://gamma.app/docs/Lume-Illuminating-Personalized-Literacy-fs4w8yo18xc3wmr)**  
**[💻 GitHub Repository](https://github.com/meetbhadra701-cloud/Lume)**

---

## 🏆 Hackathon Tracks

Lume is submitted for **three tracks**:

### ♿ Track 1 — Accessibility
**Lume is the product.** It redefines WCAG 3.0 accessibility by treating it as a dynamic, machine-learned state rather than a static preset. Every user gets a continuously personalized typographic configuration — not a one-size-fits-all toggle.

| Signal | Detail |
|---|---|
| Lighthouse score | 100 / 100 (automated) |
| axe-core violations | 0 |
| Keyboard navigation | Full — every action reachable via Tab / Enter / Escape / ←→ |
| WCAG AA compliance | Color contrast, focus rings, ARIA roles, `role="dialog"` tour |
| WCAG 3.0 dynamic personalization | Per-user Ridge model auto-applies optimal config every session |
| Onboarding friction | 60 seconds to first insight; first-time tour built in |
| Font support | OpenDyslexic (SIL-OFL, locally bundled — no CDN dependency) |

### 📊 Track 2 — EDA (Exploratory Data Analysis)
We use rigorous statistical reasoning to **mathematically prove comprehension growth** and validate the convergence point.

| Metric | What it measures |
|---|---|
| **MSE (Mean Squared Error)** | Ridge regression training loss; minimized per user across 47-dim feature space |
| **R² tracking** | Model fit quality logged per user; EDA notebook shows R² improves with more sessions |
| **Precision** | Stagnation detector: convergence fires only when σ(reward) ≤ 0.08 over 3 sessions, preventing false positives |
| **Paired t-test** | Hypothesis 1 — letter spacing significantly improves WPM (p < 0.05) |
| **One-way ANOVA** | Hypothesis 2 — arm group differences in comprehension score |
| **OLS regression** | Statsmodels OLS validates feature importance in the 47-dim vector |

All EDA code and figures live in `services/typo/app/eda/` and `docs/figures/`.

### ⚙️ Track 3 — Most Technically Challenging Hack
A full-stack ML system with production-grade architecture:

- **16-arm Thompson Sampling Contextual Bandit** with continuous Beta(α,β) posterior updates — each arm is a distinct typographic configuration
- **Per-user Ridge Regression** (47-dim feature vector: text complexity, syllable density, Flesch-Kincaid, arm config booleans) gated at ≥30 events
- **Blended reward signal**: `R = 0.7 × normalize_wpm(WPM) + 0.3 × blend_comprehension(self_rating, MCQ)` — fuses two independent comprehension signals
- **Stagnation detection**: convergence when `mean(reward) ≥ 0.65 AND std(reward) ≤ 0.08` over last 3 sessions → auto-locks Best Fit config
- **8 custom DSAs**: Trie (prefix lookup), FreqIndex (heap-backed), Knuth-Plass hyphenator (DP), and 5 more
- **Multi-stack**: Next.js 16 + React 19 frontend · FastAPI + Python 3.11 backend · SQLite · scikit-learn · scipy · statsmodels
- **145 passing pytest tests** · CI pipeline: ruff + lint + pnpm build + notebook smoke + secret guard + public-base guard

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

## Submitted Tracks

| # | Track | Status |
|---|---|---|
| 1 | ♿ **Accessibility** | ✅ Primary — Lume is the product |
| 2 | 📊 **EDA / Exploratory Data Analysis** | ✅ Primary — MSE, R², precision, OLS, ANOVA |
| 3 | ⚙️ **Most Technically Challenging Hack** | ✅ Primary — 16-arm bandit + Ridge + 145 tests |

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
