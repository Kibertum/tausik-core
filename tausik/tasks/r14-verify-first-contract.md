---
slug: r14-verify-first-contract
title: "Verify-First Contract: separate task_done from heavy gates (root-cause fix for VS Code hangs)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: complex
role: null
stack: null
tier: substantial
call_budget: 150
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:17:39Z"
---

## Goal

Release 1.4 readiness: r14-verify-first-contract

## Acceptance Criteria

1. Триггер `verify` добавлен в VALID_GATE_TRIGGERS. 2. pytest и все subprocess-гейты переведены на trigger=verify в default_gates+stacks/*. 3. task_done запускает только cheap-гейты (filesize, tdd_order) и проверяет наличие свежего verify_run в кеше; иначе блокирует с понятной ошибкой. 4. Опция config.task_done.auto_verify (default false) для opt-in старого поведения. 5. Доки обновлены, тесты добавлены.

## Plan

## Rollback

## Journal

- 2026-04-30T23:48:57Z [planning] — Step 1-5 done: VALID_GATE_TRIGGERS extended; pytest/tsc/cargo/phpstan/javac/js-test/terraform/helm/kubeval/hadolint/ansible-lint stack gates moved from task-done to verify trigger; service_verification gained has_fresh_verify_run + parameterized run_gates_with_cache; service_gates._enforce_verify_first added with auto_verify opt-out; CLI verify and MCP _handle_verify use trigger=verify.
- 2026-05-01T00:17:15Z [planning] — AC: 1. task_done returns instantly when verify cache exists - verified by test_fresh_verify_run_unblocks. 2. task_done blocks with explicit remediation when no verify run - verified by test_no_verify_run_blocks + test_block_message_points_to_remediation. 3. tausik verify writes verification_runs row with trigger=verify cache key - verified by test_task_done_bucket_does_not_satisfy_verify_first. 4. config.task_done.auto_verify=true preserves legacy inline behavior - verified by TestAutoVerifyOptOut (pass + fail variants). 5. Negative scenario - cache mismatch (different trigger bucket) does not satisfy enforcement - verified by TestCacheBucketSeparation. 6. Empty verify trigger config skips enforcement (small projects) - verified by TestNoVerifyGatesProjectIsExempt.
- 2026-05-01T00:17:15Z [planning] — All steps complete: VALID_GATE_TRIGGERS+verify, 12 stack JSONs migrated, service_verification has_fresh_verify_run + parameterized trigger, service_gates _enforce_verify_first with auto_verify opt-out, CLI verify + MCP _handle_verify trigger=verify, conftest opt-out fixture for legacy tests, verify_first marker registered, 14 dedicated tests in test_verify_first_contract.py, docs updated (cli.md/quickstart.md/CHANGELOG/ship+task skills/bootstrap_templates HARD_CONSTRAINTS/SENAR_RULES/COMMANDS/QUALITY_GATES), .claude/mcp mirror synced. Full suite: 2313 passed, 7 skipped (pre-existing bootstrap detection issue is unrelated).
