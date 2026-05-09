# Lume — Execution Plan (rev. 4)

## Phase Map

| Hours | Phase | Output | Gate |
|---|---|---|---|
| 0–2 | 0. Setup + stub loop | Both servers up; schemas; stub loop; DB | Hour 3 early-cut trigger |
| 2–10 | 1. Algorithms | 8 DSAs + tests | — |
| 10–16 | 2. ML core | Bandit + Ridge + recommender | Hour 12 API gate |
| 16–22 | 3. EDA ⭐ | 3 hypotheses; figures; notebook | DO NOT CUT |
| 22–32 | 4. Frontend + a11y | End-to-end; Lighthouse ≥95 | Hour 24 demo gate |
| 32–40 | 5. Pitch + real data | Deck; 10 passages; README | — |
| 40–46 | Buffer | Bug fixes; re-record demo | — |
| 46–48 | Submit | — | — |

## Scope-Freeze Gates

| Gate | Question | If NO |
|---|---|---|
| Hour 3 | Phase 0.6 stub loop done? | Cut OpenDyslexic + stat-reviewer + Figma |
| Hour 12 | `/render` + `/rate` callable e2e, events writing? | Freeze ML/DSA; fix loop |
| Hour 24 | paste→render→read→comprehension working? | Freeze polish; ship loop with stubs |

## Pre-Decided Cut Order

1. Cut #1: Phase 4.6 stats page → inline post-reading panel + deck screenshots
2. Cut #2: Phase 4.8 Figma multi-screen → desktop reader only
3. Cut #3: Phase 3.7 stat-reviewer cell
4. Cut #4: Phase 5.6 backup video (only if live demo cleanly practiced 3×)
5. Last resort: Phase 2.2 Thompson bandit → random sampler

## Phase 0 Progress

- [ ] 0.1 Bootstrap scaffold
- [ ] 0.2 Next.js frontend + shadcn stub components
- [ ] 0.3 uv backend init + deps + main.py + paths.py
- [ ] 0.4 SQLite schema + db.py + reset_db.py + test_db.py
- [ ] 0.5 schemas.py + api_examples + test_schemas.py
- [ ] 0.6 Stub loop (/render + /rate + frontend reader)
- [ ] 0.7 EDA dep smoke (deferred; run if time permits)
- [ ] 0.8 Commit + tag v0.0-setup then v0.1-stub-loop

## Phase 1 Progress

- [ ] 1.1 Trie (O(L))
- [ ] 1.2 Binary search freq_index (O(log V))
- [ ] 1.3 Syllable DFS (O(S))
- [ ] 1.4 Knuth-Plass-inspired DP hyphenation (O(L²))
- [ ] 1.5 Adaptation heap (O(log k))
- [ ] 1.6 Spacing, color, chunking (recursion in chunking)
- [ ] 1.7 Highlight / emphasis (trie + freq_index → flag)

## Phase 2 Progress

- [ ] 2.0 reward.py + arms.py + real_user_arms.py + mode_configs.py
- [ ] 2.1 features.py (47-dim)
- [ ] 2.2 bandit.py (Thompson, continuous Beta, rebuild from events)
- [ ] 2.3 model.py (per-user Ridge, n≥30 gate)
- [ ] 2.4 recommender.py
- [ ] 2.5 Wire /render → recommender; /rate → persist

## Phase 3 Progress

- [ ] 3.1 fetch_corpus.py + sample_corpus.jsonl fallback
- [ ] 3.2 Notebook scaffold
- [ ] 3.3 H1 paired t-test
- [ ] 3.4 H2 OLS
- [ ] 3.5 H3 ANOVA (synthetic only)
- [ ] 3.6 5-fold CV
- [ ] 3.7 Stat-reviewer cell (Cut #3 candidate)

## Phase 4 Progress

- [ ] 4.1 Reader page (paste + demo passage button + text_id)
- [ ] 4.2 Token rendering
- [ ] 4.3 WPM clock
- [ ] 4.4 Comprehension component
- [ ] 4.5 Adaptation toggles (7)
- [ ] 4.6 Inline post-reading panel (Cut #1 fallback from stats page)
- [ ] 4.7 A11y audit (Lighthouse + axe — DO NOT CUT)
- [ ] 4.8 Figma (Cut #2 candidate)

## Phase 5 Progress

- [ ] 5.1 Real-user data collection (LUME_COLLECT_MODE=real_user, 10 passages, 5-arm subset)
- [ ] 5.2 Re-run notebook --inplace
- [ ] 5.3 deck_outline.md + 12-slide deck
- [ ] 5.4 README final
- [ ] 5.5 Practice pitch (×3)
- [ ] 5.6 90s demo video (Cut #4 candidate)
