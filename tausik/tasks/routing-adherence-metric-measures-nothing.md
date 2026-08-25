---
slug: routing-adherence-metric-measures-nothing
title: "Routing Adherence 1.6% на n=10909: метрика фиксирует «нарушение» правила, которое невыполнимо"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/project_cli_ops.py (переформулировать презентацию метрики), scripts/model_routing_adherence.py (докстринг-семантика), tests/"
scope_exclude: "Не менять record_adherence/aggregate_adherence data-ключи (pct/n/top_deviations) — существующие тесты и данные; не удалять сбор данных (это калибровка)"
relevant_files:
  - "scripts/project_cli_ops.py"
  - "scripts/model_routing_adherence.py"
  - "tests/test_routing_adherence.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T23:17:02Z"
---

## Goal

Аудит сессии #132 (SENAR Rule 9.5). `tausik metrics` показывает Routing Adherence 1.6% при n=10909, из них `deviation sonnet->opus: 10739`. Метрика, сообщающая о нарушении правила в 98.4% случаев, не измеряет нарушение — она измеряет, что правило невыполнимо. И это подтверждено собственной документацией: bootstrap_templates.WORKFLOW прямо пишет, что Claude Code НЕ переключает модели программно и рекомендацию надо применять руками через IDE-picker. То есть фреймворк рекомендует Sonnet для medium-задачи, сессия идёт на Opus (сознательный выбор пользователя), и это записывается как отклонение — десять тысяч раз. Три следствия: (1) сигнал 10739 строк маскирует те случаи, где отклонение действительно значимо; (2) число попадает в метрики релиза и выглядит как провал дисциплины, которым не является; (3) любой, кто попробует «починить» adherence, будет чинить не то. Решить: считать adherence только там, где переключение реально возможно и заявлено; либо переименовать в «дельта рекомендации» без коннотации нарушения; либо перестать писать строку, когда активная модель равна модели сессии по конфигу. Требуется решение о ЗНАЧЕНИИ метрики, поэтому role=architect.

## Acceptance Criteria

AC1. РЕШЕНИЕ (role=architect): метрика переформулирована из 'adherence/deviation' (коннотация нарушения) в 'recommendation fit' (калибровка). Обоснование: программное переключение модели недоступно (Claude Code, bootstrap WORKFLOW), модель фиксирована на сессию выбором пользователя → recommended≠actual это НЕ нарушение дисциплины, а данные о соответствии рекомендации реальности. Выбор reframe (не suppress-rows и не count-only-switchable) задокументирован в tausik_decide.
AC2. Презентация `tausik metrics` больше НЕ содержит слов 'Adherence'/'deviation' в смысле нарушения; добавлена строка-пояснение, что выбор модели — per-session/вручную (IDE picker), поэтому разрыв это калибровка, а не провал дисциплины.
AC3. Данные не тронуты: record_adherence/aggregate_adherence ключи (match/pct/n/top_deviations) сохранены; tests/test_routing_adherence.py зелёные.
AC4. Докстринг model_routing_adherence.py проясняет семантику (recommendation-fit дельта, не compliance; переключение вручную).
AC5. НЕГАТИВ/граничные: при n==0 (нет данных) секция вообще не печатается (отсутствие данных не рождает ложный 0%-провал); при отсутствии top_deviations строка разрывов не печатается. Тест на новую презентацию: вывод содержит нейтральную формулировку + пояснение, НЕ содержит 'violation'-фрейминга.

## Plan

## Rollback

git revert; изменение — переформулировка презентации + докстринг, данные не тронуты. Откат возвращает 'adherence/deviation' формулировку.

## Journal

- 2026-07-26T23:17:01Z [implementation] — AC-1: ✓ РЕШЕНИЕ #183 (reframe, не suppress/count-only) — задокументировано в tausik_decide #183 + докстринге. Обоснование: программное переключение недоступно (bootstrap WORKFLOW), модель фиксирована выбором пользователя. AC-2: ✓ Презентация без 'Adherence'/'deviation'-нарушения — tests/test_routing_adherence.py::TestRecommendationFitPresentation::test_framing_is_fit_not_violation ('adherence'/'deviation' отсутствуют, 'recommendation fit' + 'per-session' + 'not switched programmatically' присутствуют, данные 1.6%/10909/sonnet->opus сохранены). AC-3: ✓ Данные не тронуты — record_adherence/aggregate_adherence ключи (match/pct/n/top_deviations) сохранены; все существующие TestRecord/TestAggregate/TestTaskDoneIntegration зелёные (16 passed). AC-4: ✓ Докстринг model_routing_adherence.py проясняет: recommendation-fit дельта, не compliance, переключение вручную (bootstrap WORKFLOW, decision #183). AC-5: ✓ НЕГАТИВ — test_empty_sample_prints_nothing (n==0/None → '' , нет ложного 0%-провала) + test_no_deviation_line_when_no_gaps (нет разрывов → строка не печатается). Формула вынесена в чистую format_recommendation_fit (тестируемо). mypy 2 файла Success. Domain: метрика перестала называть невыполнимое правило нарушением на 98.4% (10739 строк маскировали значимые случаи) — класс #306 (прокси-метрика не должна штрафовать делопроизводство). verification_run #1464 scoped pytest PASS. CHANGELOG EN+RU + decision #183.
