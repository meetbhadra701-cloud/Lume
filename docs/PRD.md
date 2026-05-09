# Lume — Product Requirements Document

## §B.1 Overview

Lume is a personalized reading-accessibility web app for adults with dyslexia. The core loop:

1. User pastes text (or loads a seed passage)
2. Backend renders the text with research-informed typographic adaptations
3. User reads, then answers comprehension questions
4. System logs WPM + comprehension → computes reward
5. Thompson-sampling bandit + per-user Ridge regression converge on each user's optimal adaptation config

## §B.1.1 Users

Primary: adults with dyslexia seeking faster, more comfortable reading.
Secondary: reading researchers, hackathon judges.

## §B.1.2 Core Value

Show that personalized typography — tuned per user via ML — measurably improves reading speed and comprehension.

## §B.1.3 Hypotheses

**H1:** Increased letter spacing improves WPM for dyslexic readers (paired t-test on synthetic data).

**H2:** Text complexity (Flesch-Kincaid + syllable density) predicts comprehension score (OLS regression).

**H3:** User × adaptation interaction produces heterogeneous treatment effects — some users benefit from chunking, others from hyphenation (ANOVA on synthetic multi-user data).

## §B.1.4 Adaptations (7)

See ARCHITECTURE.md §B.2.1.

## §B.1.5 Scope IN

- Paste text → render with adaptations → measure WPM + comprehension
- Thompson-sampling bandit over 16 explicit arms
- Per-user Ridge regression with 47-dim feature vector (n ≥ 30 gate)
- 3 EDA hypotheses tested (statsmodels OLS, scipy paired t-test, ANOVA)
- WCAG 2.2 AA accessibility compliance
- Lexend default font, OpenDyslexic optional (locally bundled)
- SQLite data storage (local only)
- Real-user data collection (5-arm balanced subset, N=10)

## §B.1.6 Scope OUT

- Backend deployment beyond localhost demo
- Multi-user authentication / accounts
- Mobile responsive layout (Chrome desktop only)
- Safari / Firefox compatibility
- Non-English language detection or adaptation
- Durable render cache (process-local in-memory only)
- Persistent bandit posteriors (rebuilt from events on startup)
- PDF / EPUB ingestion
- Real-time collaborative reading
- Alembic migrations (schema reset only)

## §B.1.7 Conservative Language

| Don't say | Say |
|---|---|
| "Knuth-Plass" | "Knuth-Plass-inspired DP" |
| "evidence-based typographic adaptations" | "research-informed typographic adaptations" |
| "difficult words" (UI) | "Reading emphasis" / "frequency-aware emphasis" |
| "Irlen filter" | "warm color overlay" |
| "measures lift to 4 decimal places" | "reports lift to 1 decimal point" |
| "non-reversible hash" | "HMAC-keyed identifier; raw text never leaves your machine" |

## §B.1.8 Hypotheses (EDA)

See §B.1.3 above. All plots labeled `[synthetic, N=200]` or `[real-user, N=10]`. Strict `data_source` filter. H3 labeled `[H3 synthetic simulation, N=200, 3+ synthetic users]` — real-user N=10 cannot support user×adaptation ANOVA.
