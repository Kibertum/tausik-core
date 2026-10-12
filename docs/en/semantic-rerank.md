[Русский](../ru/semantic-rerank.md) | **English**

# Semantic re-rank: optional, gated, and off until it is worth paying for

<!-- doc-map: reader=maintainer; zone=memory-and-store -->

Keyword search over the shared knowledge store is FTS5 with BM25F field weighting
(`bm25(fts_memory, 10.0, 1.0, 3.0)` — title over tags over content). This page describes the
optional layer that can REORDER what that search already found, why it is optional, and the
three gates that keep it out of the way.

## Why a re-rank and not a search

The plan for this feature was pure local embeddings. The published record turned it around:

| Evidence | What it says |
|---|---|
| Cursor online A/B, 2025-11-06 | +12.5% offline retrieval accuracy, **+0.3%** on code actually kept; +2.6% only past a thousand files |
| Sourcegraph | **Removed** embeddings in favour of BM25F over a code graph |
| Short keyword queries | semantic retrieval collapses to nDCG@10 near zero — and that is the dominant shape an agent sends |
| CORE-Bench, June 2026 | the hybrid wins; no single method dominates |

So the keyword path is the spine. This layer can only reorder candidates FTS5 returned: it
cannot introduce a row FTS5 missed and cannot remove one it found.

## The three gates

| Gate | Closed when | Because |
|---|---|---|
| `no-provider` | no `semantic_rerank` block, or `enabled: false` | default off is the zero-dependency promise |
| `small-corpus` | fewer than 1000 live rows | the effect does not exist below that size; a round-trip would buy latency only |
| `keyword-query` | under 4 words, or no glue word | the shape semantic retrieval fails on |

Two more reasons appear in telemetry after the layer has started: `provider-failed` (down,
unreachable, or answering the wrong shape) and `over-budget` (slower than the configured
timeout). Both hand back the keyword order.

**A closed gate costs nothing.** The candidate window stays at the page size, the provider is
never contacted, and the result is byte-identical to a checkout without this module.

## Configuration

```json
{
  "semantic_rerank": {
    "enabled": true,
    "endpoint": "http://127.0.0.1:11434/api/embed",
    "model": "nomic-embed-text",
    "timeout_s": 2.0
  }
}
```

The endpoint must accept `{"model": ..., "input": [...]}` and answer `{"embeddings": [[...]]}`
for the whole batch. Batched deliberately: one request per candidate would put twenty
round-trips inside a two-second budget, and this way it is two.

## How the orders are combined

Reciprocal Rank Fusion, `1/(60 + rank)` summed over both orderings. Not a weighted sum of
scores: BM25 and cosine are not on the same scale, and calibrating them needs labelled data
this project does not have — a made-up weight would be a number with no evidence behind it.
Ties resolve to the keyword order, so an equal score never reshuffles what FTS5 decided.

## Measured on our own traffic

Vendor benchmarks are not trusted here: LoCoMo was discredited when a no-memory baseline beat
Mem0 73:68. Two commands answer from this machine:

```bash
python scripts/semantic_rerank.py --probe     # what the gates say about this corpus
python scripts/semantic_rerank.py --report    # what the layer actually did
```

**The measurement at the time of writing: the shared store held 45 live rows against a
threshold of 1000 — 4.5% of it — and no provider was configured.** Both query shapes meet a
closed gate, so the activation rate here is zero. That is the finding, not a gap: the layer
exists switched off until the corpus makes it worth paying for.

Keyword-path latency, measured over 20 searches on the live store: median 6.3 ms, p95 46.2 ms
against a 2 s budget.

## What is never recorded

**The query text.** A search string can carry a secret, and a telemetry file is the last place
to learn that. `semantic_rerank.jsonl` records the gate, the corpus size, the candidate count,
whether the top page changed, and the elapsed milliseconds — shapes and outcomes, never words.
Its retention is declared with the other sidecars in `scripts/telemetry_retention.py`.

## See also

- [Knowledge store](knowledge-store.md) — what the shared store is and how rows get into it.
- [What is NOT guaranteed](known-limitations.md).
