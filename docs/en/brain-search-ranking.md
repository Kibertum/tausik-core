# Brain search ranking (`brain_search`)

Local hits use SQLite FTS5 **bm25** (`brain_search.search_local`): lower `score` means more relevant.

When the MCP tool passes **`prefer_stack`** (list of strings, e.g. `python`, `react`):

1. The local path may return up to **`min(limit × 5, 100)`** candidates so a strong stack match is not dropped before reranking.
2. After merging with optional Notion fallback hits, results are sorted by **effective score**  
   `effective = bm25_score − stack_boost`, where `stack_boost` grows when a row’s `stack` JSON overlaps a preferred label (exact or substring match). Boost is capped so bm25 still dominates for distant matches.
3. The final list is truncated to **`limit`**.

Empty or whitespace-only **`query`**: handlers return an immediate message; `search_with_fallback` returns no results and a warning explaining that the query is empty.
