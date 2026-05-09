# Data Sources

## Corpus: Project Gutenberg

Source: Project Gutenberg (https://www.gutenberg.org/) — public domain works.

Passage IDs used in `apps/web/lib/seed_passages.ts`:
- These are short excerpts (<10,000 chars) from public domain texts
- Exact titles and Gutenberg IDs documented at fetch time in `services/typo/app/eda/fetch_corpus.py`

## Synthetic Data Generator

File: `services/typo/app/eda/synthesize.py`

Random seed: `42` (fixed for reproducibility)

The generator creates **paired** observations: same paragraph + user under both default and letter-spacing conditions, enabling a valid paired t-test (H1). Output format: `demo_seed_events.jsonl` with `data_source='synthetic'`.

Generator parameters:
- N = 200 synthetic events
- 3+ simulated users (for H3 ANOVA)
- WPM sampled from N(μ, σ) per adaptation condition
- Comprehension sampled from Beta(α, β) per complexity bucket

## Sample Corpus Fallback

File: `services/typo/app/eda/sample_corpus.jsonl`

Used when: Gutenberg fetch fails OR `LUME_OFFLINE=1` is set.

Content: ~30 paragraphs from public domain texts, committed to the repo. Each paragraph is ≥50 words.

## Real-User Data

File: `docs/data/real_user_log.csv`

Columns: `user_id, text_hash, features_json, adaptation_config_json, wpm, comprehension_score, comprehension_type, reward, data_source`

**No raw text.** `text_hash` column omitted from the committed CSV (HMAC-SHA-256 of normalized text with per-machine salt from `.env`; not claimed to be one-way against brute-force dictionary attacks).

## Licensing

All corpus content used is public domain (Project Gutenberg pre-1928 works). Synthetic data is generated from scratch and carries no third-party licensing.
