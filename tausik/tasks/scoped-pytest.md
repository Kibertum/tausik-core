---
slug: scoped-pytest
title: "Сузить scoped pytest по доказательным краям без потери честности"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: verify-certifies-a-run-that-touched-no-test-of-the-subject
scope: "scripts/gate_test_resolver.py; scripts/gate_command_runner.py; tests/test_gate_test_resolver_crosscutting.py; tests/test_gate_command_runner.py; tests/test_gate_test_resolver_import_edge.py; task metadata only"
scope_exclude: "Do not raise command-gate timeout, broaden to transitive imports, weaken scope-honesty/receipt controls, edit release metadata, tag, push or publish."
relevant_files:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_command_runner.py"
  - "tests/test_gate_test_resolver_crosscutting.py"
  - "tests/test_gate_command_runner.py"
  - "tests/test_gate_test_resolver_import_edge.py"
  - "tests/test_crosscutting_registry.py"
scope_paths:
  - "scripts/gate_test_resolver.py"
  - "scripts/gate_command_runner.py"
  - "tests/test_gate_test_resolver_crosscutting.py"
  - "tests/test_gate_command_runner.py"
  - "tests/test_gate_test_resolver_import_edge.py"
  - "tests/test_crosscutting_registry.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить измеренный блокер release 1.9: задача с пятью relevant_files выбирает 71/521 тест из-за широкого CROSSCUTTING_SCOPE=[scripts/] и не укладывается в бюджет verify. Выборщик должен различать доказательные причины включения теста, ограничивать широкий declared-scope маршрут без скрытия прямого subject-покрытия и сохранять безопасный отказ, если проверить предмет невозможно.

## Acceptance Criteria

1. Есть воспроизводимый тест: широкий CROSSCUTTING_SCOPE=['scripts/'] не раздувает scoped run для небольшого набора файлов до всего дерева, но тесты с direct import/basename для предмета остаются. 2. Отчёт SCOPE показывает происхождение/ограничение выбранного набора так, чтобы не выдавать его за полный охват. 3. Явно объявленные узкие CROSSCUTTING_SCOPE и CROSSCUTTING_SCOPE=[] сохраняют существующую семантику. 4. Нет транзитивного import expansion, повышения timeout, ослабления scope-honesty или исключения незадекларированных файлов. 5. Focused pytest, mypy, ruff, dedupe и signed verify зелёные; при невозможности зелёной верификации причина и измерение записаны, задача не закрывается.

## Plan

[{"step": "Measure each resolver edge contributing to the 71-file scoped selection and identify the smallest honest policy boundary.", "done": true}, {"step": "Define and test an explicit treatment for broad declared scopes that preserves direct, basename and narrow declared coverage.", "done": false}, {"step": "Implement source-aware selection and transparent SCOPE disclosure without expanding imports or time limits.", "done": false}, {"step": "Run focused behavior tests plus mypy, ruff and dedupe; record before/after selection counts.", "done": false}, {"step": "Run signed verify; close only if it certifies the declared task scope.", "done": false}]

## Rollback

git revert the selector provenance/budget change.

## Journal

- 2026-09-10T12:50:25Z [implementation] — Measurement: for the five-file predecessor scope, basename selects 4 tests, direct imports 17, declared scopes 40, observed 0, union 55 before test-file-induced scope expansion; 35 test modules declare bare scripts/ (some together with other roots). Formal verify selected 71/521 and timed out after 34.7s. The broad declarations are the dominant source, not direct imports.
- 2026-09-10T12:53:31Z [implementation] — Independent full-lane blocker reproduced deterministically: tests/test_crosscutting_registry.py::TestCrosscuttingVisibility::test_new_tree_iterator_must_declare_or_optout fails because tests/test_subagent_reviewer.py iterates a source tree without CROSSCUTTING_SCOPE or explicit []. This is a pre-existing registry-contract defect, not evidence for changing selector semantics; it is queued as the next short task.
- 2026-09-10T12:56:56Z [implementation] — Clean repeat verify #2395 confirms real policy/cost failure: 66/521 selected, only 10% completed in 27.7s. Decision for implementation: preserve direct-import, basename and narrow declared-path edges; treat declarations at whole top-level source-tree breadth (e.g. scripts/) as deferred global checks, disclose their count in SCOPE, and do not let them alone certify a no-subject change. This neither raises timeout nor claims deferred checks ran.
- 2026-09-10T13:01:19Z [implementation] — Fresh source entrypoint (python scripts/project.py verify) validates new policy: selected 28/521, direct-import subject tests=17, deferred global tree checks=40, versus 66 before. It still times out after 13.4s at 28%, so selection reduction alone is insufficient. Next design: execute the preserved scoped set in bounded subprocess batches; do not raise per-command timeout or discard subject tests.
- 2026-09-10T13:07:49Z [implementation] — Fresh source verify #2400: PASS ruff+pytest, 28/521 in 20.5s, 40 deferred global guards disclosed; handle not used because git-mismatch. Authorized commit attempt was correctly blocked: resolver is 559>500 lines, test-dedupe grew 322/753→323/755, and state_roundtrip requires two task exports owned by other work. No commit created; do not stage foreign task files.
- 2026-09-11T12:41:19Z [implementation] — Возобновлено после снятия формального prerequisite: registry-contract tree reviewer исправлен в 173f0249. Resolver/batched execution уже в 8422b977. Новое измерение требуется потому что verify-dynamic-state выбирает 73 теста: direct imports verify_scope_honesty тянут широкий proof-suite; задача selector должна доказать bounded execution и точный SCOPE без выдачи narrowed run за full suite.
- 2026-09-11T12:46:25Z [implementation] — Новая выборка для relevant_files verify-dynamic-state текущим source resolver: 36 тестовых модулей (4 direct-import, 40 global guards deferred; overlap снижает union). Это честнее прежних 73 MCP-stale. Batches 1 и 2 по 12 прошли: 248 passed in 8.05s; 237 passed in 7.76s. Последняя партия (service/verify proof suite) с xdist доходит до 96% и остаётся живой после transport window; без xdist спустя 30s лишь 38%. Два подтверждённых зависших дочерних pytest процесса от непредъявимых повторов остановлены. Не менять batch size до профилирования конкретного тяжёлого модуля: уменьшение может не помочь, если один модуль сам длинный.
- 2026-09-11T12:50:17Z [implementation] — Fresh source verify #2407 after e1043053: ruff=PASS, pytest=PASS in 42.516s with four-file bounded batches; signed run has handle nonce but receipt is under-declared solely on historical paths scripts/verify_commit_ownership.py, tests/test_verify_commit_ownership.py, tests/test_subagent_reviewer.py and a framework dead-end memory projection. These were committed under overlapping/no same-commit task exports, so current fail-closed ownership intentionally cannot subtract them. Do not consume the handle or close.
