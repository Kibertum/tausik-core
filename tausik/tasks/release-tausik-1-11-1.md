---
slug: release-tausik-1-11-1
title: "Release TAUSIK 1.11.1"
status: done
epic: null
story: null
complexity: medium
role: "release engineer"
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Release governance records, the complete current 1.11.1 worktree, release commit, v1-11 push, tag v1.11.1, and GitHub release."
scope_exclude: "No new product features; no closure of r111-economy-hardening-acceptance; no savings claim; no unrelated backlog work."
relevant_files:
  - AGENTS.md
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_codex.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_governance.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_opencode.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_templates.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "docs/en/cli-quality.md"
  - "docs/en/configuration.md"
  - "docs/ru/cli-quality.md"
  - "docs/ru/configuration.md"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/subagents/tausik-external-reviewer.md"
  - "harness/skills/review/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - pyproject.toml
  - release-body-1.11.1.md
  - ROADMAP.md
  - "scripts/assurance_policy.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v68.py"
  - "scripts/backend_migrations_v69.py"
  - "scripts/backend_migrations_v70.py"
  - "scripts/backend_migrations_v71.py"
  - "scripts/backend_migrations_v72.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_indexes.py"
  - "scripts/benchmark_cohort_render.py"
  - "scripts/benchmark_cohorts.py"
  - "scripts/benchmark_compare.py"
  - "scripts/benchmark_compare_cli.py"
  - "scripts/benchmark_compare_support.py"
  - "scripts/hooks/session_start.py"
  - "scripts/model_pinning.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_cli_review.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_errors.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_parser_review.py"
  - "scripts/project_parser_task.py"
  - "scripts/review_routing.py"
  - "scripts/review_separation.py"
  - "scripts/risk_l3_trigger.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/service_review_gate.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "scripts/stack_registry.py"
  - "scripts/state_assurance_parse.py"
  - "scripts/state_export.py"
  - "scripts/state_import.py"
  - "scripts/task_assurance_fields.py"
  - "scripts/task_context_package.py"
  - "scripts/task_detail_fields.py"
  - "scripts/tausik_version.py"
  - "scripts/update_check.py"
  - "scripts/usage_codex_report.py"
  - "scripts/usage_kilo.py"
  - "scripts/work_packet.py"
  - "stacks/_schema.json"
  - "stacks/ansible/stack.json"
  - "stacks/helm/stack.json"
  - "stacks/kubernetes/stack.json"
  - "stacks/terraform/stack.json"
  - "tausik/published_tags.json"
  - "tausik/tasks/release-tausik-1-11-1.md"
  - "tests/test_assurance_policy.py"
  - "tests/test_benchmark_cohorts.py"
  - "tests/test_benchmark_compare.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_claudemd_drift.py"
  - "tests/test_governance_profile.py"
  - "tests/test_publication_lines.py"
  - "tests/test_published_tags_are_promises.py"
  - "tests/test_review_routing.py"
  - "tests/test_review_separation.py"
  - "tests/test_risk_l3_trigger.py"
  - "tests/test_rules_generator_warning_parity.py"
  - "tests/test_session_host_binding.py"
  - "tests/test_session_open_handler.py"
  - "tests/test_stack_registry.py"
  - "tests/test_state_export.py"
  - "tests/test_state_import.py"
  - "tests/test_task_context_package.py"
  - "tests/test_update_check.py"
scope_paths:
  - "tausik/published_tags.json"
  - "tests/test_published_tags_are_promises.py"
scope_tools: []
assurance_profiles:
  - executable
  - migration
  - research
assurance_impact: "{\"blast_radius\":\"broad\",\"data_change\":\"non_destructive\",\"governance_boundary\":true,\"level\":\"high\",\"owner_escalation\":true,\"privileged\":true,\"reversibility\":\"conditional\",\"security_boundary\":false}"
depends_on: []
completed_at: "2026-10-04T15:36:04Z"
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

Провести проверяемый выпуск TAUSIK 1.11.1 из подготовленного состояния: аудит, финальные гейты, commit, push, tag и публикация release без заявления недоказанной экономии.

## Acceptance Criteria

AC-1 Просроченный аудит SENAR 9.5 проведён и отмечен. AC-2 Полный review и релизные проверки зелёные с явными знаменателями. AC-3 Подготовленные изменения закоммичены в ветку v1-11. AC-4 После отдельного подтверждения push ветки и тега v1.11.1 выполнен. AC-5 GitHub release 1.11.1 опубликован из release-body-1.11.1.md без заявления недоказанной экономии. Negative: при красном review, тесте, gate или несовпадении версии выпуск останавливается до исправления; публичный тег не переписывается.

## Plan

## Rollback

Before publication, revert the release commit. After public tag publication, never rewrite v1.11.1; correct defects in a new 1.11.x patch release.

## Journal

- 2026-10-04T11:46:42Z [implementation] — Release preflight: version CLI reports TAUSIK 1.11.1; release-body validation passes; SENAR v1.5 tag exists. GitLab origin and GitHub branches refreshed with --no-tags. GitHub has no v1.11.1 tag. `gh auth status` is currently red because the stored GitHub token is invalid; publication will require re-authentication. Decision #421 fixes future versioning: only 1.11.x patches before 2.0.
- 2026-10-04T11:52:52Z [implementation] — Independent deep release review read 174 files and returned FAIL: 4 CRITICAL, 0 HIGH, 1 MEDIUM. Confirmed locations: handlers_status.py:101 arbitrary caller-controlled snapshot write; review_routing.py:182 stale review record not bound to reviewed state; task_context_package.py:154 ambient-cwd config can weaken service-project review floor; state_import.py:210 malformed assurance metadata crosses import boundary and can crash package/review/closure. ROADMAP.md:15 also contradicts owner decision #421. No commit, push, tag, audit mark, or release performed.
- 2026-10-04T11:54:37Z — Full suite: 12,946 collected; 12,905 passed, 37 skipped, 0 deselected, 4 failed; 62 warnings; 488.20s. Failures: stale ruff-format legacy list (4 paths), stale-memory-ref ratchet (8 refs vs 0), DB backups (4 vs keep<=3), ship skill missing required `Subagent route (phase=code-review)` wording. pytest dedupe audit: exit 0; 282 parallel groups, 0 copies; fake-test category empty across 7,829 test functions.
- 2026-10-04T13:21:51Z — Final repair verification: canonical unfiltered suite collected 12,979 items and finished 12,941 passed, 38 skipped, 0 deselected, 0 failed, 62 warnings in 564.82s. The immediately preceding run exposed only 2 mypy gate failures in the shared benchmark helper (12,940 passed, 37 skipped); defect fix-benchmark-review-aggregation-mypy corrected the typing contract and verification_run #3494 passed. Dedupe audit remains 0 copy groups and no fake tests among 7,829 functions.
- 2026-10-04T14:02:13Z — Final repair-wave verification: full suite collected 12987; 12950 passed, 37 skipped, 0 deselected, 0 failed, 62 warnings in 493.78s. mypy: 560 source files clean. Dedupe audit: 282 parallel groups / 669 tests, 0 copy; no fake tests among 7829 functions. SENAR 9.5 audit marked after the green sweep. External review #58 findings were all repaired in six completed tasks; a fresh L3 review is still required.
- 2026-10-04T14:05:40Z — Post-full-suite hygiene repair: memory-tail truncation now strips trailing whitespace. Verify #3510 passed 210 scoped tests across 15 mapped files; git diff --check is clean after bootstrap redeploy and regeneration. The preceding full suite remains 12950 passed / 37 skipped / 0 failed; the only later runtime change is the one-line rstrip covered by #3510. Requesting a fresh different-model L3 review of the final state.
- 2026-10-04T14:19:17Z [implementation] — Release verify #3513 PASS: 8 gates passed, hadolint skipped as not applicable; scoped denominator 335/659 test files (288 direct-import), 6091 passed, 18 skipped, 81 deselected, 0 failed. Full-suite evidence remains 12950 passed / 37 skipped / 0 deselected / 0 failed. service_task_done.py is 499 lines, mypy clean, and its focused review/risk tests pass 62/62. Fresh L3 binding requested for the mechanical 503-to-499 refactor.
- 2026-10-04T15:10:43Z [implementation] — Published v1.11.1 after CI run 37209153655 completed success in lint, Linux full, macOS fast, and Windows fast. Public lightweight tag refs/tags/v1.11.1 resolves to snapshot 55dabf9320a6e33a0541556f954058a5d0674bb9; GitHub Release https://github.com/Kibertum/tausik-core/releases/tag/v1.11.1 is published, non-draft, non-prerelease from release-body-1.11.1.md. Updated the development-line published-tags promise registry in the same pass; no tag was moved or forced.
- 2026-10-04T15:23:31Z [implementation] — AC verified: 1. ✓ SENAR 9.5 audit marked after the green full sweep. 2. ✓ Full suite: 12950 passed, 37 skipped, 0 deselected, 0 failed; release verify #3514: 6100 passed, 18 skipped, 81 deselected, 0 failed, 8 gates passed, hadolint skipped; external L3 review #61: 0 critical/high/warnings. 3. ✓ Release commit b6b1c20f9ef2ac5af5227c0da83cbab9bc863c9d exists on v1-11 and origin/v1-11. 4. ✓ After separate owner confirmation, annotated development tag v1.11.1 was pushed to origin and lightweight public tag v1.11.1 was pushed to GitHub snapshot 55dabf9320a6e33a0541556f954058a5d0674bb9; no force and no tag rewrite. 5. ✓ GitHub Release TAUSIK 1.11.1 is published at https://github.com/Kibertum/tausik-core/releases/tag/v1.11.1 from release-body-1.11.1.md, draft=false, prerelease=false, with no unproved savings claim. Negative: ✓ every red finding was repaired before publication; CI run 37209153655 is success on lint, Linux full, macOS fast and Windows fast; public tag was created only after green CI and never rewritten. Postcondition: all 13 public tags match tausik/published_tags.json (9 tests passed). Rollback: development metadata can be reverted by a new commit; published tag v1.11.1 must never move; if the release needs withdrawal, mark/remove the GitHub Release while preserving the tag and publish a new 1.11.x patch.
