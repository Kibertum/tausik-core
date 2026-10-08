---
slug: cheap-gates-run-after-the-expensive-one
title: "Дешёвые гейты стоят в конце: статика ловится после четырёхминутной ленты"
status: done
epic: release-110-deferred-from-19
story: release110-terse-answers
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_runner.py"
  - "scripts/gate_spec.py"
  - "scripts/gate_outcome.py"
  - "scripts/gate_registry_scoped.py"
  - "tests/test_gate_runner_phases.py"
scope_paths:
  - "scripts/gate_runner.py"
  - "scripts/gate_spec.py"
  - "scripts/gate_outcome.py"
  - "scripts/gate_registry_scoped.py"
  - "tests/test_gate_runner_phases.py"
  - "tests/test_gate_registry.py"
  - "tests/test_gate_test_dedupe.py"
  - "tests/test_config_trust.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T13:31:03Z"
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

Дешёвые проверки идут ДО дорогой, и дорогая не запускается, если дешёвая уже упала. Сейчас test_dedupe, filesize, bootstrap_drift, class_surface и doc_coverage висят на task-done, то есть срабатывают ПОСЛЕ полной ленты и scoped verify — цена срабатывания 2-3 хода и 4 минуты. Все они статические: ruff плюс dedupe плюс prose считаются 3,5 секунды. Замер смены #278: около 15 срабатываний, примерно 35 лишних вызовов из 290.

## Acceptance Criteria

1. У гейта объявлена стоимость: fast или slow; прогоны тестов — slow, статика — fast. 2. Раннер делит на две фазы: все fast прогоняются ЦЕЛИКОМ и отчитываются вместе, slow запускается только если блокирующих отказов в fast нет. 3. НЕГАТИВНЫЙ: внутри фазы отказ НЕ прерывает остальные — иначе три дефекта дадут три раунда вместо одного; проверяется тестом на трёх падающих fast-гейтах. 4. Статические гейты добавлены в триггер verify, чтобы ловиться до task done. 5. НЕГАТИВНЫЙ: ни один гейт не ослаблен и не удалён — состав и severity до и после совпадают, проверяется тестом. 6. Отчёт называет, что slow-фаза пропущена и почему. 7. Полная лента зелёная.

## Plan

## Rollback

git revert; порядок гейтов возвращается к порядку реестра, ни один гейт не удалён и не ослаблен.

## Journal

- 2026-09-29T13:29:49Z [implementation] — AC-1: ✓ gate_spec.SLOW_GATES плюс gate_cost(); тесты ::TestTheCostIsDeclaredAndComplete, включая test_every_gate_that_runs_the_project_is_declared_slow — объявленный список обязан покрывать каждый гейт, чья команда гоняет тесты или сборку. AC-2: ✓ ::TestThePhaseBoundary — четыре теста: slow не запускается при блокирующем отказе fast, запускается при зелёном fast, идёт последним, и warn-уровень границу НЕ закрывает. AC-3 НЕГАТИВНЫЙ: ✓ ::test_three_failing_fast_gates_all_report — три падающих гейта отчитываются вместе, иначе один раунд стал бы тремя.
- 2026-09-29T13:29:49Z [implementation] — AC-4: ✓ живой verify печатает ruff, filesize, ruff_format, test_dedupe, class_surface, bootstrap_drift, doc_coverage — и только потом pytest; раньше пять из них ждали task done. AC-5 НЕГАТИВНЫЙ: ✓ ::TestNothingWasWeakened — severity сохранены, триггер task-done остался у всех пяти. AC-6: ✓ непрогнанный тестовый гейт отчитывается COULD_NOT_RUN с причиной fast_phase_failed и текстом «не запускался: блокирующий статический гейт упал первым». AC-7: ✓ полная лента 12291 прошли, 34 пропущены. Domain: проверено на живом прогоне verify, а не только на фикстуре. Три чужих теста закрепляли прежние триггеры — каждый обновлён с причиной, ни один не ослаблен.
