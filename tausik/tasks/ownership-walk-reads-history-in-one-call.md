---
slug: ownership-walk-reads-history-in-one-call
title: "Обход владения читает историю одним git log и пропускает коммиты без проверяемых путей"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: verify-uses-commit-history-as-task-diff
scope: "Только сбор списка коммитов и файлов внутри foreign_completed_paths_since и тест счётчика вызовов."
scope_exclude: "Не менять ярусы и правила владения, не трогать hang guard, faulthandler_timeout, selector, не релизить."
relevant_files:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/verify_commit_ownership.py"
  - "tests/test_verify_commit_ownership.py"
  - "tausik/tasks/ownership-walk-reads-history-in-one-call.md"
  - "tausik/stories/release19-proof-integrity.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:19:31Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР, смена #244: tests/test_service_verification.py::TestRunGatesWithCacheGitDiffIntegration::test_cache_hit_when_declared_matches_changes идёт 168-190 с (и на версии 8c63c76c — 172 с), потому что foreign_completed_paths_since делает git diff-tree на каждый из 630 коммитов с 2026-04-28 и git show на каждый task export в каждом коммите, хотя проверяемый набор — один путь scripts/foo.py. Hang-guard (порог 150 с при faulthandler_timeout=300) возвращает rc=1 партии scoped pytest, и подписанный verify задач, чей scope тянет этот файл, получает FAIL при 213 зелёных тестах. Переписать обход: один вызов git log --since --format=%x01%H --name-only даёт коммиты с их файлами; коммит без пересечения с changed_paths пропускается целиком; git show экспортов и git grep parent-tree выполняются только для коммитов с проверяемыми путями. Семантика решения владельца не меняется.

## Acceptance Criteria

AC-1: foreign_completed_paths_since issues exactly one git log for the window and no git diff-tree; a runner-counting test proves a commit touching none of changed_paths triggers no git show and no git grep. AC-2 (negative): a commit that does touch an inspected path still reads its exports — all 22 existing real-git ownership tests stay green unchanged. AC-3 (negative boundary): a git log failure still returns the empty set (safe degradation), and a malformed commit header line is ignored rather than mis-parsed. AC-4: test_cache_hit_when_declared_matches_changes measured under 10 s (was 168-190 s); the scoped batch containing tests/test_service_verification.py exits 0 under the hang guard. AC-5: ruff, mypy, dedupe without new groups, signed verify; CHANGELOG EN/RU entry.

## Plan

[{"step": "\u041e\u0434\u0438\u043d git log --name-only \u0441 \u0440\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u0435\u043b\u0435\u043c %x01 \u0432\u043c\u0435\u0441\u0442\u043e diff-tree \u043d\u0430 \u043a\u043e\u043c\u043c\u0438\u0442; \u043f\u0440\u043e\u043f\u0443\u0441\u043a \u043a\u043e\u043c\u043c\u0438\u0442\u043e\u0432 \u0431\u0435\u0437 inspected", "done": true}, {"step": "\u0422\u0435\u0441\u0442 \u0441\u043e \u0441\u0447\u0438\u0442\u0430\u044e\u0449\u0438\u043c runner: \u043d\u0435\u0442\u0440\u043e\u043d\u0443\u0442\u044b\u0439 \u043a\u043e\u043c\u043c\u0438\u0442 \u043d\u0435 \u043f\u043e\u0440\u043e\u0436\u0434\u0430\u0435\u0442 git show/git grep", "done": true}, {"step": "\u0417\u0430\u043c\u0435\u0440 \u043c\u0435\u0434\u043b\u0435\u043d\u043d\u043e\u0433\u043e \u0442\u0435\u0441\u0442\u0430 \u0438 \u043f\u0430\u0440\u0442\u0438\u0438 \u043f\u043e\u0434 hang guard; ruff, mypy, dedupe, signed verify; CHANGELOG", "done": true}]

## Rollback

git revert одного коммита; возвращается пер-коммитный diff-tree.

## Journal

- 2026-09-12T13:19:05Z [implementation] — Root cause (performance): foreign_completed_paths_since enumerated commits with git log, then ran git diff-tree per commit and git show per export in every commit, regardless of whether the commit touched any inspected path; the cost scaled with window length × exports, not with the receipt's scope. Prevention: one git log --name-only for the window, commits without inspected paths are skipped, and a runner-counting test pins that an untouched commit costs no git show/grep.
- 2026-09-12T13:19:06Z [implementation] — AC verified: AC-1 ✓ test_a_commit_touching_no_inspected_path_costs_no_git_show — seen == ['log'], no diff-tree, no show, no grep. AC-2 ✓ test_a_commit_touching_an_inspected_path_still_reads_its_exports — foreign.py owned, 'show' present, 'diff-tree' absent; the 22 pre-existing real-git tests unchanged and green (27/27). AC-3 ✓ Negative: git log failure → _git_text None → empty set (existing degradation path); test_malformed_history_yields_no_commits[empty|malformed-header|orphan-paths]. AC-4 ✓ test_cache_hit_when_declared_matches_changes 168.0 s → 0.59 s; gate batch [test_service_verification, test_tausik_service, test_v131_blind_review, test_verify_cache_empty_scope] 195 s/rc=1 → 6.9 s/rc=0, no HEADROOM line. AC-5 ✓ ruff, mypy clean; dedupe 322 groups unchanged; CHANGELOG EN/RU; signed verify below. Domain: the receipt's cost now scales with what it inspects, so a task started in April costs the same as one started today.
