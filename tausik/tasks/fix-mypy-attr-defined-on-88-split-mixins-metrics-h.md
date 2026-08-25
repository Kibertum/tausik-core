---
slug: fix-mypy-attr-defined-on-88-split-mixins-metrics-h
title: "fix mypy attr-defined on #88 split mixins (metrics + hierarchy)"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: split-backend-queries-metrics
scope: "scripts/backend_queries_metrics.py, scripts/service_hierarchy.py"
scope_exclude: null
relevant_files:
  - "scripts/backend_queries_metrics.py"
  - "scripts/service_hierarchy.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T09:05:15Z"
---

## Goal

The #88 filesize-split batch extracted BackendQueriesMetricsMixin (backend_queries_metrics.py) and HierarchyMixin (service_hierarchy.py), but those mixins access host-class attributes (_q/_q1, epic_list, session_current, session_usage_summary, _require_epic, _require_story) that mypy cannot resolve on a standalone mixin — 18 attr-defined errors. The pre-commit mypy hook blocks the commit. The sibling backend_queries_usage.py established the fix pattern (inline # type: ignore[attr-defined]); the split author omitted it. Apply the same so mypy is clean and the batch commits.

## Acceptance Criteria

1. backend_queries_metrics.py: all host-class accesses (self._q/_q1, self.epic_list, self.session_current, self.session_usage_summary) carry # type: ignore[attr-defined], matching backend_queries_usage.py precedent. 2. service_hierarchy.py: self._require_epic / self._require_story resolved via TYPE_CHECKING method stubs (matching the file's be: SQLiteBackend style). 3. python -m mypy passes with 0 errors. 4. Negative/boundary: runtime behaviour UNCHANGED (comments/TYPE_CHECKING only, never executed) — pytest stays green, no new ruff violations. 5. bootstrap re-run so .claude mirror matches scripts. 6. Security: no threat surface — change is type-annotation-only, no logic/IO/input handling touched.

## Plan

## Rollback

git revert / remove the added # type: ignore comments

## Journal

- 2026-06-14T09:04:50Z [implementation] — backend_queries_metrics.py: 12 inline # type: ignore[attr-defined] (matches backend_queries_usage.py precedent). service_hierarchy.py: TYPE_CHECKING method stubs for _require_epic/_require_story (matches the file's existing be: SQLiteBackend annotation style). Bootstrap re-run. mypy: Success, 0 issues (198 files). ruff clean. Targeted pytest: 154 passed (metrics/hierarchy/epic/story).
- 2026-06-14T09:05:14Z [implementation] — AC-1: ✓ 12 inline # type: ignore[attr-defined] on _q/_q1/epic_list/session_current/session_usage_summary in backend_queries_metrics.py — verified by reading file + mypy. AC-2: ✓ TYPE_CHECKING stubs for _require_epic/_require_story in service_hierarchy.py. AC-3: ✓ python -m mypy → Success, 0 issues (198 files). AC-4 (negative): ✓ comments/TYPE_CHECKING never execute → runtime unchanged; targeted pytest 154 passed, ruff clean — tested via tests/ -k 'metric or hierarchy or epic or story'. AC-5: ✓ bootstrap re-run. AC-6 (security): ✓ type-annotation-only, no logic/IO touched. Domain: get_metrics()/epic CRUD produce identical results — the mixins are mixed into the same composed classes at runtime, ignores affect only static analysis. Root cause (category=process): split task closed without running the mypy pre-commit hook (commit was deferred), so the omitted attr-defined ignores went undetected. Prevention: run `python -m mypy` before closing any filesize-split that extracts a mixin.
