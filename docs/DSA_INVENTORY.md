# DSA Inventory

| DSA | File | Function | Complexity | Test | Product Feature (visible) | Notes |
|---|---|---|---|---|---|---|
| Hashmap | `app/api/routes.py` | `render_sessions` dict + process-local render cache by `(text_hash, sha1(json(config)))` | O(1) amortized | `test_render_cache` + `test_render_cache_keyed_by_config` | Repeat-render speedup | Demo-only process-local; not durable |
| Trie | `app/data_structures/trie.py` | `lookup`, `freq_rank` | O(L) | `test_trie` | Reading emphasis (frequency-aware) | — |
| Binary search | `app/data_structures/freq_index.py` | `rank` | O(log V) | `test_freq_index` | Drives emphasis threshold | — |
| Heap (min) | `app/data_structures/adaptation_heap.py` | `top_k` | O(log k) push/pop | `test_adaptation_heap` | Top-k arm chips in inline post-reading panel | Row stands if top-k chips shown inline; otherwise dropped |
| DFS | `app/adaptations/syllables.py` | `walk()` | O(S) | `test_syllables` | Syllable emphasis | — |
| Recursion | `app/adaptations/chunking.py` | `chunk_text` | depth ≤ log L | `test_chunking` | Chunked pagination | — |
| Sliding window | `apps/web/lib/timing.ts` | `RollingAverage.push` | O(1) | `timing.test.ts` (only if vitest kept) | Rolling-WPM display in reader | Row stands only if RollingAverage is visibly used; otherwise drop |
| DP (KP-inspired) | `app/adaptations/hyphenation.py` | `_knuth_plass_breaks` | O(L²) memoized | `test_hyphenation_dp` | Optimal hyphen break selection | "Knuth-Plass-inspired" — not claiming canonical algorithm |

Note: BFS row removed — no genuine BFS use in codebase (rev. 4 fix from plan review).

Each row's "product feature" must be visible in the running app, or the DSA claim is dropped.
