---
slug: fix-pooled-verify-close-path-identity-root-handle
title: "Fix pooled-verify close path: identity root, handle surfacing, redemption parity"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: r1112-hierarchy-verify-and-atomic-close
scope: "scripts/verify_hierarchy.py (identity root, handle validation via verify_handle, TTL, atomic spend), scripts/verify_cohort.py (sec-sensitive fresh-cohort refusal, handle in cohort_summary), scripts/verify_hierarchy.py hierarchy_summary (handle render), harness/claude/mcp/project/handlers_hierarchy.py (preparation + scope parity), tests/test_verify_hierarchy.py + tests/test_verify_cohort.py (production-shaped tests)"
scope_exclude: "scripts/verify_cohort.py widening/recovery logic (separate defect task), backend migrations, gates.json surface count, SPEC/docs wording (separate docs defect task)"
relevant_files:
  - "scripts/verify_handle.py"
  - "scripts/verify_cohort.py"
  - "scripts/verify_hierarchy.py"
  - "scripts/project_cli_verify.py"
  - "harness/claude/mcp/project/handlers_hierarchy.py"
  - "harness/claude/mcp/project/tools_extra.py"
  - "tests/test_verify_cohort.py"
  - "tests/test_verify_hierarchy.py"
  - "tausik/gates.json"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-07T14:00:55Z"
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

Make the pooled-verification CLOSE path work in production: today story/epic done --verify-handle never accepts a real receipt (root=None identity recompute vs mint-time root_from_service), the handle is never printed by any transport, a dotless handle crashes with IndexError, redemption skips TTL/constant-time/atomic-spend, security-sensitive unions pool silently on fresh cohorts, and the MCP pooled lane skips the preparation the CLI pays.

## Acceptance Criteria

AC-1: story/epic done --verify-handle succeeds end-to-end in a git-backed project: verify --story mints, close consumes the SAME root-derived identity (production-shaped test with a real repo root, no _green_receipt-style fabrication). AC-2: cohort_summary/hierarchy_summary render the delegated report's verify_handle + redemption command on CLI and MCP (one shared render). AC-3: malformed handle without a dot returns the designed REFUSED line, never a traceback. AC-4: redemption reuses verify_handle.py (parse_handle/load_run_for_handle/redeem semantics: TTL, single-use atomic spend) instead of the weaker third validator. AC-5: a security-sensitive union is refused pooling on a FRESH cohort too (contract SS4), not only in the drift branch. AC-6: MCP pooled lane pays the same fixed preparation as the CLI lane and defaults the same scope. AC-7 negative: root divergence between mint and redeem sides is pinned by a test that fails if either side changes its root source.

## Plan

## Rollback

git revert of the fix commit; no schema migration involved (v75 columns unchanged); redeploy bootstrap --ide all after revert

## Journal

- 2026-10-07T13:38:32Z [implementation] — HANDOFF STATE (session #296 end). CODE COMPLETE IN WORKING TREE, NOT COMMITTED. Files touched: scripts/verify_handle.py (_RUN_COLUMNS + cohort_identity), scripts/verify_cohort.py (pooled_handle_lines + cohort_summary renders handle; sec-sensitive refusal on FRESH cohort; unscoped refusal BEFORE open_cohort - no residue; preparation INSIDE run_cohort_verify with prepare=True param; dead loop 140-142 deleted), scripts/verify_hierarchy.py (redemption rewritten: parse_handle + load_run_for_handle + hmac.compare_digest nonce + TTL + atomic redeem inside be.transaction(); identity recompute with root_from_service(svc) - THE critical fix; epic close closes its stories; hierarchy_summary renders handle), scripts/project_cli_verify.py (--task+pooled-flag conflict refused exit 2; pooled branches slimmed, prepare honored via param), harness/claude/mcp/project/handlers_hierarchy.py (scope parity, default standard), harness/claude/mcp/project/tools_extra.py (scope property on tausik_verify_cohort/tausik_verify_hierarchy + uncertain-dependency-mapping in description), tests/test_verify_cohort.py + tests/test_verify_hierarchy.py (production-shaped: _mint_identity uses root_from_service; TestProductionCloseParity class: git-root end-to-end, dotless/wrong-nonce/expired refusals, epic-stories, projection; tautologies removed; member-status-drift covered). STOPPING POINT: last run 30 passed 7 failed - ALL seven failures are the NEW correct TTL check rejecting _green_receipt's stale default ran_at=2026-10-06T00:00:00Z. FIX IS ONE LINE: in tests/test_verify_hierarchy.py _green_receipt change default ran_at to datetime.now(timezone.utc).isoformat(). NEXT STEPS IN ORDER: (1) fix ran_at default, run pytest tests/test_verify_cohort.py tests/test_verify_hierarchy.py to green; (2) measure MCP surface (tests/test_mcp_surface_ratchet.py _measure pattern) and bump gates.json mcp_surface.max_bytes with argued comment - scope property grew it past 59242; max_tools stays 149; (3) python bootstrap/bootstrap.py --ide all (+ --check zero drift); (4) .tausik/tausik verify --task fix-pooled-verify-close-path-identity-root-handle (REAL gates; declare relevant_files first: scripts/verify_handle.py scripts/verify_cohort.py scripts/verify_hierarchy.py scripts/project_cli_verify.py harness/claude/mcp/project/handlers_hierarchy.py harness/claude/mcp/project/tools_extra.py tests/test_verify_cohort.py tests/test_verify_hierarchy.py), close with --ac-verified --verify-handle; (5) commit; (6) L3 review record NOW POSSIBLE: .tausik/tausik review record --task r1112-hierarchy-verify-and-atomic-close --type L3 --critical 1 --high 5 --warnings 47 --reviewer-model glm-5.2 --author-model gpt-6-astra --reviewer-context different-model --reviewer-invocations 7 --deep --reason/--notes per payload already in this task's log; (7) .tausik/tausik audit mark (25 closures pending); THEN remaining defect tasks: fix-pooled-verify-recovery-ss4-widening-inputs (SS4 widening must RUN not refuse; surface files_hash in run_verify_for_task report - production inputs_digest always 'unavailable'; SPEC SS5 task-done-accepts-pooled either wired or deleted; per-test provenance decision; identity placeholders), fix-1-11-3-published-claims-spec-code-parity-21 (SPEC EN member-status-drift + cohort_identity column + SS3 honesty; 21.4x - publish derivation or restate 34x executions/4.7x wall in 4 surfaces - OWNER QUESTION; mcp.md tool rows; cli-quality verify --tasks/--story/--epic; cli-tasks story/epic done --verify-handle; configuration.md memory_tail_by_relevance; stale 152/62KB; verify_baseline.py miscounts: per-slug dup windows, sizes 3-4 dropped); release archaeology: epic release-1-11-2 mislabeled-done under pooled-verification title (retitle to actual content), create cut-release-tausik-1-11-3 task; then Track B 5 tasks (blocked-is-a-status-without-a-question-to-unblock-it; nothing-scans-the-installed-harness-state; four-ide-registries-collapse-into-one medium; ratchet-for-mcp-cli-surface-parity complex; agent-friction-becomes-a-filed-defect-not-a-swallowed-one complex); then r111-economy-hardening-acceptance (AC-1 byte probe vs frozen 63333B baseline per prefix-original-journal-20261002.json methodology: fresh stdio MCP tools/list minified + AGENTS.md + skill catalog, compact_tool_list=true in config; AC-2 verification_cycle_replay.py + frozen-corpus.json; AC-3 benchmark_observations exact windows of 3 natural post-change tasks, baseline median 89, threshold 40; AC-5 no synthetics); then release 1.11.3: version in scripts/tausik_version.py, [Unreleased]->[1.11.3]+date in BOTH changelogs, gen_doc_constants --write + README cells, full release verify lane WITH denominators naming deselected, commit, STOP - publication only on owner word. NO PUSH ever without owner.
- 2026-10-07T13:56:48Z [implementation] — Session #297: ran_at fix landed (_green_receipt default None -> datetime.now(timezone.utc) at call time); 7 TTL failures gone. Remaining failure was the projection TEST being wrong, not code: auto_export is opt-in per project (state.auto_export in .tausik/config.json) and _tree_root writes to <root>/tausik/ sibling of .tausik - test expected <root>/tasks with export off. Rewrote test to production shape (config switch + tausik/ paths). pytest tests/test_verify_cohort.py tests/test_verify_hierarchy.py: 37 passed. MCP surface measured 149 tools / 59602 bytes; gates.json mcp_surface.max_bytes 59242->59602 argued (scope property on the two pooled tools, AC-6 parity; count stays 149); ratchet 7 passed. bootstrap --ide all + --check: zero drift.
- 2026-10-07T14:00:32Z [implementation] — AC verified: AC-1 OK test_identity_minted_by_the_real_driver_closes_end_to_end (real git root, mint via real driver, close consumed SAME root_from_service identity). AC-2 OK test_green_summary_names_the_handle_and_its_redeemer + test_handleless_report_says_so_instead_of_staying_silent; pooled_handle_lines shared by cohort_summary/hierarchy_summary -> CLI and MCP render one implementation. AC-3 OK test_dotless_handle_is_refused_not_a_crash (REFUSED line, parse_handle None path). AC-4 OK redemption rewritten onto verify_handle.py machinery: test_wrong_nonce_is_refused_constant_time (hmac.compare_digest), test_expired_handle_is_refused (TTL), test_double_spend_refused (atomic spend in be.transaction). AC-5 OK test_refuses_security_sensitive_union_on_a_fresh_cohort (SS4: invalidation_reason runs on FRESH branch, not only drift). AC-6 OK preparation moved INSIDE run_cohort_verify(prepare=True); handlers_hierarchy.py routes scope or 'standard' (matches tausik_verify default) -> transport cannot skip or diverge; TestPreparation covers prepare both ways. AC-7 NEGATIVE OK inside production test: none_root identity asserted != minted identity - root divergence pinned on both sides. Verify: run #3606 PASS, 25/667 test files scoped, gates 8 passed/1 skipped (hadolint n/a), 525 tests passed. Handle 3606.5ea9af4d8793ed03196f71344b8c13ea.
- 2026-10-07T14:00:54Z [implementation] — Root cause (logic-error): hierarchy_done_with_handle recomputed cohort identity with root=None while mint stamped root_from_service(svc) -> canonical identity never matched in any git-backed project; the same None-root fabrication in tests (_green_receipt) masked it. Secondary: weaker third handle validator (no TTL/constant-time/atomic spend) and handle never rendered. Prevention: production-shaped tests mint through the real driver with a real repo root (TestProductionCloseParity), single redemption implementation shared with the single-task lane, handle surfaced by the shared renderers.
