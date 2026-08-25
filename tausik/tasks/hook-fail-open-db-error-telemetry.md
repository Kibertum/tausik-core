---
slug: hook-fail-open-db-error-telemetry
title: "Телеметрия молчаливого fail-open: task_gate/scope_write_gate пропускают правку при ошибке БД"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/_common.py (extract _emit_supervision + emit_supervision_degradation), scripts/hooks/task_gate.py, scripts/hooks/scope_write_gate.py, scripts/backend_queries_metrics.py (3-way category), scripts/project_cli_metrics.py (render), tests/"
scope_exclude: "gate_verify_first.py (отдельный inline bypass_auto_verify путь), task_done_verify.py"
relevant_files:
  - "scripts/hooks/_common.py"
  - "scripts/hooks/hook_supervision.py"
  - "scripts/hooks/task_gate.py"
  - "scripts/hooks/scope_write_gate.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_fail_open_degradation_telemetry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-21T10:35:42Z"
---

## Goal

Найдено разведкой l26-bypass-telemetry. Помимо ЯВНЫХ переключателей обхода, есть МОЛЧАЛИВОЕ ослабление: при sqlite.Error на запросе активной задачи/ACL хуки task_gate.py (:137-138) и scope_write_gate.py (:155) по умолчанию fail-open — return 0 (пропустить правку), если не установлен TAUSIK_HOOK_FAIL_SECURE. Это неотличимо от «нечего блокировать»: транзиентная порча/локбло БД тихо снимает надзор, и никто не узнает. Задача: эмитить supervision-событие action='fail_open_db_error' (entity_id=имя хука, details=текст ошибки) в этих fail-open ветках, чтобы деградация надзора была countable, а не невидима. Использовать общий хелпер _common.emit_supervision_bypass (уже есть после l26-bypass-telemetry). Категория отдельная от bypass_* — это деградация, не намеренный обход; учесть в метрике/рендере.

## Acceptance Criteria

1. task_gate.py и scope_write_gate.py эмитят supervision-событие в fail-open ветках при sqlite.Error (и defensive Exception в task_gate), action='fail_open_db_error', entity_id=имя хука, details=текст ошибки. 2. Категория ОТДЕЛЬНАЯ от bypass_* И от detections: метрика делит supervision-события на три взаимоисключающие корзины (bypass_%, fail_open_%, остальное=detection); fail_open НЕ протекает в detections. 3. Новый supervision_degradations_summary() + ключ в get_metrics. 4. Рендер отдельной секцией 'Supervision degradations' (только при total>0). 5. Общая машинерия INSERT переиспользована (не дублирована): emit_supervision_bypass и emit_supervision_degradation зовут один _emit_supervision. 6. Fail-open остаётся fail-open: эмиссия best-effort, не меняет exit code (0), не роняет хук. 7. Тесты: обе ветки эмитят fail_open_db_error; метрика три корзины не смешиваются; detection исключает fail_open; render. Зелёный pytest.

## Plan

## Rollback

## Journal

- 2026-07-21T10:29:43Z [implementation] — Impl: _common.py — извлечён _emit_supervision (общая машинерия), emit_supervision_bypass делегирует, добавлен emit_supervision_degradation (action=fail_open_<reason>, best-effort, документирован ceiling: сток = та же БД что упала). task_gate.py: эмиссия fail_open_db_error в обеих fail-open ветках (sqlite.Error + defensive Exception). scope_write_gate.py: то же в sqlite.Error ветке. Метрика: _supervision_by_action переведён на 3 взаимоисключающие категории (bypass/degradation/detection), detection теперь ИСКЛЮЧАЕТ fail_open_% (иначе деградация маскируется под сработавший надзор). +supervision_degradations_summary + ключ get_metrics. Рендер: отдельная секция 'Supervision degradations / fail-open'.
- 2026-07-21T10:32:16Z [implementation] — Тесты: tests/test_fail_open_degradation_telemetry.py (13): emit-хелпер (1 row, no-db silent, broken-db no-raise, общий writer с bypass); три корзины изолированы + degradation НЕ протекает в detection (ключевая регрессия) + unknown category ValueError; render секции вкл/выкл; оба хука реально эмитят fail_open_db_error на сломанном чтении tasks (ALTER RENAME COLUMN на реальной схеме-оракуле, events писабельна), fail_secure блокирует и НЕ эмитит. Регрессий нет: 13 + 110 (bypass/hooks/complexity) + 120 (metrics/senar/gate) зелёные.
- 2026-07-21T10:32:32Z [implementation] — AC verified: 1. ✓ task_gate/scope_write_gate emit fail_open_db_error; test_task_gate/scope_write_gate_fail_open_emits 2. ✓ 3-way category; test_degradation_does_not_leak_into_detection 3. ✓ supervision_degradations_summary + get_metrics key; test_metrics_dict_has_degradations_key 4. ✓ render section; test_degradation_section_rendered/silent 5. ✓ _emit_supervision shared; test_shares_writer_with_bypass 6. ✓ exit 0 preserved, best-effort; test_fail_secure_blocks + broken_db_never_raises 7. ✓ verify #1150 pytest PASS; 13+230 green
- 2026-07-21T10:35:40Z [implementation] — AC verified: 1. ✓ both hooks emit fail_open_db_error; test_task_gate/scope_write_gate_fail_open_emits 2. ✓ 3-way category, no leak; test_degradation_does_not_leak_into_detection + test_each_bucket_isolated 3. ✓ supervision_degradations_summary + get_metrics key; test_metrics_dict_has_degradations_key 4. ✓ render section; test_degradation_section_rendered/silent 5. ✓ _emit_supervision shared in hook_supervision; test_shares_writer_with_bypass 6. ✓ exit 0 preserved; test_fail_secure_blocks + broken_db_never_raises 7. ✓ verify #1153 pytest PASS; 13+230 green; bootstrap drift cleared all profiles
