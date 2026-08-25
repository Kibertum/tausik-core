---
slug: l26-complexity-self-declared
title: "Complexity объявляет агент — это снимает гейты scope и rollback"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/complexity_understatement.py"
  - "scripts/service_task_done.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_complexity_understatement.py"
scope_paths:
  - "scripts/service_task_done.py"
  - "scripts/complexity_understatement.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_complexity_understatement.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-21T10:00:27Z"
---

## Goal

Все жёсткие проверки QG-0 завязаны на task.complexity in (medium, complex): требование scope_paths (gate_qg0_check.py:146-154) и rollback_plan (:173-181). Complexity объявляет САМ АГЕНТ. Объявив simple или не указав вовсе, он понижает SENAR Rule 2 и Rule 6 до предупреждений (:155-158, :182-186). Варианты решения на выбор в спайке: (а) выводить сложность из объективных признаков (число файлов в scope, размер диффа, тир) и брать максимум из объявленной и выведенной; (б) требовать scope/rollback независимо от сложности; (в) фиксировать понижение сложности как событие в телеметрии обходов (см. l26-bypass-telemetry). Негативный сценарий: попытка закрыть задачу с занижённой сложностью должна быть видимой, а не тихой.

## Acceptance Criteria

AC1: На task-done, best-effort и НЕ блокирующе, вычисляется объективный прокси сложности из числа relevant_files (файлов, которых коснулась задача).
AC2: Занижение = declared complexity ниже implied по прокси: declared 'simple'/unset и файлов > SIMPLE_MAX_FILES → implied medium+; declared 'medium' и файлов > MEDIUM_MAX_FILES → implied complex.
AC3: При занижении эмитится supervision-событие action='complexity_understated' (entity_type='supervision', переиспользует метрику l26-bypass-telemetry) с details (declared/implied/file-count) + ВИДИМОЕ предупреждение в выводе task done (msgs + report warnings).
AC4: Fail-open: ошибка вычисления/эмиссии НЕ роняет close (try/except, урок #271, отдельно от риск-блока). Честно объявленные (simple с ≤порога файлов, medium с ≤порога) — МОЛЧАТ, без ложного шума.
AC5: Тесты: understated simple→event+warning; честная simple (≤порог)→молчит; medium с малым числом файлов→молчит; understated medium→complex; complex→никогда не занижена; fail-open при ошибке эмиссии. Full suite зелёный.
AC6: Метрика supervision_bypasses уже группирует по action → 'complexity_understated' там виден; проверить рендер (или явно оформить, что это подтип надзорного события, не bypass_*).

## Plan

## Rollback

git revert коммита — изменения аддитивны (детекция + эмиссия + предупреждение на пути task-done, схема БД не меняется, лишние supervision-строки безвредны). Удаление вызова детекции возвращает прежнее поведение.

## Journal

- 2026-07-21T09:57:37Z [implementation] — АДВЕРС-РЕВЬЮ (tausik-reviewer) подтвердило транзакцию/fail-open БЕЗОПАСНЫМИ (мера #271 держится, event_add до begin_tx коммитит — прецедент стр.276). Нашло 3 находки, все исправлены: [HIGH] complexity_understated через entity_type='supervision' попадал в метрику supervision_bypasses под заголовком «bypasses» — но это ДЕТЕКЦИЯ (надзор сработал), семантически противоположно обходу. Фикс: _supervision_by_action(bypass=) разделяет метрику на bypasses (action LIKE 'bypass_%') и detections (NOT LIKE); отдельный ключ supervision_detections + отдельная секция рендера. Форма supervision_bypasses сохранена → закрытые bypass-тесты не сломаны (36 passed вместе). [MEDIUM] security-sensitive recovery обнулял relevant_files → детектор молчал для рискованной категории. Фикс: recovered_for_complexity держит список для СЧЁТА (число не течёт — событие/предупреждение логируют лишь count, не пути). [LOW] дедуп файлов перед счётом (dict.fromkeys) против ложного срабатывания на дублях. Тесты: 14 в test_complexity_understatement (чистая функция исчерпывающе + интеграция event+warning + honest-silent + fail-open + метрик-разделение). Full suite 5219 passed 0 failed.
- 2026-07-21T09:58:06Z [implementation] — AC verified: 1. ✓ complexity_understatement.understatement() считает len(dedup relevant_files) на task-done; вызов в service_task_done до begin_tx, best-effort. test_complexity_understatement.py::TestUnderstatement (исчерпывающе) 2. ✓ declared simple/unset >3 файлов→medium+; medium >10→complex. implied_complexity boundaries + rank-сравнение. TestImpliedComplexity + TestUnderstatement (unset/unknown→simple, complex-never) 3. ✓ event_add supervision/complexity_understated (details=count, не пути) + видимое COMPLEXITY UNDERSTATED в msgs+report. test_understated_simple_emits_event_and_warns 4. ✓ вложенные try/except (детекция и эмиссия раздельно fail-open, урок #271); честно объявленные молчат. test_honest_simple_is_silent + test_emit_failure_does_not_block_close 5. ✓ 14 тестов зелёные + full suite 5219 passed 0 failed. Покрыто: understated simple/medium, honest silent, complex-never, unset, fail-open 6. ✓ HIGH-ревью: метрика разделена — supervision_bypasses (LIKE bypass_%) vs supervision_detections (NOT LIKE), отдельные секции рендера. test_bypass_and_detection_counted_separately; закрытые bypass-тесты не сломаны (36 passed)
- 2026-07-21T10:00:26Z [implementation] — AC verified: 1. ✓ warn_if_understated считает len(dedup relevant_files) на task-done, best-effort. TestUnderstatement исчерпывающе 2. ✓ simple/unset >3→medium+; medium >10→complex. TestImpliedComplexity boundaries + unset/unknown→simple, complex-never 3. ✓ supervision/complexity_understated (details=count) + видимое COMPLEXITY UNDERSTATED в msgs+report. test_understated_simple_emits_event_and_warns 4. ✓ warn_if_understated best-effort (детекция+эмиссия раздельно fail-open, #271); honest→молчит. test_honest_simple_is_silent + test_emit_failure_does_not_block_close 5. ✓ 14+ тестов зелёные, full suite 5219 passed до извлечения, 45 целевых после. Extraction behavior-preserving 6. ✓ метрика разделена bypasses(LIKE)/detections(NOT LIKE), отдельные секции. test_bypass_and_detection_counted_separately; закрытые bypass-тесты целы
