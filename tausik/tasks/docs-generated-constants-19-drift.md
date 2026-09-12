---
slug: docs-generated-constants-19-drift
title: "Синхронизировать сгенерированные константы документации с 1.9"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: scoped-pytest-empty-late-batch
scope: "Regenerate only docs/_generated/constants.json from its checked-in sources, with focused proof in the existing check-docs test; update generated task/story state."
scope_exclude: "Do not change product version, MCP tools, documentation prose, release/tag/push, or user-owned .agents/."
relevant_files: []
scope_paths:
  - "docs/_generated/constants.json"
  - "tests/test_check_docs_hook.py"
  - "tausik/tasks/docs-generated-constants-19-drift.md"
  - "tausik/tasks/scoped-pytest-empty-late-batch.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить воспроизводимый дрейф docs/_generated/constants.json, из-за которого check_docs красный на версии 1.9.0 и загрязняет scoped verification несвязанных задач.

## Acceptance Criteria

AC-1: generator output matches live pyproject and MCP tool source for 1.9.0. AC-2: tests/test_check_docs_hook.py::TestRealRepoSync::test_exit_0_when_in_sync passes. AC-3: no source version or tool count is changed merely to fit a stale artifact. AC-4: negative boundary: a deliberately stale generated artifact is still rejected by the existing check-docs proof. AC-5: focused pytest and signed verify pass.

## Plan

[{"step": "Inspect generator inputs and reproduce the check_docs drift without editing source claims.", "done": false}, {"step": "Regenerate the checked-in constants artifact from live sources.", "done": false}, {"step": "Run focused check-docs proof and signed verify, recording evidence.", "done": false}]

## Rollback

Revert the generated constants update if the generator output is shown inconsistent with its source.

## Journal

- 2026-09-12T10:22:59Z [implementation] — Reproducing generator drift from checked-in sources before any edit. The task is artifact-only: version and MCP source remain read-only inputs.
- 2026-09-12T10:23:24Z [implementation] — Generator updated constants.json from live sources (skills_core_count 13→14; test_count 10576→10775). The focused real-repo check now fails only because README.md and README.ru.md still claim 13 core skills. This is a separate documentation drift introduced by the new skill, not a reason to alter generator output or source counts. An attempted scripts/check_docs.py invocation was invalid because that file does not exist; the existing pytest proof is the authoritative check.
