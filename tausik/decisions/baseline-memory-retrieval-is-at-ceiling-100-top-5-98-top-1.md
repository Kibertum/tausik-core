---
slug: baseline-memory-retrieval-is-at-ceiling-100-top-5-98-top-1
task: km-retrieval-baseline-eval
date: "2026-07-27"
edges: []
---

## Decision

Baseline memory retrieval is at CEILING (100% top-5, 98% top-1) for keyword-anchored facts over the flat 325-entry store — so the shared-knowledge topic-consolidation rework (decision #143) canNOT be justified by retrieval accuracy; its justification stays command-merge + smaller injected context.

## Rationale

km-retrieval-baseline-eval measured it with a committed 49-question, content-keyed set (scripts/eval_memory_retrieval.py). The number held at 100% even after fixing a substring-match bug to a token-start anchor, confirming it is not an artifact. TAUSIK's memory titles are keyword-rich, so distinctive-term FTS retrieves them near-perfectly. The eval is a fixed, id-independent regression probe: re-run after consolidation, any DROP below top-5 is the regression signal. Caveat: a harder natural-language-paraphrase set (queries independent of entry tokens, in the corpus language) would stress ranking more — noted as future work in the script.
