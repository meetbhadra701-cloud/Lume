# Rule Change Log

Format: YYYY-MM-DD HH:MM <tz> — <file> §<section> — <change> — <rationale>
Append-only.

2026-05-06 09:30 PT — AI_RULES §2.1 — DeepSeek replaced with Anthropic API (notebook-only, optional) — manual editor's note + rev. 3 fixes 50-52
2026-05-06 09:32 PT — ARCHITECTURE §B.2.3 — DOMPurify removed; backend returns plain tokens; frontend renders <span>s — rev. 2 fixes 26-27
2026-05-06 09:34 PT — PRD §B.1.6 — Backend deployment beyond localhost added to Scope OUT — rev. 2 fix 36, rev. 3 fix 53
2026-05-06 09:36 PT — ARCHITECTURE §B.2.7 — Dyslexia-friendly font: Lexend default; OpenDyslexic optional + locally bundled — rev. 3 fix 24, rev. 4 fix 21
2026-05-06 09:38 PT — ARCHITECTURE §B.2.4 — BFS DSA row tentatively dropped pending genuine BFS use — rev. 3 fix 48
2026-05-06 09:40 PT — ARCHITECTURE §B.2.5 — events.source renamed events.data_source — rev. 4 fix 11
2026-05-06 09:42 PT — ARCHITECTURE §B.2.5 — events.render_id and events.word_count added — rev. 4 fixes 8, 9
2026-05-06 09:44 PT — ARCHITECTURE §B.2.6 — feature vector raised to 47 dims (5 main + 7 indicators + 35 interactions) — rev. 4 fix 16
2026-05-06 09:46 PT — ARCHITECTURE §B.2.6 — per-user Ridge gated on n_events >= 30 — rev. 4 fix 17
2026-05-06 09:48 PT — ARCHITECTURE §B.2.5 — Token.hyphenated removed; backend emits final display tokens — rev. 4 fix 35
2026-05-06 09:50 PT — PLAN §0.2 — Next.js version follows create-next-app@latest; --turbopack flag (not --turbo); --disable-git, --reset-preferences added — rev. 4 fixes 1-4
2026-05-06 09:52 PT — ARCHITECTURE §B.2.6 — bandit posteriors rebuilt from events on startup; demo RNG seeded once per process — rev. 4 fixes 18, 19
2026-05-06 09:54 PT — PLAN §5.1 — real-user collection narrowed to 5-arm balanced subset — rev. 4 fix 42
2026-05-06 09:56 PT — README §privacy — SHA-1 "non-reversible" claim removed; HMAC-SHA-256 with local salt — rev. 4 fix 22
2026-05-06 09:58 PT — apps/web — generated AGENTS.md/CLAUDE.md deleted; docs/AI_RULES.md is authoritative — rev. 4 fix 3
