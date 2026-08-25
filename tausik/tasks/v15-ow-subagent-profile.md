---
slug: v15-ow-subagent-profile
title: "Sub-agent skill profile + handoff contract"
status: done
epic: v15-orchestrator-worker
story: v15-ow-core
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "handoff contract module, worker skill profile definition, tests/test_ow_profile.py, docs"
scope_exclude: "CLI delegate handler (v15-ow-delegate-cli); hook wiring (v15-ow-hook-recognize)"
relevant_files:
  - "scripts/ow_handoff.py"
  - "scripts/service_delegate.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "tests/test_ow_handoff.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T20:48:54Z"
---

## Goal

Define the worker sub-agent profile: a trimmed skill set + a structured handoff contract (task slug, goal, AC, scope, scope_exclude, recommended model) that the orchestrator passes when spawning, and that the worker echoes back. Ensures a delegated worker starts with exactly the context it needs and nothing more (token economy + scope discipline).

## Acceptance Criteria

AC1: a documented handoff contract schema (task slug, goal, AC, scope, scope_exclude, recommended model) is defined and serialized deterministically. AC2: a worker skill profile (trimmed skill set) is defined and selectable. AC3: round-trip — contract built from a task equals what a worker echoes back (no data loss). AC4: missing optional fields degrade gracefully. AC5: tests in tests/test_ow_profile.py; filesize<400; stdlib-only.

## Plan

## Rollback

git revert; profile + contract are new additive modules, no existing behavior changed.

## Journal

- 2026-06-14T20:48:37Z [implementation] — Implemented handoff contract + worker profile. ow_handoff.py (pure): build_handoff_contract(task, delegation) → deterministic {slug,goal,acceptance_criteria,scope,scope_exclude,model,skills}, missing fields→"" (no KeyError); serialize_contract (json sort_keys → round-trip identity); WORKER_SKILLS=(task,test,debug,review,commit) trimmed (no plan/explore/brain). service_delegate.task_handoff(slug) builds from task_get+task_delegation. CLI `task handoff <slug>` prints contract JSON (orchestrator passes to Agent tool). 7 tests; CLI wired (post-bootstrap). ruff/mypy clean.
- 2026-06-14T20:48:54Z [implementation] — AC1: ✓ documented handoff contract schema (slug/goal/AC/scope/scope_exclude/model/skills) serialized deterministically (json sort_keys) — test_carries_task_fields..., test_serialize_is_deterministic. AC2: ✓ worker skill profile WORKER_SKILLS (trimmed; excludes plan/explore/brain) defined + carried in contract — test_worker_profile_excludes_orchestrator_skills. AC3: ✓ round-trip identity parse(serialize(c))==c — test_serialize_parse_is_identity. AC4: ✓ missing optional fields → '' (no KeyError) — test_missing_optional_fields_degrade_to_empty. AC5: ✓ 7 tests; ow_handoff.py 49<400; CLI wired (reaches service post-bootstrap). Domain: the contract is the exact payload the orchestrator passes to the Agent-tool spawn and the worker echoes back — pure fns → identical both ends. Negative: bare task dict / None delegation degrade to empty strings; unknown task → ServiceError.
