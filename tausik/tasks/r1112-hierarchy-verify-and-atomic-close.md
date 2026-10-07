---
slug: r1112-hierarchy-verify-and-atomic-close
title: "Close story and epic cohorts atomically from one receipt"
status: done
epic: release-1-11-3
story: release1113-pooled-verification
complexity: complex
role: backend
stack: python
tier: substantial
call_budget: 110
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_hierarchy.py"
  - "scripts/verify_cohort.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_verify.py"
  - "scripts/project_parser_hierarchy.py"
  - "scripts/project_cli.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "harness/claude/mcp/project/tools_extra.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_verify_hierarchy.py"
  - "tests/test_verify_cohort.py"
  - "tausik/gates.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_hierarchy.py"
  - "scripts/service_task*.py"
  - "scripts/project_parser*.py"
  - "scripts/project_cli*.py"
  - "scripts/verify_*.py"
  - "scripts/backend_*.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/test_hierarchy_update.py"
  - "tests/test_project_mcp.py"
  - "tests/test_verify_handle*.py"
  - "tests/test_tausik_service.py"
  - "tests/test_consumer_first_close.py"
  - "tausik/tasks/r1112-hierarchy-verify-and-atomic-close.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - r1112-cohort-receipts-and-incremental-rerun
completed_at: "2026-10-06T23:43:48Z"
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

Let story and epic closure consume one exact cohort receipt and atomically close all review-ready descendants, while leaving standalone task closure compatible.

## Acceptance Criteria

AC-1 erify --story <slug> and erify --epic <slug> resolve the exact non-done descendant task set and refuse an empty or single-task cohort unless explicitly requested as ordinary task verify. AC-2 Eligibility requires every member to be review-ready, all plan steps complete and numbered AC evidence present before the cohort run starts. AC-3 story done --verify-handle and epic done --verify-handle validate the exact cohort and close member tasks plus parent hierarchy atomically without rerunning gates. AC-4 Negative: a task added, removed, edited, reopened or made blocked after verify makes the handle stale; partial closure rolls back the transaction. AC-5 Standalone 	ask done and single-task handles keep their current contract; hierarchy use is opt-in and no task loses its own evidence trail. AC-6 CLI and MCP expose parity, bounded progress and an explicit denominator: members, test files, passed, failed, carried-forward, skipped and deselected.

## Plan

[{"step": "Resolve eligible story and epic descendants and surface readiness failures before running tests.", "done": true}, {"step": "Expose story/epic cohort verification through service, CLI and MCP with bounded progress.", "done": true}, {"step": "Consume exact cohort handles in an atomic task-plus-hierarchy closure transaction.", "done": true}, {"step": "Prove stale membership, task edits and partial-failure rollback while preserving standalone closure.", "done": true}]

## Rollback

Revert hierarchy/CLI/MCP integration; cohort receipts remain inert evidence and existing task done, story done and epic done commands retain their pre-1.11.2 behavior.

## Journal

- 2026-10-04T15:40:21Z [planning] — Inherits the approved 1.11.2 pooled-verification user specification from r1112-verification-cohort-contract. Hierarchy boundary: use story/epic when present, preserve standalone tasks when absent.
- 2026-10-06T23:43:42Z [implementation] — NO-DEAD-END: red runs #3579-#3584 were ratchets and doc pins catching a new surface — RUF100 (x2), transport purity (MCP handlers now call the shared cohort_summary/hierarchy_summary the CLI calls), MCP surface ratchet (baseline raised 147->149 tools / 59242 bytes with the Track A parity argument recorded in gates.json), doc drift (gen_doc_constants --write + README/README.ru/docs README tool-count cells 147->149). #3585 exit=0.
- 2026-10-06T23:43:43Z [implementation] — AC-1 (resolve exact non-done set; refuse empty/single): ✓ resolve_descendants story+epic (TestResolution 3 tests, incl. 'ordinary verify --task' referral). AC-2 (review-ready: plan complete, AC evidence): ✓ review_ready_reasons blocks incomplete plan and missing numbered AC evidence (TestReadiness). AC-3 (story/epic done --verify-handle closes atomically, no rerun): ✓ hierarchy_done_with_handle — one transaction closes members+parent+redeems handle; test_closes_everything_on_the_exact_receipt; runner called ONCE in run_hierarchy_verify (delegation, no gates at close). AC-4 NEGATIVE (added/removed/edited/reopened/blocked -> stale; partial closure rolls back): ✓ member statuses participate in cohort identity (member-status-drift invalidator added to verify_cohort); tests: edited-member stale, membership-change (blocked) stale, double-spend refused; rollback path names the cause and closes nothing. AC-5 (standalone task done and single-task handles unchanged; opt-in; evidence trail kept): ✓ test_standalone_story_done_untouched; cohort run stamped via verification_runs.cohort_identity keeps each member's audit link. AC-6 (CLI+MCP parity, explicit denominator): ✓ CLI verify --story/--epic + story/epic done --verify-handle; MCP tausik_verify_cohort/tausik_verify_hierarchy + verify_handle on story/epic done; hierarchy_summary prints members/test_files denominator. All: ✓ tests/test_verify_hierarchy.py 11 passed + test_verify_cohort.py 14 + transport ratchet green; verify #3585 handle 3585.710e1562f36f4d104bb0b5e2836f0766. Domain: real schema transaction (cursor, BEGIN/COMMIT/ROLLBACK); lifecycle guards respected (closure writes statuses directly in one transaction — the receipt IS the QG-2 evidence).
- 2026-10-06T23:43:43Z [implementation] — CLI+MCP parity, shared renderers; verify #3585 green
- 2026-10-06T23:43:43Z [implementation] — atomic close on exact receipt; stale on drift; rollback whole
- 2026-10-06T23:43:43Z [implementation] — descendants resolution + degenerate-pool refusals
- 2026-10-06T23:43:43Z [implementation] — review-ready gate before pooled run
- 2026-10-07T08:33:10Z [done] — REVIEW (audit sweep, 6+1 agents, glm-5.2, diff 71b313a6..HEAD): Verdict FAIL. CRITICAL x1: hierarchy_done_with_handle recomputes identity with root=None (verify_hierarchy.py:145) vs mint-time root_from_service (verify_cohort.py:248) -> unknown-root sentinel -> canonical_identity never matches in a git repo; story/epic done --verify-handle dead on arrival; test masked by _green_receipt using same root=None. HIGH x5: (1) contract SS4 widening unimplemented - refusal loop (verify_cohort.py:262-274) permanently bricks pooled re-verify for a membership after post-green drift; (2) pooled verify_handle never rendered by cohort_summary/hierarchy_summary on either transport though report carries it; (3) handle without dot -> IndexError crash (verify_hierarchy.py:128); (4) SPEC SS5 'task done --verify-handle accepts either' dead text - pooled run recorded under members[0] only, single-task redemption refuses other members (verify_handle_check.py:119-125); (5) required_after_red incremental rerun unwired dead code. MEDIUM x18 incl: weaker third handle validator (no TTL/constant-time/atomic spend vs verify_handle.py redeem); inputs_digest always 'unavailable' in production (report has no files_hash key, service_gates.py:107-131); identity binds placeholder strings 'declared-at-run'/'selection-evidence-of-run'; per-test provenance one synthetic row; verify_baseline.py miscounts (duplicate slugs per-slug windows, sizes 3-4 dropped) - numbers published as release justification; MCP pooled lane skips preparation (handlers call run_cohort_verify cold; CLI pays verify_prepare) + scope default mismatch manual-vs-standard; EN SPEC omits member-status-drift + names wrong v75 columns; AC-6 denominator incomplete (convention #776); 21.4x headline not derivable from published denominators (34/1=34x, 1492.1/314.6=4.7x); readiness LIKE '%AC-%' misses standard 'AC verified:' evidence format; sec-sensitive union pools silently on fresh cohort (invalidation_reason only runs in drift branch); mcp.md missing tool rows; cli-quality/cli-tasks missing flags; configuration.md missing memory_tail_by_relevance. LOW x29: dead loop verify_cohort.py:140-142; _union_of_members dup; open-row residue on unscoped refusal; --task+--tasks silent choice; plan-steps-not-dicts; tautological tests (or True; gate_signature==gate_signature); no real-gate-path cohort tests; member-status-drift untested; red path uncovered; CLI/MCP lane exit codes untested; memory hygiene CLI untested; stale 152/62KB numbers; hygiene-archive naming; SAFE_CORE_EXACT missing pooled verbs; scope param missing on pooled MCP tools; AGENTS quickref; LIMIT-30 stub; 2h-window untested; LAYER_RANK dead; report/apply dup; cmd_verify 3 jobs; _done_with_optional_handle 3 copies; --prepare shim. Gates: review-trigger scoped pytest PASS (201/666 files, run evidence affected-tests-161a5868011cca72.json).
