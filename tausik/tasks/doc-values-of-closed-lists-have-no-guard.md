---
slug: doc-values-of-closed-lists-have-no-guard
title: "Значения и числа закрытых перечней живут в доках копиями без охраны: список типов SPEC там всё ещё девять"
status: done
epic: release-19-renar-conformance
story: standards-drift-detection
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gen_doc_constants.py, scripts/doc_drift_common.py, scripts/doc_drift_scanners.py, tests (новый тест сканера + существующие doc-drift), docs/en/mcp.md, docs/ru/mcp.md, README.md, README.ru.md, docs/_generated/constants.json"
scope_exclude: "состав закрытых перечней (SPEC_TYPES, FINDING_CATEGORIES, ADAPT_STATUSES); tests/closed_list_counts.py и tests/test_spec_types_closed_list.py (их область — код, не доки); решение #182 об асимметрии test_count"
relevant_files:
  - "scripts/doc_closed_lists.py"
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_scanners.py"
  - "scripts/gen_doc_constants.py"
  - "tests/test_doc_closed_list_drift.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-06T11:32:08Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР (#210). ТРИ ПОДТВЕРЖДЁННЫХ НОСИТЕЛЯ, ОДИН ПЕРЕСЧИТАТЬ.
(1) ПОДТВЕРЖДЕНО И УЖЕ ЛОЖЬ: docs/en/mcp.md:130 и docs/ru/mcp.md:127 объявляют тип SPEC «закрытым списком 9 (ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS)». Миграция v49 довела перечень до ОДИННАДЦАТИ по ADR-013, добавив TEST и DOC. Документация врёт с момента v49, и не покраснело нигде.
(2) ПОДТВЕРЖДЕНО: README.md:11 несёт бейдж «7115 tests» рукописным числом, тогда как механизм сверки чисел в доках СУЩЕСТВУЕТ — scripts/doc_drift_common.py:166 сверяет группу с constants.json["test_count"]. Бейдж этой охраной не покрыт. Живая лента на смене #210 даёт 8866, то есть бейдж занижает почти на две тысячи.
(3) ПОДТВЕРЖДЕНО ЧАСТИЧНО: README.md:138 и :161 дважды называют «128 MCP tools (121 project + 7 brain)», таблица IDE на :152 несёт число инструментов в ячейках. СКОЛЬКО ИМЕННО ячеек без охраны — ПЕРЕСЧИТАТЬ: передача #209 называла пять, я это число НЕ проверял и не выдаю за замер.
(4) СЮДА ЖЕ ЗНАЧЕНИЯ, А НЕ ТОЛЬКО ЧИСЛА: задача adapt-status-rename-missed-four-doc-carriers (#210) показала, что перечень статусов ADAPT назван в доках СЛОВАМИ в четырёх местах, и переименование signed->approved до них не дошло. Чинилось руками; механической охраны нет.

КОРЕНЬ ОДИН, И ЧИНИТЬ НАДО ЕГО (память #481): документация несёт КОПИИ содержимого закрытых перечней — и числа, и значения, — а сверяется с источником лишь часть. Охрана уже есть (doc_drift_common + constants.json, память #547 про gen_doc_constants --check). Задача — РАСПРОСТРАНИТЬ её на непокрытые носители, а не завести вторую охрану рядом: вторая копия детектора есть тот же дефект этажом выше.
ОБЯЗАТЕЛЬНО: у охраны должна быть ВЫРАЗИМАЯ КРАСНАЯ ветвь — тест, где доке подсунуто расходящееся значение и она краснеет. Без него это контроль, который не умеет падать (ADR-021), а таких мы в 1.9 уже нашли несколько.

## Acceptance Criteria

AC-1 (значения и число закрытых перечней в доках сверяются с источником): constants.json несёт ЗНАЧЕНИЯ и число трёх закрытых перечней (типы SPEC, категории находок ADAPT, статусы ADAPT), выведенные из SPEC_TYPES / FINDING_CATEGORIES / ADAPT_STATUSES генератором gen_doc_constants; новый сканер в doc_drift_scanners сверяет каждое перечисление в доках и с числом, и с составом. Предмет перечисления ВЫВОДИТСЯ по наибольшему пересечению с известными перечнями, а не по имени файла и не по строке-якорю.
AC-2 (красная ветвь выразима, ADR-021): тест подсовывает доке (а) верное число при неверном составе, (б) верный состав при неверном числе, (в) перечень с лишним значением, (г) перечень с недостающим значением — сканер краснеет в каждом случае и НАЗЫВАЕТ, чего не хватает или что лишнее. Зелёная ветвь: живые доки после починки дают ноль сообщений.
AC-3 (живая ложь исправлена): docs/en/mcp.md и docs/ru/mcp.md называют одиннадцать типов SPEC с TEST и DOC; после правки сканер зелёный, а до правки — красный (проверено прогоном и записано в журнал).
AC-4 (ячейки таблицы под охраной): числовые ячейки столбца, чей заголовок называет инструменты MCP, сверяются с mcp_main_tools; пять ячеек README.md и их близнецы в README.ru.md перестают быть невидимыми. Negative: подмена одной ячейки даёт сообщение с номером строки и именем столбца.
AC-5 (вторая охрана не заведена): новый сканер живёт в doc_drift_scanners рядом с существующими, читает constants.json и переиспользует _strip_fenced_blocks/_strip_dynamic_block; закрытые перечни в constants.json выводятся из тех же кортежей, что и всё остальное, — второго литерального перечня нет (test_spec_types_closed_list::test_no_second_literal_list_of_spec_types и closed_list_counts остаются зелёными).
AC-6: gen_doc_constants --check зелёный, развёрнутые копии constants.json обновлены bootstrap-ом; полный прогон ленты; мутации объявлены и убиты ПО ВЕТВИ; CHANGELOG в обоих файлах.

## Plan

## Rollback

git revert коммита задачи; constants.json перегенерируется gen_doc_constants --write, схема и данные не затрагиваются.

## Journal

- 2026-09-04T22:25:23Z [planning] — ИНВЕНТАРЬ И ПОПРАВКА К ЗАМЕРУ #210, снято чтением и прогоном трёх сканеров на живых доках (все три дают 0 сообщений сегодня). (1) ПОДТВЕРЖДЕНО, НАСТОЯЩАЯ ЛОЖЬ: docs/en/mcp.md:130 и docs/ru/mcp.md:127 — «closed list of 9 (ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS)» при одиннадцати с миграции v49. Носители ЗНАЧЕНИЙ закрытых перечней в доках: ровно два файла, шесть строк — SPEC-типы (en:130, ru:127), категории находок (en:145, ru:142 — «closed list of 7», значения верны), статусы ADAPT (en:148, ru:145 — «§7.8.1 closed list: draft/review/asked/answered/approved/frozen/superseded», без числа, значения верны после v50). Охрана closed_list_counts/LIST_RE ходит по scripts/harness/tests и НЕ ВИДИТ docs — там нет ни одного носителя из её области. (2) ПРЕМИСА ЗАДАЧИ НЕВЕРНА В ЭТОЙ ЧАСТИ: бейдж «7115 tests» ОХРАНОЙ ПОКРЫТ — README.md в CROSS_FILE_SCAN_TARGETS, шаблон tests-(\d+)-(brightgreen…) совпадает. Правило АСИММЕТРИЧНО ПО ЗАМЫСЛУ (решение #182): test_count — нижняя граница, краснеет только ЗАВЫШЕНИЕ (found > expected). 7115 при живых 8835 — занижение, drift не объявляется намеренно. Настоящая (и меньшая) претензия: бейдж пишет «7115 tests», а не «7115+», то есть форма обещает точность, которой правило не требует. Отдельного дефекта не завожу — это выбор владельца по #182, предъявляю цифрами. (3) ПЕРЕСЧИТАНО (передача #209 называла пять, число ПОДТВЕРЖДАЕТСЯ): в README.md ровно одна таблица со столбцом «MCP tools» и ПЯТЬ числовых ячеек 128 в нём (Claude, Qwen, Kilo, Cursor, VSCode). Ни один шаблон scan_mcp_tool_counts на голую ячейку таблицы не рассчитан: они требуют слов (N tools / N project tools / **N tools** / the same N tools). Прозаические «128 MCP tools (121 project + 7 brain)» на :138 и :161 покрыты парным шаблоном. В README.ru.md — семь вхождений 128, разбор тот же. (4) Значения статусов ADAPT и категорий находок в доках сегодня ВЕРНЫ, но не охраняются ничем: их правильность — состояние, а не свойство конструкции (та же формулировка, что у задачи про три литеральные копии). ВЫВОД ДЛЯ ФОРМЫ: расширять НАДО существующую машинерию doc_drift (constants.json + сканеры), а не заводить вторую. Двумя добавками: (а) закрытые перечни попадают в constants.json ЗНАЧЕНИЯМИ и числом, а новый сканер сверяет с ними и число, и состав, определяя предмет по НАИБОЛЬШЕМУ ПЕРЕСЕЧЕНИЮ с известными перечнями (иначе доку, которая врёт составом, нельзя опознать по составу); (б) сканер столбца markdown-таблицы: ячейки столбца с заголовком «MCP tools» сверяются с mcp_main_tools.
- 2026-09-06T11:24:30Z [implementation] — ПОЧИНКА. Новый scripts/doc_closed_lists.py (CLOSED_LISTS: три перечня, выведенные из SPEC_TYPES/FINDING_CATEGORIES/ADAPT_STATUSES, число едет как len(); closed_lists_flat кладёт их в constants.json одним ключом closed_lists — вложенным, чтобы число не ездило отдельно от значений). В doc_drift_common: _CLOSED_LIST_ENUM_RE (три и более токена через слэш), _CLOSED_LIST_COUNT_RE (число непосредственно перед перечислением), CLOSED_LIST_COUNT_LOOKBEHIND=40, CLOSED_LIST_MIN_OVERLAP=3, _MCP_TABLE_COLUMN_RE (заголовок столбца). В doc_drift_scanners: scan_closed_list_enums (предмет ВЫВОДИТСЯ по наибольшему пересечению через _best_closed_list; сообщение называет недостающее, лишнее и расхождение числа) и scan_mcp_table_columns (столбец находится по ЗАГОЛОВКУ, индекс сбрасывается на конце таблицы, нечисловые ячейки пропускаются). gen_doc_constants вызывает обе в --check и кладёт перечни в payload. ЖИВАЯ ЛОЖЬ ИСПРАВЛЕНА: docs/en/mcp.md:130 и docs/ru/mcp.md:127 — одиннадцать типов с TEST и DOC. Замер до правки: сканер давал 4 сообщения (два файла × состав + число), после правки — 0. Таблица README: 0 сообщений (ячейки верны), красная ветвь закреплена тестом. ЛЕНТА: tests/test_doc_closed_list_drift.py 20 passed ОДИНОЧНЫМ запуском (память #593); constants перегенерированы, bootstrap --ide all + --check без дрейфа, gen_doc_constants --check зелёный; ruff/format/mypy чисто; файлы 355/368/327/57/228 строк. МУТАЦИИ 12: убито 10 сразу (D1 недостающие игнорируются, D2 лишние игнорируются, D3 число не сверяется, D4 порог пересечения снят, D5 предмет берётся первым, а не по лучшему пересечению, D6 fenced не срезается, D8 столбец по индексу, D9 индекс течёт за таблицу, D10 нечисловые ячейки как счёт, D12 типы SPEC переписаны литералом). ДВЕ ВЫЖИЛИ, обе разобраны ДО КОНЦА: D11 (перечни выброшены из payload) — настоящая дыра: нагрузка без ключа глушит сканер ПО ЗАМЫСЛУ, и все доковые тесты оставались зелёными; написан test_the_live_constants_actually_carry_the_lists, D11 им убита. D7 (порог три токена → два) — ЭКВИВАЛЕНТНАЯ мутация: двухтокенный набор не может дать пересечение ≥3 и отсеивается порогом шагом позже; прогон ВСЕГО файла её не убивает, потому что убивать нечего. Не засчитываю как убитую, а объявляю эквивалентной прямо в докстринге _CLOSED_LIST_ENUM_RE, чтобы следующий читатель не принял этот порог за охрану.
- 2026-09-06T11:29:23Z [implementation] — ПОЛНЫЙ ПРОГОН ПОСЛЕ ПРАВКИ ПОКАЗАЛ ДВА КРАСНЫХ, И ОБА ПО ДЕЛУ — чужие охраны написанного счёта: test_no_hand_written_count_of_finding_categories и test_no_hand_written_count_beside_the_list. Мои же докстринги цитировали старую формулировку доки («closed list of 9 (ARCH/…)») и писали «eleven SPEC types», а фикстура несла литерал «closed list of 7». Мои новые файлы лежат ВНУТРИ дерева (scripts/, tests/), по которому эти охраны ходят. ИСПРАВЛЕНО ПЕРЕФОРМУЛИРОВАНИЕМ, НЕ РАЗРЕШАЮЩИМ СПИСКОМ (тот же вывод, что в #212): докстринг doc_closed_lists описывает состояние доки без чисел («описывала список, каким он был ДО миграции v49 — двух добавленных ADR-013 типов не было в значениях, а число рядом было старым») и прямо говорит, почему чисел нет; в тестах все счётчики выведены из len(SPEC_TYPES)/len(FINDING_CATEGORIES), включая ожидаемые подстроки сообщений. Прогон трёх файлов вместе: 108 passed. Это же был единственный красный полной ленты (9003 passed / 2 failed до правки), mypy 366 файлов чисто, ruff чисто, gen_doc_constants --check зелёный. Bootstrap: после правки скриптов развёрнутые копии снова разошлись — bootstrap --ide all и --check прогнаны заново, дрейфа нет.
- 2026-09-06T11:32:06Z [implementation] — AC-1: ✓ scripts/doc_closed_lists.py — три перечня в constants.json, выведенные из SPEC_TYPES/FINDING_CATEGORIES/ADAPT_STATUSES; scan_closed_list_enums сверяет и состав, и число, предмет выводится по наибольшему пересечению. tests/test_doc_closed_list_drift.py::test_the_lists_are_derived_from_the_service_tuples, tests/test_doc_closed_list_drift.py::test_the_live_constants_actually_carry_the_lists AC-2: ✓ красные ветви по всем четырём случаям — tests/test_doc_closed_list_drift.py::test_a_missing_value_is_named (верное число, неверный состав), tests/test_doc_closed_list_drift.py::test_the_right_values_with_a_wrong_count_still_reds (верный состав, неверное число), tests/test_doc_closed_list_drift.py::test_an_unknown_value_is_named (лишнее значение), tests/test_doc_closed_list_drift.py::test_a_renamed_value_reds_as_both_missing_and_unknown (переименование signed→approved), tests/test_doc_closed_list_drift.py::test_the_finding_categories_are_watched_too. Зелёная ветвь: tests/test_doc_closed_list_drift.py::test_an_honest_enumeration_is_silent и tests/test_doc_closed_list_drift.py::test_the_live_docs_are_clean AC-3: ✓ docs/en/mcp.md:130 и docs/ru/mcp.md:127 называют одиннадцать типов с TEST и DOC; замер записан в журнал: до правки сканер давал 4 сообщения (два файла × состав + число), после — 0 AC-4: ✓ scan_mcp_table_columns; tests/test_doc_closed_list_drift.py::test_a_stale_cell_is_named_with_its_line (сообщение с номером строки и именем столбца), tests/test_doc_closed_list_drift.py::test_the_column_is_found_by_its_header_not_its_position, tests/test_doc_closed_list_drift.py::test_a_second_table_without_the_column_is_not_scanned, tests/test_doc_closed_list_drift.py::test_a_non_numeric_cell_is_not_a_count AC-5: ✓ сканеры живут в doc_drift_scanners рядом с существующими, читают constants.json, переиспользуют _strip_fenced_blocks (tests/test_doc_closed_list_drift.py::test_a_fenced_illustration_is_ignored); второго литерального перечня нет — tests/test_spec_types_closed_list.py::test_no_second_literal_list_of_spec_types зелёный, мутация D12 (перечень переписан литералом) убита AC-6: ✓ gen_doc_constants --check зелёный, развёрнутые копии constants.json обновлены bootstrap --ide all, --check без дрейфа; полный прогон ленты; CHANGELOG.md и CHANGELOG.ru.md; мутации 12 объявлено, 11 убито по ветви, 1 (D7, порог в три токена) ЭКВИВАЛЕНТНА и объявлена таковой в докстринге _CLOSED_LIST_ENUM_RE Negative: tests/test_doc_closed_list_drift.py::test_an_unrelated_slash_run_is_not_one_of_our_lists и tests/test_doc_closed_list_drift.py::test_two_shared_values_are_coincidence_not_a_quotation — путь и прозаический набор не объявляются перечнем; tests/test_doc_closed_list_drift.py::test_an_empty_registry_disables_the_scan — деградация в тишину, а не в падение Domain: дрейф документации против закрытых перечней стандарта (§13.3.4, §7.4.4, §7.8.1), constants.json как единственный источник чисел и значений для доков.
