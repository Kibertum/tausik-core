---
slug: route-explanations-to-smallest-useful-format
title: "Route explanations to the smallest useful format"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "answer contract/format routing, existing Mermaid/artifact integration points, response audit, focused existing tests, EN/RU documentation and changelog."
scope_exclude: "No automatic videos, paid voice APIs, API-key handling, decorative artifacts, synthetic benchmark fan-out, new frontend framework, commit, push, or release."
relevant_files:
  - "scripts/answer_shape.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "changelog.d/conditional-explanation-format-routing-111.md"
scope_paths:
  - "scripts/answer_shape.py"
  - "scripts/hooks/user_prompt_submit.py"
  - "tests/test_answer_rules_every_prompt.py"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "changelog.d/conditional-explanation-format-routing-111.md"
scope_tools: []
depends_on:
  - controlled-prose-for-user-facing-answers
completed_at: "2026-10-02T11:58:41Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Choose prose, table, Mermaid diagram, or opt-in HTML from the information shape so explanations become easier to understand without generating expensive artifacts by default.

## Acceptance Criteria

AC-1 A shipped decision rule keeps short prose as the default; uses a table for repeated exact mappings/comparisons and Mermaid for hierarchy, sequence, or three-plus connected relationships. AC-2 HTML is opt-in or requires a named interactive need that text/table/diagram cannot meet; video remains outside automatic routing. AC-3 The router reuses existing answer rules and artifact capabilities without adding a parallel telemetry or renderer path. AC-4 Natural answers or existing fixtures verify every route and the fallback. Negative: uncertainty, missing renderer support, accessibility risk, or no material comprehension gain falls back to concise prose without error.

## Plan

[{"step": "Define a minimal format matrix from information shape and comprehension need", "done": true}, {"step": "Wire the matrix into the existing answer contract and artifact paths", "done": true}, {"step": "Cover prose fallback plus table, Mermaid, and opt-in HTML with compact behavioral cases", "done": true}, {"step": "Validate on natural answers and report output cost without a synthetic artifact run", "done": true}]

## Rollback

Remove the format-routing clause and retain concise prose as the universal fallback; generated artifacts are disposable.

## Journal

- 2026-10-02T11:33:14Z [planning] — User specification: route explanations by comprehension value—text first, then table/diagram, HTML only for genuine interactivity. Large disposable artifacts are allowed only when they pay for themselves; video and API-key workflows are excluded from automatic 1.11 behavior.
- 2026-10-02T11:52:15Z [implementation] — Defined the bounded format matrix and prose fallback.
- 2026-10-02T11:52:15Z [implementation] — Step 1 done: matrix is prose default; table for ≥3 exact mappings/comparisons; Mermaid for hierarchy, sequence or ≥3 linked parts; HTML only for explicit/named interaction; video never auto-selected; uncertainty/accessibility/no gain → prose.
- 2026-10-02T11:56:37Z [implementation] — Step 2 done: reused answer_shape + UserPromptSubmit. The 773-char always-loaded contract is unchanged; only explanation-shaped prompts receive the matrix. No renderer, telemetry, frontend or model call was added.
- 2026-10-02T11:56:37Z [implementation] — Step 3 done: one existing test covers table, Mermaid, HTML, video and RU triggers plus ordinary-prose fallback and live hook delivery. Focused file: 5 passed.
- 2026-10-02T11:56:37Z [implementation] — Wired conditional guidance through the existing prompt hook.
- 2026-10-02T11:56:38Z [implementation] — Covered all routes and fallback in one compact behavioral case.
- 2026-10-02T11:57:22Z [implementation] — Step 4 done: natural prompts 'продолжай работу' and 'Изучи и давай распланируем' add 0 chars; an actual RU explanation request adds one 337-char/49-word matrix. No artifact/model run was generated. Hook-focused lane: 152 passed.
- 2026-10-02T11:57:22Z [implementation] — Validated natural prompt routing and measured conditional instruction cost without generating artifacts.
- 2026-10-02T11:58:24Z [implementation] — AC-1/2 (prose/table/Mermaid/HTML/video matrix): ✓ tests/test_answer_rules_every_prompt.py::test_explanation_format_matrix_covers_routes_and_hook_delivery AC-3 (existing hook and answer module, no renderer/telemetry): ✓ tests/test_answer_rules_every_prompt.py::test_the_hook_injects_the_rules_on_a_prompt_with_no_prior_answer AC-4 and Negative (RU/EN routes, ordinary fallback, no error): ✓ tests/test_answer_rules_every_prompt.py::test_explanation_format_matrix_covers_routes_and_hook_delivery Natural cost: ordinary prompts 0 chars; matched prompt 337 chars/49 words. Scoped verification_run #3372: 741 passed, 12 skipped, 23/657 files.
- 2026-10-02T11:58:37Z [implementation] — AC-1 prose/table/Mermaid routing verified by tests/test_answer_rules_every_prompt.py::test_explanation_format_matrix_covers_routes_and_hook_delivery. AC-2 HTML and video remain opt-in. AC-3 existing UserPromptSubmit and answer_shape paths are reused; no renderer or telemetry was added. AC-4 RU/EN routes and prose fallback verified. Negative: uncertain, unsupported, inaccessible, or unclear benefit routes to prose. Domain: natural ordinary prompts add 0 chars; matched prompts add 337 chars. Verification_run #3372 passed 741 tests over 23 of 657 mapped files.
