---
slug: quickstart-qg0-trap
title: "Fix quickstart first-task QG-0 negative-scenario trap"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/quickstart.md"
  - "docs/ru/quickstart.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T12:59:37Z"
---

## Goal

Remove the onboarding footgun: quickstart.md's first example task ('создай главную страницу с заголовком и кнопкой') hits the QG-0 negative-scenario HARD block (gate_qg0_check.py:201-207), contradicting the 'два-три сообщения на задачу' promise. Either make the example a task with a natural edge case, or pre-warn the reader that TAUSIK requires an error/boundary criterion and the agent supplies it — set expectations before the block fires.

## Acceptance Criteria

1. docs/en/quickstart.md and docs/ru/quickstart.md Step 6 set the expectation — BEFORE the reader's first `task start` — that acceptance criteria must include at least one error/boundary case (QG-0 Context Gate requires it) and that the agent supplies it automatically. 2. EN and RU stay structurally in sync (same added note, same list shape) — no translation drift. 3. NEGATIVE/boundary: the note must not overpromise — if the reader's own phrasing already implies an edge case the note still reads correctly (no contradiction), and it never claims QG-0 is optional. 4. Existing doc-drift / count / link gates stay green (no new drift introduced).

## Plan

## Rollback

## Journal

- 2026-07-27T12:59:35Z [implementation] — AC verified: 1. ✓ docs/en/quickstart.md + docs/ru/quickstart.md Step 6 point 2 now state the AC must include ≥1 error/boundary case, that QG-0 requires it, and that the agent supplies it automatically (example given) — placed BEFORE Step 7, i.e. before the reader's first task start. 2. ✓ EN/RU symmetric: same list position (point 2), same note structure, same example; translation-drift + doc-drift test suite green (383 passed). 3. ✓ NEGATIVE/boundary: note says the agent ADDS the criterion (does not claim QG-0 optional); reads correctly whether or not the reader's own phrasing already implies an edge case — no contradiction. 4. ✓ No counts/links changed (prose-only addition); pytest -k 'drift or quickstart or translation or doc' → 383 passed, 1 skipped, 0 failed.
