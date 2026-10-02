---
slug: retrospektiva-rashoda-codex-1-11-kontekst-tool
title: "Ретроспектива расхода Codex 1.11: контекст, tool output и ценность тестов"
status: planning
epic: null
story: null
complexity: null
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Measured Codex traces: 3,596 response rounds; 451.6M input tokens, 441.5M cached (97.75%); average 125.6k input and 122.8k cached per response. At a 0.1 cached-input price illustration, cached reads still dominate weighted input volume, but OpenAI does not publish the ChatGPT/Codex weekly subscription accounting formula, so this is not a causal quota claim. The main controllable drivers are number of model returns times persistent prefix/conversation size; raw final pytest logs were only 16.1KB default + 0.6KB slow, so output text alone is secondary. Suite inventory: 12,822 default cases + 143 slow, 654 test files, 8,490 source test functions; default wall 145.6s and slow 135.4s. Static audit found 448 source-text contract tests and 109 single-shape candidates; dedupe audit found 282 parallel groups/669 tests but zero proven literal copies, so deletion requires behavioral evidence. High-cost meta families include generated-doc constants, doctor/doc drift, dead-symbol, hygiene, dedupe and registry scans. Recommended wave: (1) host-context lifecycle guard: TAUSIK session reopen in same host thread is not fresh context; warn/block before context/quota runaway, checkpoint and emit fresh-window prompt; (2) compact project instructions/tool schemas and enforce output-to-artifact with bounded failure summaries; (3) change-scoped test selection for ordinary verify, full default/slow only release/cadence; (4) evidence-based pruning of low-value source/existence/exact-string/duplicated meta tests with no replacement governance tests, preserving security behavior; (5) measure natural accepted task rounds and quota observations. External evidence: official OpenAI docs say cached tokens are discounted but still count toward token rate limits; GitHub recommends lean context, minimal toolsets, fresh/compacted sessions, stable model/settings for cache, cheaper focused subagents, and short grounded instructions; pytest supports quiet/short output and JUnit artifacts; pytest-testmon selects tests affected by changes; mutmut recommends mutation evidence and localized tests.

## Acceptance Criteria

## Plan

## Rollback

## Journal
