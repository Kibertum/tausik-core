---
slug: quickstart-contradicts-readme-and-buries-first-run
title: "Quickstart contradicts README and buries the first run under jargon"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/quickstart.md"
  - "docs/ru/quickstart.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "docs/en/senar.md"
  - "docs/ru/senar.md"
  - "changelog.d/quickstart-contradicts-readme-and-buries-first-run.md"
scope_paths:
  - README.md
  - README.ru.md
  - "docs/"
  - "changelog.d/"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:14:05Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Cold read (session #279): quickstart.md:206 'Output economy' is a ~350-word paragraph (caveman, SPEC/ADAPT, response contract, a test path) in a guide that promises no prior experience (line 10). README:84 'No --force' vs quickstart:202 re-enabling gating via config and README:165 'enforces nothing' for untrusted Codex. senar.md:7 expands SENAR with 'Research'.

## Acceptance Criteria

AC-1 quickstart first-run path (Steps 0-8) has no paragraph over 80 words and no test-file path. AC-2 The contradictions are resolved to one statement each, true against the code (cite file:line): no --force vs auto_verify, untrusted Codex, legacy single-step close. AC-3 SENAR expansion is one spelling across README, quickstart, senar.md, both languages. AC-4 NEGATIVE: no setting documented before is lost — each moved callout lands in configuration.md and a link from the quick-start reaches it. AC-5 The same in docs/ru/quickstart.md.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T22:13:57Z [implementation] — AC-1: ✓ Step 7 callouts (582 words) moved out; no prose paragraph over 80 words and 0 test-file paths in Steps 0-8 of docs/en and docs/ru quickstart (the only >80-word blocks are the numbered install-prerequisite lists). AC-2: ✓ auto_verify stated once, true against scripts/config_trust.py:168-171 (closes without a signed receipt, a weakening a trusted tier tightens back); the 'legacy single-step' claim removed; README no longer says 'No --force'; Codex trust stated once in README, consistent with docs/en/model-providers.md#codex-enforcement-matrix. AC-3: ✓ SENAR = 'Supervised Engineering & Normative AI Regulation' (standard corpus); docs/en/senar.md:7 and docs/ru/senar.md:7 fixed, no other expansion in the tree. AC-4 Negative: ✓ every moved setting (context_tier, output_mode, model_profile, auto_verify, preserve-if-exists, structured task_done) lands in docs/{en,ru}/configuration.md#settings-met-in-the-quick-start, linked from Step 7; tests/test_docs_links_resolve.py green (425 passed). AC-5: ✓ RU mirrored.
