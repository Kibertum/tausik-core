---
slug: mcp-metrics-answers-one-line-where-cli-prints-the-report
title: "tausik_metrics отдаёт ОДНУ строку там, где CLI печатает весь отчёт SENAR: агент судит о проекте по сводке"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "risk_metrics.py и service метрик не трогаем — их предмет вычисление, а не представление; состав и смысл метрик SENAR не меняем, только место сборки текста; verify и task_show остаются своим задачам"
relevant_files:
  - "scripts/render_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "tests/test_mcp_handlers_are_transport.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "harness/claude/mcp/project/handlers_status.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/render_metrics.py"
  - "tests/test_mcp_handlers_are_transport.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T14:14:13Z"
---

## Goal

MCP-обработчик метрик возвращает «Tasks: N/M (x%), Sessions: ...» — одну строку. CLI печатает throughput, lead time, FPSR, DER, cycle time, knowledge capture rate, dead end rate, стоимость по сложности и риск-секцию. CLAUDE.md велит агенту предпочитать MCP, то есть основной читатель метрик видит наименьшую их часть. Схлопнуть в один рендерер: cmd_metrics печатает построчно через project_cli_metrics.render_extended_metrics и risk_metrics.format_risk_section, поэтому нужна конверсия печати в список строк, а не перенос текста. Заведено из one-implementation-per-command-mcp-over-cli: там снят инвентарь (17 вторых реализаций, 13 схлопнуто), эта осталась как объявленный остаток, а не как незамеченная.

## Acceptance Criteria

AC-1 (одна реализация): отчёт метрик собирается ОДНОЙ функцией, возвращающей строки, и её зовут обе поверхности. cmd_metrics печатает её вывод, обработчик MCP отдаёт его же. Никакой печати внутри сборщика — иначе поверхность MCP не сможет его использовать, что и было причиной второй реализации.
AC-2 (потеря закрыта): tausik_metrics отдаёт то же, что печатает CLI, — throughput, lead time, FPSR, DER, cycle time, knowledge capture rate, dead end rate, стоимость по сложности и риск-секцию, — а не одну строку сводки. Доказано ПРОГОНОМ обеих поверхностей на одной БД со сверкой вывода, а не чтением кода.
AC-3 (храповик сжат): tausik_metrics удалён из базовой линии tests/test_mcp_handlers_are_transport.py, и test_the_baseline_only_shrinks это требует.
AC-4 NEGATIVE (пустой проект не даёт ни падения, ни ложного отчёта): на БД без задач и сессий обе поверхности отвечают ОДИНАКОВО и не бросают; величины, которых нет (lead time, cycle time), печатаются как 'n/a', а не как 0 — ноль есть утверждение о замере, которого не было. Negative: подмена 'n/a' на 0 обязана краснеть.
AC-5 NEGATIVE (секция риска недоступна): если risk_metrics не даёт сводки, отчёт выходит БЕЗ риск-секции и не роняет команду — на обеих поверхностях одинаково.
AC-6: мутации объявлены и убиты по ветви либо объявлены эквивалентными; полный прогон, mypy, ruff, bootstrap --check --ide all; CHANGELOG в обоих файлах; карта перевыпущена.

## Plan

## Rollback

git revert <commit>: изменение чисто в слое представления (сборщик строк + два вызова), схемы и данных не трогает. Откат возвращает одностроечную сводку в MCP и печать в CLI; храповик придётся вернуть tausik_metrics в базовую линию.

## Journal

- 2026-09-06T14:14:04Z [implementation] — AC verified: AC-1 (одна реализация): ✓ scripts/render_metrics.py собирает отчёт СТРОКАМИ (metrics_lines + extended_metrics_lines), печати внутри нет; cmd_metrics печатает его вывод, _handle_metrics отдаёт тот же. Перенос буквальный — каждый print стал append вместе с ведущими «\n», поэтому вывод CLI побайтово прежний. project_cli_metrics.py ужался с 331 до 148 строк, render_extended_metrics сохранён как тонкий печатник над общим сборщиком. ✓ tests/test_mcp_handlers_are_transport.py::TestBothSurfacesSayTheSameThing::test_metrics_is_the_whole_report_on_both AC-2 (потеря закрыта): ✓ tausik_metrics отдаёт весь отчёт — throughput, lead time, FPSR, DER, cycle time, knowledge CR, dead end rate, стоимость, хвосты; доказано ПРОГОНОМ обеих поверхностей на одной БД со сверкой вывода. ✓ tests/test_mcp_handlers_are_transport.py::TestBothSurfacesSayTheSameThing::test_metrics_is_the_whole_report_on_both AC-3 (храповик сжат): ✓ tausik_metrics удалён из BASELINE; замер даёт ровно ['tausik_task_show', 'tausik_verify']. ✓ tests/test_mcp_handlers_are_transport.py::test_the_baseline_only_shrinks AC-4 NEGATIVE (пустой проект): ✓ обе поверхности отвечают одинаково и не бросают; Lead Time и Cycle Time печатаются как «n/a», а не «0». Мутация Q2 («n/a» → 0) убита по ветви. ✓ tests/test_mcp_handlers_are_transport.py::TestBothSurfacesSayTheSameThing::test_metrics_on_an_empty_project_answers_rather_than_raising AC-5 NEGATIVE (риск-секция недоступна): ✓ _risk_lines и _routing_lines возвращают пустой список при любом исключении, отчёт выходит без секции и команда не падает; в parity-тестах оба хвоста monkeypatch-ятся, потому что читают МАШИНУ, а не сервис. ✓ tests/test_mcp_handlers_are_transport.py::TestBothSurfacesSayTheSameThing::_pin_machine_tails AC-6: ✓ мутаций 4, все KILLED по ветви (Q1 выбрасывание extended-хвоста — ВЫЖИЛА при первом прогоне и разобрана до конца: parity слеп к содержанию, добавлена проверка присутствия секции; Q2 n/a→0; Q3 обработчик возвращает первую строку; плюс перепроверка Q1). Мутатор удалён сразу. Полный прогон 9100 passed / 27 skipped, mypy Success 354 файла, ruff All checks passed, bootstrap --check без дрейфа после --ide all; CHANGELOG в обоих файлах. Domain: агент, читающий метрики через MCP, теперь видит те же числа, по которым судят проект в CLI, — включая FPSR и DER, по которым он судит сам себя.
