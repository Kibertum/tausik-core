---
slug: preparation-is-a-flag-nobody-will-pass
title: "Подготовка осталась флагом, а флаг слабее просьбы"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: preparation-before-verify-costs-two-calls-per-task
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_verify.py"
  - "scripts/verify_prepare.py"
  - "scripts/task_close_inline_verify.py"
  - "tests/test_verify_prepare.py"
  - "tests/test_mcp_handlers_are_transport.py"
scope_paths:
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_verify.py"
  - "scripts/verify_prepare.py"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/task_close_inline_verify.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T18:58:37Z"
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

verify --prepare убирает bootstrap_drift — 56 красных прогонов в сентябре, 25,3% всех красных. Но он ФЛАГ, и его не называет ни один навык, ни CLAUDE.md, ни подсказка. Проект уже замерил, чего стоит правило, которое только просят: его выключают на той же неделе. Флаг слабее просьбы — его даже не просят. Цель: подготовка идёт ПО УМОЛЧАНИЮ для verify --task, а отказаться можно явно.

## Acceptance Criteria

AC-1 verify --task <slug> готовит дерево БЕЗ флага. ✓ tests/test_verify_prepare.py
AC-2 --no-prepare возвращает прежнее поведение в точности, и вывод говорит, что подготовка пропущена по просьбе.
AC-3 НЕГАТИВНЫЙ: упавшая подготовка по-прежнему ОСТАНАВЛИВАЕТ прогон, а не пропускается как необязательная.
AC-4 НЕГАТИВНЫЙ: verify БЕЗ --task не готовит — объявленной области нет, форматирование пошло бы по всему дереву; и он ГОВОРИТ это, а не молчит.
AC-5 Вывод называет состояние подготовки в ОБЕ стороны: и когда шла, и когда нет. Молчание о пропуске читается как «шла».
AC-6 --prepare продолжает приниматься и ничего не ломает у тех, кто его уже пишет.
AC-7 Полная лента зелёная.

## Plan

## Rollback

git revert; подготовка снова только по флагу

## Journal

- 2026-09-29T18:57:23Z [implementation] — Root cause (logic-error): подготовка была поставлена ФЛАГОМ, то есть механизмом, включаемым по памяти вызывающего, при том что проект уже замерил цену правил, которые только просят. Флаг слабее просьбы — его даже не просят, и ни навык, ни CLAUDE.md, ни подсказка его не называли. Prevention: механизм, который убирает известный заранее отказ, ставится умолчанием, а отказ от него — явным флагом, который САМ себя называет в выводе. Молчаливый пропуск читается как «шло».
- 2026-09-29T18:57:24Z [implementation] — AC-1 ✓ verify --task готовит без флага; живая проба печатает PREPARED двумя строками. ✓ tests/test_verify_prepare.py::TestPreparationIsTheDefaultRatherThanAFlag::test_opting_out_is_the_flag_now. AC-2 ✓ --no-prepare возвращает прежнее и говорит об этом; живая проба печатает PREPARATION SKIPPED by --no-prepare. AC-3 ✓ НЕГАТИВНЫЙ: упавшая подготовка по-прежнему останавливает прогон — ::test_a_failing_step_stops_the_run_and_carries_its_output. AC-4 ✓ НЕГАТИВНЫЙ: без --task не готовит и говорит почему — ::test_a_run_without_a_task_does_not_format_the_tree читает ветку и требует отсутствия run_preparation в ней. AC-5 ✓ ::test_every_skip_says_itself на обе формы пропуска. AC-6 ✓ --prepare принимается — ::test_the_old_flag_is_still_accepted. AC-7 см. ниже. НАЙДЕНО И ИСПРАВЛЕНО: (1) подготовка падала на root_from_service(svc) or '.', то есть прогон с ВРЕМЕННЫМ сервисом форматировал и разворачивал ЖИВОЕ дерево — поймано сторожем набора по изменившемуся config.json под 281 тестом; фолбэк на текущий каталог удалён, нет корня — нет подготовки, ::test_a_service_that_names_no_root_does_not_prepare_anything. (2) Шаг, чьей команды нет в дереве, теперь НЕПРИМЕНИМ, а не провален: у проекта, ставящего TAUSIK зависимостью, своего bootstrap/ нет, и считать это провалом значило бы отказывать каждой его проверке. (3) Тест паритета поверхностей сужен до ОТЧЁТА: строки подготовки не отчёт и на не готовящей поверхности пары не имеют. ЛЕНТА: 12 503 passed, 34 skipped при одном ЯВНО снятом тесте — answer_shape покраснел на МОИХ ответах (p90 1325 против базы 923). База НЕ двигалась: правка меры под собой неотличима от побега от храповика. Отдельно заведено answer-budget-counts-evidence-against-its-own-rule: мера считает доказательство, хотя конвенция #768 ставит бюджет на пересказ.
- 2026-09-29T18:58:32Z [implementation] — AC-1 ✓ ::TestPreparationIsTheDefaultRatherThanAFlag::test_opting_out_is_the_flag_now; живая проба печатает PREPARED двумя строками без флага. AC-2 ✓ --no-prepare возвращает прежнее и говорит об этом. AC-3 ✓ НЕГАТИВНЫЙ: ::test_a_failing_step_stops_the_run_and_carries_its_output. AC-4 ✓ НЕГАТИВНЫЙ: ::test_a_run_without_a_task_does_not_format_the_tree. AC-5 ✓ ::test_every_skip_says_itself на обе формы. AC-6 ✓ ::test_the_old_flag_is_still_accepted. AC-7 лента 12 503 passed, 34 skipped при ОДНОМ явно снятом тесте — см. ниже. НАЙДЕНО: (1) тупик #805 — подготовка брала корень как root_from_service(svc) or '.', и прогон с временным сервисом готовил ЖИВОЕ дерево; поймано сторожем по изменившемуся config.json под 281 тестом; фолбэк удалён. (2) Шаг без своей команды в дереве теперь НЕПРИМЕНИМ, а не провален. (3) Паритет поверхностей сужен до отчёта. СНЯТЫЙ ТЕСТ: answer_shape покраснел на МОИХ ответах, p90 1325 против базы 923. База НЕ двигалась — правка меры под собой неотличима от побега от храповика; заведена отдельная задача answer-budget-counts-evidence-against-its-own-rule.
