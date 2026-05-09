# Lume — Architecture

## Next.js Version

Determined at scaffold time via `pnpm dlx create-next-app@latest --version`. Updated below after scaffold.

**Scaffolded version:** Next.js 16.2.6 (create-next-app@latest as of 2026-05-09)

---

## §B.2.1 Adaptation Set (7 toggles)

| # | Toggle | Values | Notes |
|---|---|---|---|
| 1 | letter_spacing_em | 0.0 / 0.04 | binary |
| 2 | word_spacing_em | 0.0 / 0.16 | binary |
| 3 | hyphenation_on | bool | Knuth-Plass-inspired DP |
| 4 | emphasis_on | bool | UI label: "Reading emphasis" (not "difficult words") |
| 5 | color_overlay_on | bool | binary, single warm overlay; WCAG-AA-tested colors |
| 6 | chunked_on | bool | ~80-word chunks, recursion-based splitter |
| 7 | opendyslexic_on | bool | Optional; locally bundled font (SIL-OFL) |

## §B.2.2 Font Policy

- **Default:** Lexend via `next/font/google` (self-hosted by Next.js; SIL-OFL)
- **Optional:** OpenDyslexic at `apps/web/public/fonts/OpenDyslexic-Regular.woff2` with SIL-OFL LICENSE.md
  - Toggle hidden via `document.fonts.check('1em "OpenDyslexic"')` if font fails to load
  - Cut at hour 3 if stub loop is not complete

## §B.2.3 Token Rendering

- Backend returns `tokens: list[Token]` with final display-ready text (hyphenation applied server-side)
- Frontend renders `<span>` elements with `class_hints` from each token
- **No DOMPurify, no HTML injection** — all content is token text only
- `Token.hyphenated` field removed (rev. 4); backend emits final display tokens

## §B.2.4 Render Cache

- **Process-local in-memory cache only** (not durable)
- Cache key: `(text_hash, sha1(json(adaptation_config_canonical)))`
- Reload clears the cache
- README and all docs say "process-local in-memory cache" everywhere — never "durable caching"

## §B.2.5 Events Table

Columns: see `schema.sql`. Key design decisions:

- **`data_source`** (not `source`): backend infers server-side
  - `'real_user'` if `LUME_COLLECT_MODE == 'real_user'`
  - `'demo'` if `user_id == DEMO_USER_ID`
  - else `'demo'` (live API never writes `'synthetic'`)
  - `'synthetic'` written only by scripts/notebook seeders
- **`recommendation_source`**: how the config was chosen (`bandit`, `model`, `demo_seed`, `mode_default`, `mode_bionic`, `mode_lume_tuned`, `user_override`)
- **`render_id`**: TEXT column linking each event to its originating render
- **`word_count`**: enforces ≥50 word logging gate
- **`created_at`**: `int(time.time() * 1000)` computed in Python — millisecond precision (SQL `strftime` only gives second-level × 1000)
- **`was_user_modified`**: bool stored as INTEGER 0/1; round-tripped in Python

## §B.2.6 ML System

### 47-Dim Feature Vector

```
text_features (5)         = [avg_word_len, syllable_density, freq_percentile_mean, sentence_count, flesch_kincaid]
adaptation_indicators (7) = [letter_spacing_em, word_spacing_em, int(hyph_on), int(emph_on), int(color_on), int(chunk_on), int(od_on)]
interactions (35)         = flatten([t * a for t in text_features for a in adaptation_indicators])
feature_vector            = concat(text_features, adaptation_indicators, interactions)  # 47 total
```

Main effects are included to prevent all-zero (default) config from collapsing to the same vector regardless of text.

### Per-User Ridge

- StandardScaler + Ridge regression
- **Fitting gated on `n_events_for_user >= 30`** — below this threshold, recommender uses bandit only
- Documented as hackathon simplification: "47 features against 10 events is underdetermined — bandit-only below n=30"
- `was_user_modified=True` rows excluded from Ridge training

### Thompson-Sampling Bandit (16 arms)

- Beta(α, β) posteriors; continuous reward update: `α += reward`, `β += 1.0 - reward`
- **Posteriors not persisted to disk**; rebuilt from events table on startup via `rebuild_from_events(db)`
- Demo RNG seeded **once per process** via `bandit.seed_demo_user(42)` in `app/main.py`
- Per-user `np.random.Generator` instances stored in `self._rngs[user_id]`

### Mode → Config Mappings (`app/api/mode_configs.py`)

| Mode | Config |
|---|---|
| `mode_default` | All toggles off, both spacings 0.0 |
| `mode_bionic` | `emphasis_on=True`, all others off |
| `mode_lume_tuned` | Bandit/model recommendation; bandit if n_events < 30 |

### arm_index=-1

Used for `recommendation_source ∈ {mode_default, mode_bionic, user_override}`. `mode_lume_tuned` resolves to a real arm (0–15).

## §B.2.7 Real-User Collection Mode

- Env var: `LUME_COLLECT_MODE=real_user` (restart uvicorn after setting)
- Forces uniform-random arm from **5-arm balanced subset**: `default`, `letter+word_spacing`, `hyphenation+spacing`, `emphasis+spacing`, `chunked+spacing`
- Defined in `app/ml/real_user_arms.py`

## §B.2.8 API Shape

### `/render` (POST) — read-only

- Accepts `RenderRequest`; returns `RenderResponse`
- **Writes nothing to events table**
- Populates `render_sessions[render_id]` (in-memory)
- If `mode == 'lume_tuned'`, calls recommender and populates `arm_index` and `recommendation_source`

### `/rate` (POST) — sole event writer

- Accepts `RateRequest`; reads `render_sessions[render_id]` for context
- Falls back to client-supplied `text_hash`, `features_json`, `word_count`, `text_id` if session not in memory
- Gates on `word_count >= 50`
- Computes `reward`, infers `data_source`, inserts exactly one row

### Error Shape (3 handlers)

```json
{"error": {"code": "validation_error", "message": "..."}}   // 422
{"error": {"code": "...", "message": "..."}}                  // original HTTPException status
{"error": {"code": "internal_error", "message": "..."}}      // 500 (no stack trace)
```

## §B.2.9 Frontend Architecture

- Browser calls `/api/render` and `/api/rate` (Next.js route handlers)
- Route handlers call `TYPO_API_BASE_URL` (server-side only; never `NEXT_PUBLIC_TYPO_*`)
- `AbortController` with 5s timeout in each route handler
- Debounce 300ms on adaptation toggle changes before re-render

## §B.2.10 Warm Color Overlay (locked CSS values)

```css
:root {
  --lume-overlay-warm: oklch(0.97 0.03 80);   /* parchment-warm; AA against default and emphasized text */
  --lume-emphasis: oklch(0.35 0.18 25);        /* AA on overlay AND on white */
}
```

WCAG-AA verified in Phase 4 axe audit. Adjust L only if violations found — never re-pick colors from scratch.

## §B.2.11 Path Helpers (`app/store/paths.py`)

- `repo_root()`: walks upward from `__file__` until `pnpm-workspace.yaml` found; falls back to `LUME_REPO_ROOT` env
- `db_path()`: returns `Path(os.environ.get("LUME_DB_PATH") or (repo_root() / "services/typo/seed.db"))`
- No absolute paths baked into code or `.env.example`
