---
slug: fix-1-11-3-published-claims-spec-code-parity-21
title: "Fix 1.11.3 published claims: SPEC/code parity, 21.4x derivation, missing references"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: r1112-pooled-verification-proof-and-rollout
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/cli-quality.md"
  - "docs/ru/cli-quality.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/verification-cohort-contract.md"
  - "docs/ru/verification-cohort-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/verify_baseline.py"
  - "tests/test_verify_baseline.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T17:08:08Z"
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

Make the published 1.11.3 claims match the implementation: EN SPEC diverges from code and its RU mirror (member-status-drift, v75 columns, SS3), the 21.4x headline is not derivable from any published pair, the new pooled MCP tools and CLI flags are missing from the references, and stale 152/62KB figures survived the 149 edit.

## Acceptance Criteria

AC-1: EN SPEC matches code and RU mirror: member statuses in SS1, member-status-drift in SS4, v75 column named cohort_identity (not cohort_id/cohort_size), SS3 marked honestly if the fine-grained set stays unwired. AC-2: the 21.4x claim either carries a published derivation (which gate-execution counts produced it) or is replaced by the derivable 34x executions / 4.7x wall in all four surfaces (CHANGELOG en+ru, SPEC en+ru). AC-3: mcp.md en+ru gain tausik_verify_cohort/tausik_verify_hierarchy rows and story/epic done verify_handle args; cli-quality.md documents verify --tasks/--story/--epic; cli-tasks.md documents story/epic done --verify-handle; configuration.md documents memory_tail_by_relevance. AC-4: stale numbers corrected: main 149 count line, 58KB/14.8k surface-cost figure, 'memory archive --confirm' naming. AC-5 negative: no number published without its denominator; en/ru rows agree cell-for-cell (doc parity check green).

## Plan

## Rollback

## Journal

- 2026-10-07T17:07:51Z [implementation] — AC EVIDENCE (verify run #3612 PASS: 362 passed / 16 skipped over 6/668 scoped files; gen_doc_constants OK; dedupe 282/669 on baseline; translation drift exit=0). AC-1 VERIFIED: SPEC EN matches code and RU mirror — SS1 carries member statuses, SS4 carries member-status-drift among named invalidators; SS5 names the REAL v75 column cohort_identity (was cohort_id/cohort_size; verified against backend_migrations_v75.py:13 + backend_schema.py:322); SS3 rewritten honestly: required_after_red is pure+unit-proven but NOT wired in the live path (only occurrence in scripts/ is the definition; after red the pooled run re-executes the full lane) — RU mirror carries the same statement. AC-2 VERIFIED: 21.4x REPLACED by the derivable pair in all four surfaces — CHANGELOG EN+RU and SPEC EN now read 34x executions (34 -> 1) / 4.7x wall (1492.1 s -> 314.6 s, ~19.6 min returned); SPEC RU already carried it; README has no 21.4 cells (grep). AC-3 VERIFIED: mcp.md EN+RU gained tausik_verify_cohort (tasks) / tausik_verify_hierarchy (kind, slug) rows + verify_handle args on story/epic done rows; cli-quality.md EN+RU document verify --tasks/--story/--epic with widening semantics + contract link; cli-tasks.md EN+RU document epic/story done [--verify-handle H]; configuration.md EN+RU document memory_tail_by_relevance (default false, relevance head, recency fallback). AC-4 VERIFIED: main count line 152 -> 149 (149+7=156 consistent); surface-cost figure replaced with the measured 59,602 bytes / ~59.6 KB / ~14.9k est tokens (EN+RU), citing the gates.json mcp_surface ratchet — measured by the ratchet's own probe (count=149, bytes=59602); 'memory archive --confirm' naming checked repo-wide against live CLI --help: no stale spelling remains (only correct hygiene archive --confirm and memory archive --before ... --confirm). PLUS (owner briefing item): verify_baseline.py recounted — per-slug duplicate windows fixed (story-level 2h gap slicing, distinct membership), invocations attributed to their own window only, sizes 3-4 gained their own bucket; 4 tests pin both defects; published numbers restated WITH denominators everywhere: 2187/3605 re-runs = 60.7% (was 2153/3562 = 60.4%), >=5 cohorts 1147 invocations / ~8.4 h / 58 cohorts / 466 seats / under-declared 658 (was inflated 2049 / ~12.5 h / 1175), 3-4 bucket 625 invocations / 71 cohorts; SPEC EN Why + CHANGELOG EN+RU contract entry also fixed: selected_tests marked dropped from identity with the reason, cohort_identity column named. AC-5 NEGATIVE VERIFIED: every republished number carries its denominator (pairs above); en/ru rows agree cell-for-cell — translation-drift audit exit=0 after the intentionally-abbreviated RU contract mirror declared itself with the bare skip marker (format pinned by regex, reason kept in an adjacent comment); doc constants check OK. Domain: all corrected figures recomputed from the live production DB and the ratchet probe, none synthesized.
- 2026-10-07T17:08:07Z [implementation] — Root cause (documentation): the published claims were written from an early draft of the contract and a defective counter — 21.4x was not derivable from any published pair (the derivable pair is 34 executions and 1492.1/314.6 s), the EN SPEC named v75 columns that never existed in code, and verify_baseline.py double-counted windows (per-slug slicing + cross-window attribution) while silently dropping sizes 3-4. Prevention: convention #340 — a constant quoted in prose is backed by a test reading the machine source; published ratios must name their derivation pair, and a counter's buckets must partition the space (every size matches exactly one bucket).
