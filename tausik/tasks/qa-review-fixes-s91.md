---
slug: qa-review-fixes-s91
title: "Apply separate-model review findings (rule7 + notes-guard)"
status: done
epic: v15-polish
story: v15p-debt
complexity: simple
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "scripts/project_cli_task.py, scripts/root_cause.py (nudge text only), tests/test_root_cause_structured.py, tests/test_task_update_notes_guard.py"
scope_exclude: "scripts/task_notes_guard.py (lazy import left as-is — reviewer confirmed runtime-safe), regex logic (behavior correct)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T12:46:51Z"
---

## Goal

Address the adversarial Sonnet review of session #91 code: (Medium-1) CLI 'task update --notes-overwrite' without --notes does a misleading no-op DB write reporting 'updated' — guard it; (Medium-2/Low) the colon-separator label root-cause form is accepted but not advertised — make the nudge wording honest; (Low) strengthen the weak colon-form test to assert the full dict and add guard edge-case tests (empty-string notes, whitespace notes, overwrite-without-notes).

## Acceptance Criteria

AC-1: CLI 'task update --notes-overwrite' without --notes prints a clear stderr notice and does NOT issue a no-op update (Medium-1). AC-2: structured_nudge_message wording honestly reflects the accepted label forms (both '—' and ':' separators) (Medium-2). AC-3: test_label_form_colon_then_dash_accepted asserts the full {category,description,prevention} dict (Low). AC-4: new guard tests: empty-string notes on non-empty journal refused, whitespace-only notes refused, notes_overwrite without notes is a no-op (Low). Negative: no behavior change to the happy paths already covered; all prior tests stay green. AC-5: targeted tests + ruff + filesize green via .tausik/tausik.

## Plan

## Rollback

git checkout -- the 4 files; additive test/UX-guard only, no logic/migration change.

## Journal

- 2026-06-14T12:46:50Z [implementation] — AC verified: 1. ✓ CLI 'task update --notes-overwrite' without --notes now prints stderr notice + returns, no no-op write (project_cli_task.py:143). 2. ✓ structured_nudge_message lists both label separators honestly (root_cause.py). 3. ✓ test_label_form_colon_then_dash_accepted asserts full dict. 4. ✓ added test_empty_string_notes_refused, test_whitespace_notes_refused, test_overwrite_flag_without_notes_is_noop. 5. ✓ 24 passed (root_cause+notes_guard), ruff clean, no filesize breach. Negative: happy paths unchanged, all prior tests green. Domain: addresses separate-model (Sonnet) adversarial review — 0 crit/0 high; the 1 real UX bug (misleading no-op 'updated') is now fixed.
