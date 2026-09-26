---
slug: heredoc
title: "Гейт рамок не видит записи, сделанной питоновским скриптом через heredoc"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/python_source_writes.py"
  - "scripts/hooks/bash_write_parse.py"
  - "tests/test_heredoc_program_writes.py"
  - "tests/test_write_gate_reads_code_not_text.py"
  - "tests/test_firewall_reads_heredoc_as_data.py"
  - "tests/test_rag_prune_dead_paths.py"
scope_paths:
  - "scripts/hooks/python_source_writes.py"
  - "scripts/hooks/bash_write_parse.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:07:50Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО НА ЖИВОЙ РАБОТЕ, смена #238, при работе над xargs-executes-its-arguments.

ЧТО ПРОИЗОШЛО. У активной задачи scope_paths был испорчен (список сохранился одной строкой JSON и не совпадал ни с чем). Инструмент Write в tests/ был ЗАБЛОКИРОВАН гейтом рамок — правильно. Но правка scripts/hooks/bash_cmd_norm.py, сделанная в том же состоянии через 'python - <<EOF ... pathlib.Path(...).write_text(...) EOF', ПРОШЛА. Файл вне объявленных рамок изменён, ни одна проверка не сработала.

ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ УЖЕ ЗАКРЫТОГО. Задача write-from-inside-a-script-file закрыла случай 'python helper.py', где запись лежит в ФАЙЛЕ скрипта: гейт читает файл и находит open()/write_text. Здесь скрипта-файла нет вовсе — текст программы приходит heredoc'ом на stdin интерпретатора. bash_write_gate снимает тела heredoc'ов ПЕРЕД разбором (strip_heredoc_bodies, и это верно для поиска перенаправлений), поэтому тело, которое исполнит python, не осматривается никем.

ГРАНИЦА И НАПРАВЛЕНИЕ. Направление — ДЫРА в гейте рамок и в гейте записи разом. Чинить, не открыв ложных блоков: тело heredoc'а, уходящее в python/sh/node, есть ПРОГРАММА и должно осматриваться теми же правилами, что и файл скрипта; тело, уходящее в git commit -F - или в cat > file, программой не является и осматриваться не должно. Различие структурное — по КОМАНДЕ, которой heredoc скармливается, а не по содержимому.

ЗАМЕР ПЕРВЫМ ШАГОМ: предъявить цифрой, сколько heredoc-вызовов в журнале этого репозитория уходят интерпретатору и сколько из них содержат запись. Без цифры это мнение о том, как часто так делают.

## Acceptance Criteria

AC-1. ЗАМЕР ПО РЕАЛЬНОМУ КОРПУСУ: сколько heredoc-вызовов в журнале уходят интерпретатору (python/sh/bash/node), сколько из них пишут в проект, и сколько из этих записей гейт сегодня НЕ ВИДИТ. Число измеренное.
AC-2. ТЕЛО HEREDOC'А, УХОДЯЩЕЕ ИНТЕРПРЕТАТОРУ, ОСМАТРИВАЕТСЯ теми же правилами, что и файл скрипта: 'python - <<EOF ... write_text(path) ... EOF' даёт path целью записи.
AC-3. РАЗЛИЧИЕ СТРУКТУРНОЕ, А НЕ ПО СОДЕРЖИМОМУ: тело, уходящее НЕ интерпретатору (git commit -F -, cat > f, mail), программой не считается и не осматривается. Правило опирается на команду, которой скармливается heredoc.
AC-4. НЕГАТИВНЫЙ СЦЕНАРИЙ И ГЛАВНОЕ ОГРАНИЧЕНИЕ: расширение не смеет стать ложным блоком. Матрица безвредных heredoc'ов (сообщение коммита со словом open() в прозе, текст заметки со стрелкой, SQL-скрипт) остаётся незаблокированной. Живым хуком, а не только парсером.
AC-5. МУТАЦИИ: снятие починки возвращает невидимость записи; ни одна мутация не добавляет проверку.
AC-6. Снятие тел heredoc'ов ДЛЯ ПОИСКА ПЕРЕНАПРАВЛЕНИЙ сохраняется как есть — оно верно и защищает от фантомов из прозы. Новая проверка добавляется рядом, а не вместо.

## Plan

## Rollback

## Journal

- 2026-09-23T22:04:19Z [implementation] — AC-1 замер по реальному корпусу (транскрипты проекта, C:\Users\AYUMAS~1\AppData\Local\Temp/hd_measure.py, прогон разборщика bash_write_parse.write_targets на каждом Bash-вызове с heredoc): heredoc-вызовов 2600, отдано интерпретатору 1483, из них пишут файл 1085; гейт не видел цель в 917 до правки, 750 после привязок open(), 507 после заголовка с cd, 414 после VAR=1, 74 после Path-привязок и сегмента с <<. Остаток 74 — пути в переменных оболочки и циклы по именам (граница в enforcement-coverage).
- 2026-09-23T22:04:19Z [implementation] — AC-2: ✓ tests/test_heredoc_program_writes.py::test_the_write_inside_the_program_is_a_target
- 2026-09-23T22:04:20Z [implementation] — AC-2: ✓ tests/test_heredoc_program_writes.py::test_the_header_is_read_at_the_statement_that_takes_the_heredoc
- 2026-09-23T22:04:20Z [implementation] — AC-3: ✓ tests/test_heredoc_program_writes.py::test_a_heredoc_not_fed_to_an_interpreter_is_not_read_as_a_program
- 2026-09-23T22:04:21Z [implementation] — AC-4: ✓ tests/test_heredoc_program_writes.py::test_a_helper_that_only_reads_its_parameter_names_nothing; 545 тестов гейтов записи/firewall зелёные
- 2026-09-23T22:04:22Z [implementation] — AC-5: ✓ tests/test_write_gate_reads_code_not_text.py::test_detector_reads_code_not_text (строка 'computed path (name)' закрепляла дыру и перенесена в записи)
- 2026-09-23T22:04:22Z [implementation] — AC-6: ✓ снятие тел heredoc для поиска перенаправлений не тронуто; новая проверка рядом (_python_stdin_heredoc_writes)
- 2026-09-23T22:04:23Z [implementation] — NO-DEAD-END: красные прогоны — старый тест, закреплявший дыру, и мой отладочный пример с настоящим переводом строки
- 2026-09-23T22:06:46Z [implementation] — NO-DEAD-END: красный verify — два моих теста прошлых задач (firewall, rag-prune) читали вывод подпроцесса без encoding; добавлен encoding=utf-8
