# Lume — Pitch Deck Outline (12 slides)

| Slide | Title | Visual Asset | Speaker Note |
|---|---|---|---|
| 1 | Lume: Reading Made Personal | Logo + hero screenshot of reader UI | "1 in 6 people has dyslexia. The fonts and spacing in most apps were never designed for them. Lume changes that — and learns what works for you." |
| 2 | The Problem | IDA statistic + stock reading image | "15–20% of the population shows dyslexia symptoms. Yet most text is presented in one rigid format — no adaptation, no personalization." |
| 3 | Research-Informed Adaptations | Side-by-side: default vs. Lume-tuned text | "7 typographic adaptations: letter spacing, word spacing, hyphenation, frequency-aware emphasis, warm color overlay, chunked reading, and OpenDyslexic font. Each is togglable; all are WCAG-AA compliant." |
| 4 | The Learning Loop | Flow diagram: paste → render → read → comprehend → reward → bandit | "Lume measures your WPM and comprehension after each passage. A Thompson-sampling bandit explores 16 adaptation configurations. A per-user Ridge regression model — trained on your data — takes over at 30+ events." |
| 5 | The Tech Stack | Architecture diagram | "FastAPI backend, Next.js frontend, SQLite, scikit-learn Ridge, scipy/statsmodels, pyphen for hyphenation. 8 custom data structures — trie, binary search, heap, DFS, DP, recursion, sliding window, hashmap." |
| 6 | Live Demo | (screen share) | "Watch me paste a Gutenberg excerpt, see Lume's recommendation, read it, answer 3 comprehension questions, and see the reward update the bandit's posteriors." |
| 7 | Hypothesis 1: Spacing Improves WPM | `docs/figures/h1_spacing_ci.png` | "Paired t-test on synthetic data: letter spacing produces a statistically significant WPM lift [synthetic, N=200]. CI shown — we're honest about the sample size." |
| 8 | Hypothesis 2: Complexity Predicts Comprehension | `docs/figures/h2_residuals.png` | "OLS regression: Flesch-Kincaid + syllable density explain R²=[X] of comprehension variance [synthetic, N=200]. 5-fold CV confirms generalization." |
| 9 | Hypothesis 3: User × Adaptation Interaction | `docs/figures/h3_interaction.png` | "ANOVA on synthetic 3-user data: significant interaction effect — different users benefit from different adaptations [H3 synthetic simulation, N=200]. This is why personalization matters." |
| 10 | Real-User Results | `docs/figures/cv_pred_actual.png` + `[real-user, N=10]` figure | "10 passages, 5-arm balanced subset, 1 real user. WPM trend and comprehension scores shown. Small N — we say so explicitly. The bandit is learning." |
| 11 | Accessibility | Lighthouse + axe screenshots from `docs/a11y/` | "Lighthouse accessibility score ≥95. axe-core: 0 violations. Keyboard-navigable. WCAG 2.2 AA verified for emphasis and overlay colors." |
| 12 | Try It | GitHub URL + run commands | "Two terminal commands. Runs entirely on localhost — your text never leaves your machine. Clone it, paste something you're reading today." |

## Speaker Notes: Full 60-Second Script

"[1] Lume — reading made personal. [2] 1 in 6 people has dyslexia; most text apps weren't designed for them. [3] Lume applies 7 research-informed typographic adaptations and learns which combination works best for you. [4] The loop: paste text, read it, answer comprehension questions. A bandit explores adaptation configs; a Ridge model takes over once you have 30 readings. [5] Built with FastAPI, Next.js, and 8 custom data structures. [6] [demo] [7] Paired t-test shows spacing improves WPM — on synthetic data, sample size disclosed. [8] Flesch-Kincaid predicts comprehension at R²=X. [9] User-by-adaptation interaction — personalization is real. [10] Real-user data: 10 passages, honest small-N labeling. [11] Fully keyboard-accessible, WCAG AA, Lighthouse 95+. [12] Two terminal commands. Try it."
