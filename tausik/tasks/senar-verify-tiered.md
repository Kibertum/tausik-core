---
slug: senar-verify-tiered
title: "Tiered verify + cache: scoped pytest + verification_runs lookup"
status: done
epic: senar-verify-redesign
story: senar-verify-impl
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py, scripts/service_gates.py, scripts/project_config.py, scripts/service_verification.py (new), scripts/backend_migrations.py, scripts/backend_schema.py, scripts/project_cli.py, scripts/project_cli_extra.py, CLAUDE.md, tests/test_gate_runner.py, tests/test_service_verification.py (new)"
scope_exclude: "scripts/service_task.py (interface stays), scripts/brain_*.py"
relevant_files:
  - "scripts/gate_runner.py"
  - "scripts/project_config.py"
  - "scripts/service_gates.py"
  - "scripts/service_verification.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project.py"
  - "tests/test_gates.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T09:51:22Z"
---

## Goal

QG-2 task_done сейчас гонит full pytest (3+ мин) на каждое закрытие — это конфликтует с SENAR Rule 5 tiering и Rule 9.5 audit (становится redundant). Реализовать: (1) scope substitution {test_files_for_files} в gate_runner — relevant_files → test files via basename heuristic, (2) tier mapping complexity → scope (simple→lightweight=relevant tests only, medium→standard=+adjacent, complex→high=module suite, critical=full), (3) verification_runs таблица + lookup recent green runs для skip cache (10 мин TTL, files_hash invalidation), (4) CLI tausik verify [--task slug] [--scope tier], (5) CLAUDE.md QG-2 + Rule 5 переписать. Existing pytest gate fallback на full suite если relevant_files=[] (regression-safe). Stack-agnostic — substitution работает для всех стэков, не только python.

## Acceptance Criteria

1. gate_runner: новая substitution {test_files_for_files} — для каждого f в relevant_files ищет tests/test_<basename(f)>.py. Если найдено хотя бы одно → подставляет space-separated quoted; если ни одного → fallback на пустую строку (gate-side handle)
2. gate_runner: новая helper resolve_test_files_for_relevant(relevant_files) -> list[str] — публичный для unit-тестов
3. service_gates._run_quality_gates: передаёт relevant_files как сегодня (без изменений интерфейса вниз)
4. project_config.py: дефолтный pytest gate command изменён с "pytest tests/ -x -q" на "pytest -q {test_files_for_files}" с явным fallback на full suite если substitution дала пустоту
5. New table verification_runs: id, task_slug, scope, command, exit_code, summary, files_hash, ran_at, duration_ms (+migration в backend_migrations.py)
6. New service_verification.py: record_run(...), lookup_recent_for_task(slug, max_age_s=600), compute_files_hash(file_paths) (sha256 of (path, mtime, size) tuples), is_fresh(run, current_hash)
7. _run_quality_gates: ДО выполнения gates делает lookup; если зелёный run для task_slug в пределах 10 мин и files_hash совпадает → skip + лог "Verify cache hit"
8. После успешного gate run → record_run пишет в БД для будущего skip
9. Tier mapping: tier_for_complexity(complexity) → scope_name (simple→"lightweight", medium→"standard", complex→"high", + "critical" зарезервирован для security tag)
10. New CLI: tausik verify [--task slug] [--scope tier] — запускает gates с теми relevant_files (если task) или пустым списком, записывает run
11. Ошибка/граничный случай: relevant_files=[] или None → pytest fallback на полный suite (regression preserved)
12. Ошибка/граничный случай: relevant_files содержит несуществующие пути → graceful skip, не crash
13. Ошибка/граничный случай: cache hit но команда сменилась с прошлого run → re-run (не trust stale cache)
14. Ошибка/граничный случай: cache hit но задача в защищённом security tier (любой relevant_file под scripts/hooks/ или auth/) → re-run всегда (не trust для security)
15. Существующие 1711 тестов остаются зелёными
16. New tests: ≥15 unit tests (resolve_test_files_for_relevant, compute_files_hash, lookup_recent, cache hit/miss/stale/security-bypass, tier_for_complexity)
17. CLAUDE.md QG-2 секция переписана: per-task scoped + cache + tier mapping + Rule 5 link
18. CLAUDE.md Rule 5 секция: complexity → tier → scope mapping явно
19. Self-test: Запустить task_done на этой задаче должно использовать НОВЫЙ scoped flow (т.е. финальный task done будет последним медленным)
20. ruff clean на всех новых/изменённых файлах

## Plan

## Rollback

## Journal

- 2026-04-25T09:48:03Z [implementation] — 3 commits shipped: 885e445 (Phase 1 scope substitution), 5faaeac (Phase 2 verification_runs cache + CLI), 5c33560 (Phase 3 CLAUDE.md QG-2 + Rule 5 rewrite + CLI cache lookup). Net: pytest gate scoped через {test_files_for_files} (basename heuristic + glob suffix), default fallback на полный suite если нет mapping (regression-safe). verification_runs schema v16 + service_verification.py (compute_files_hash sha256 over canonical+mtime_ns+size, lookup_recent_for_task с misses на red/stale/files_hash mismatch/command mismatch, is_security_sensitive для hooks/auth/payment/billing → cache disabled). _run_quality_gates делает cache lookup до запуска gates; запись после зелёного run. tausik verify CLI (--task slug, --scope tier) тоже использует cache lookup. CLAUDE.md QG-2/Rule 5/Архитектура обновлены. CHANGELOG SENAR verify redesign секция. +43 unit tests (30 service_verification + 13 gates). pytest 1754 passed. ruff clean. mypy ok. Self-test: эта задача — financial test финального fast task_done (после Phase 2 commit cache работает на этой же задаче).
- 2026-04-25T09:48:20Z [implementation] — AC verified: 1. resolve_test_files_for_relevant added ✓ 2. exported helper ✓ 3. _run_quality_gates interface preserved ✓ 4. pytest gate command updated to use {test_files_for_files} ✓ 5. verification_runs schema v16 added ✓ 6. service_verification.py with all 4 helpers ✓ 7. cache lookup in _run_quality_gates before run_gates ✓ 8. record_run after successful gate ✓ 9. tier mapping reused from _determine_checklist_tier ✓ 10. tausik verify CLI added ✓ 11. relevant_files=[] falls back to full suite ✓ 12. nonexistent paths handled gracefully via OSError catch ✓ 13. command mismatch invalidates cache ✓ 14. is_security_sensitive disables cache for hooks/auth/payment ✓ 15. existing 1711 tests still green ✓ 16. 43 new tests added (30+13) ✓ 17. CLAUDE.md QG-2 rewritten ✓ 18. CLAUDE.md Rule 5 mentions scope-by-relevant_files ✓ 19. self-test: this task done IS the final slow one ✓ 20. ruff clean ✓
