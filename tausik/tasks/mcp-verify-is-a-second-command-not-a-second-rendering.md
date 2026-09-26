---
slug: mcp-verify-is-a-second-command-not-a-second-rendering
title: "tausik_verify — вторая РЕАЛИЗАЦИЯ команды, а не второй рендеринг: квитанция, дескриптор и код выхода живут только в CLI"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "service_verification.py, gate_runner.py и подпись квитанций не трогаем — их предмет исполнение и запись, а не текст; кэш и одноразовость дескриптора не меняем; task_show остаётся своей задаче"
relevant_files:
  - "scripts/render_verify.py"
  - "scripts/project_cli_verify.py"
  - "scripts/mcp_handler_shape.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "tests/test_mcp_handlers_are_transport.py"
  - "tests/test_cli_verify_guards.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/render_verify.py"
  - "scripts/project_cli_verify.py"
  - "scripts/mcp_handler_shape.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "tests/test_mcp_handlers_are_transport.py"
  - "tests/test_project_mcp.py"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_mcp_verify_handler.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-06T14:32:22Z"
resolution: null
resolution_reason: null
---

## Goal

Ветка CLI `verify` объявляет relevant_files, обрабатывает попадание в кэш, печатает квитанцию и одноразовый verify-дескриптор и завершается кодом выхода; обработчик MCP возвращает текстовый блок со своей сводкой и своими NOTE. Это не рендеринг, который можно вынести, — это разные команды под одним именем, и схлопывание есть перепроектирование того самого пути, через который проходит закрытие по QG-2. Поэтому вынесено отдельной задачей, а не сделано наполовину. Заведено из one-implementation-per-command-mcp-over-cli (инвентарь: 17 вторых реализаций, 13 схлопнуто, эта объявлена остатком).

## Acceptance Criteria

AC-1 (одна реализация отчёта): тело отчёта verify — заголовок, результаты гейтов, длительность, все заметки, строка записи, квитанция и дескриптор — собирается ОДНОЙ функцией, возвращающей строки, и её зовут обе поверхности. В CLI остаётся только принадлежащее CLI: разбор argparse, объявление relevant_files и код выхода; в обработчике MCP — только конверт ошибки.
AC-2 (объединение по ЗАМЕРУ, а не перенос в одну сторону): MCP получает то, чего у него не было, — длительность, заметку no-tests-declared, заметку о НЕДООБЪЯВЛЕННОЙ области, строку 'Recorded verification_run #N' либо причину её отсутствия (включая случай, когда запись не удалась и прогон не удостоверяет ничего), строку квитанции с различением 'ключа нет' и 'ключ есть, подпись не удалась'. CLI получает то, чего не было у него, — агрегированную заметку о ПРОПУЩЕННЫХ гейтах и заметку об отсутствии объявленной области. Дескриптор у MCP БЫЛ (премиса задачи в этой части неверна, исправлено в журнале) — он остаётся, но печатается общим кодом.
AC-3 (попадание в кэш перестаёт выглядеть пустым прогоном): при cache_hit MCP говорит, что прогон взят из кэша, с номером и временем, а не печатает заголовок и пустой список гейтов. Сегодня это молчаливое 'ничего не исполнилось' — дефект того же класса, ради которого задача заведена.
AC-4 (храповик сжат): tausik_verify удалён из базовой линии tests/test_mcp_handlers_are_transport.py; в ней остаётся только task_show.
AC-5 NEGATIVE (провал остаётся провалом): при красном гейте CLI выходит с кодом 1, а обе поверхности печатают отказ; ни одна не ставит слово PASSED рядом с признанием, что запись не состоялась. Мутация, снимающая SystemExit(1), обязана краснеть.
AC-6 NEGATIVE (пропущенный гейт неотличим от пройденного — запрещено): заметка о SKIP присутствует на ОБЕИХ поверхностях; мутация, убирающая её, краснеет. Исторический дефект: обработчик печатал список ИМЁН гейтов, и агент читал 'pytest' как 'тесты прогнаны'.
AC-7: мутации объявлены и убиты по ветви либо объявлены эквивалентными; полный прогон, mypy, ruff, bootstrap --check --ide all; CHANGELOG в обоих файлах; карта перевыпущена.

## Plan

## Rollback

git revert <commit>: изменение в слое представления verify (общий сборщик строк + два вызова). Схему, кэш, подпись квитанции и логику гейтов не трогает — run_verify_for_task остаётся как есть. Откат возвращает две реализации отчёта и возвращает tausik_verify в базовую линию храповика.

## Journal

- 2026-09-06T14:19:25Z [implementation] — ПРЕМИСА ЗАДАЧИ ЧАСТИЧНО НЕВЕРНА, ИСПРАВЛЯЮ ДО РАБОТЫ. Я написал в AC-2, что MCP не отдаёт одноразовый дескриптор и потому агент на MCP не может закрыть задачу по QG-2. ЭТО НЕ ТАК: handlers_verification._handle_lines отдаёт «HANDLE: <дескриптор> (valid until ..., single use)» и прямо говорит передать его в tausik_task_done. Проверено чтением, а не памятью. ЗАМЕР РЕАЛЬНОЙ РАЗНИЦЫ, ПО ОБЕ СТОРОНЫ. Чего нет у MCP: длительность прогона; заметка verify_zero_gate.verdict_note для status=no-tests-declared; заметка о НЕДООБЪЯВЛЕННОЙ области (scope_description == under-declared); строка «Recorded verification_run #N» либо причина её отсутствия (включая RECORD_FAILED_STATUS, где CLI прямо говорит, что прогон НИЧЕГО не удостоверяет); строка квитанции целиком, вместе с различением «ключа нет» и «ключ есть, но подпись не удалась»; и ВЕСЬ путь попадания в кэш — при cache_hit сервис возвращает пустые results, а обработчик MCP всё равно печатает заголовок и пустой список гейтов, то есть попадание в кэш выглядит как прогон, в котором не исполнилось ничего. Чего нет у CLI: агрегированная заметка о ПРОПУЩЕННЫХ гейтах (у CLI только [SKIP] в построчном выводе); заметка «no relevant_files declared»; заметка о полном прогоне без области. ВЫВОД: схлопывание — это ОБЪЕДИНЕНИЕ, а не перенос текста в одну сторону, и cache_hit на стороне MCP — самостоятельный дефект того же класса (молчаливое «ничего не исполнилось»). AC-2 переписываю под замер.
- 2026-09-06T14:23:21Z [implementation] — ДЕТЕКТОР ПРИДЁТСЯ УТОЧНИТЬ, И ЭТО НЕ ПОДГОНКА ПОД ЗЕЛЁНОЕ. После схлопывания tausik_verify остался помеченным: обработчик обязан ДЕРЖАТЬ результат (report) в переменной, чтобы обернуть ошибки конвертом, и join по строкам, собранным ОБЩИМ рендерером, попадает под критерий «строит текст из результата». Это ложное срабатывание: сшивание уже готовых строк есть транспорт. Уточнение УЗКОЕ: join над ОДНИМ вызовом функции, НЕ определённой в модуле обработчиков. Локальный _fmt(rows), собранный тем же join, остаётся второй реализацией с лишней косвенностью — иначе правило само открывало бы дыру, через которую рендеринг прячется за приватным помощником. ACL расширен на scripts/mcp_handler_shape.py по замеру.
- 2026-09-06T14:32:13Z [implementation] — AC verified: AC-1 (одна реализация отчёта): ✓ scripts/render_verify.py собирает весь отчёт строками (verify_lines + cache_hit_lines, receipt_lines, handle_lines, заметки); project_cli_verify.py ужался с 271 до 95 строк и держит только argparse, объявление relevant_files и коды выхода; handlers_verification.py — с 198 до 133 и держит только конверт ошибки. ✓ tests/test_mcp_handlers_are_transport.py::TestVerifyReportIsBuiltOnce::test_both_surfaces_render_the_same_report AC-2 (объединение по замеру): ✓ MCP получил длительность, строку записи, квитанцию, §8.6(e) и заметку о недообъявленной области; CLI получил агрегированную заметку о SKIP. Дескриптор у MCP был — премиса исправлена в журнале ДО работы. ✓ tests/test_mcp_handlers_are_transport.py::TestVerifyReportIsBuiltOnce::test_the_report_carries_what_only_the_cli_used_to_say ✓ tests/test_mcp_handlers_are_transport.py::TestVerifyReportIsBuiltOnce::test_the_report_carries_what_only_the_handler_used_to_say AC-3 (кэш перестал выглядеть пустым прогоном): ✓ при cache_hit отчёт говорит «Verify cache HIT ... #N», а не печатает заголовок над пустым списком гейтов. Мутация R2 (провал в обычный путь) убита по ветви. ✓ tests/test_mcp_handlers_are_transport.py::TestVerifyReportIsBuiltOnce::test_a_cache_hit_says_where_the_answer_came_from AC-4 (храповик сжат): ✓ замер даёт ['tausik_task_show'] — один элемент, чужая задача. tausik_verify удалён из BASELINE. ✓ tests/test_mcp_handlers_are_transport.py::test_the_baseline_only_shrinks AC-5 NEGATIVE (провал остаётся провалом): ✓ CLI выходит с кодом 1 на красном прогоне; при неудавшейся записи печатается NOT RECORDED и слова PASSED рядом нет. Мутации R5 (снят SystemExit) и R3 (вердикт рядом с признанием отсутствия записи) убиты по ветви. ✓ tests/test_mcp_handlers_are_transport.py::TestVerifyReportIsBuiltOnce::test_a_red_run_exits_one_on_the_cli ✓ tests/test_mcp_handlers_are_transport.py::TestVerifyReportIsBuiltOnce::test_a_failed_write_never_prints_the_word_passed AC-6 NEGATIVE (SKIP не читается как проход): ✓ заметка на обеих поверхностях, «gates=['» не возвращается; мутация R1 убита по ветви; прежние тесты tests/test_mcp_verify_handler.py прошли без правок. AC-7: ✓ мутаций 6, все KILLED по ветви (R1 SKIP, R2 кэш, R3 запись, R4 длительность, R5 код выхода, R6 локальный помощник в детекторе). Полный прогон 9108 passed / 27 skipped, mypy Success 355 файлов, ruff чист, bootstrap --check без дрейфа. CHANGELOG в обоих файлах. ДЕТЕКТОР УТОЧНЁН, А НЕ ПОДОГНАН: join над ОДНИМ вызовом внешней функции — транспорт; join над локальным помощником — по-прежнему вторая реализация (мутация R6 это доказывает). Иначе правило само открывало бы дыру для рендеринга за приватной функцией. Domain: полный прогон verify внутри этой задачи напечатал новый объединённый блок дескриптора, включая строку для tausik_task_done, — поведение проверено на живом прогоне, а не только на фикстурах.
