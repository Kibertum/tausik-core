---
slug: filesize-gate-counts-lines-in-binary-files
title: "Гейт размера считает строки в бинарном файле и блокирует закрытие по PDF"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: simple
role: backend
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_filesize.py"
  - "tests/test_gates.py"
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-25T13:24:38Z"
---

## Goal

Гейт filesize применяет лимит 500 строк только к тому, у чего строки есть смысл считать — к исходному тексту. Бинарный или нетекстовый файл в объявленной области не превращает закрытие задачи в отказ по несуществующему нарушению.

## Acceptance Criteria

AC1. ВОСПРОИЗВЕДЕНИЕ (сессия #177, наблюдено вживую): tausik task done с relevant_files, содержащими PDF, даёт отказ 'TAUSIK-report-survey.pdf: 9897 lines (max 500)' и 'TAUSIK-report-survey-full.pdf: 45795 lines (max 500)'. Это не нарушение лимита исходника, а подсчёт байтовых переводов строки в сжатом потоке.
AC2. КОРЕНЬ НАЗВАН ТОЧНО: цикл в scripts/gate_filesize.py фильтрует только по каталогам-исключениям, точным путям и базовым именам. Фильтра по ТИПУ файла нет вовсе, поэтому лимит исходника применяется к чему угодно — PDF, PNG, архив.
AC3. Решение опирается на СОДЕРЖИМОЕ, а не на список расширений: расширения не исчерпать, а следующий бинарный формат приедет с очередной задачей. Признак нетекстового файла (нулевой байт в первых килобайтах либо неудача декодирования) — устойчивее.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест обязан сначала ПОКРАСНЕТЬ на настоящем маленьком бинарном файле, собранном фикстурой.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: длинный ТЕКСТОВЫЙ файл по-прежнему нарушает лимит. Послабление не имеет права снять гейт с исходников — он для этого и заводился (решение #190).
AC6. Файл в UTF-8 с кириллицей НЕ считается бинарным. Проверка на нулевой байт этого не путает, а вот наивная проверка 'декодируется в ascii' — путает, и тогда гейт замолчит на половине наших исходников.

## Plan

## Rollback

git revert коммита: гейт снова считает строки во всех объявленных файлах

## Journal

- 2026-08-25T13:22:48Z [implementation] — AC1 воспроизведён тестом: фикстура PDF даёт 'TAUSIK-report-survey.pdf: 602 lines (max 500)' — тот же отказ, что наблюдался вживую в #177. AC2 подтверждён чтением: цикл run_filesize_gate фильтрует только по каталогам, точным путям и базовым именам, фильтра по типу нет вовсе. Реализовано is_binary_file по СОДЕРЖИМОМУ (AC3): нулевой байт в первых 8192 байтах либо неудача декодирования UTF-8. Декодер инкрементальный без final=True — фиксированное чтение режет многобайтовый символ пополам, и обычный bytes.decode объявил бы бинарным каждый длинный кириллический исходник (AC6). Красное до правки: 6 тестов. После: 115 passed в test_gates.py.
- 2026-08-25T13:25:06Z [done] — AC-1: ✓ tested via tests/test_gates.py::TestGateRunner::test_binary_file_does_not_violate_the_line_cap. AC-2: ✓ корень назван и устранён в scripts/gate_filesize.py — вызов is_binary_file добавлен в цикл run_filesize_gate перед count_lines. AC-3: ✓ tested via tests/test_gates.py::TestGateRunner::test_binary_detection_reads_content_not_the_extension и ::test_long_text_wearing_a_binary_extension_still_blocks — проверены ОБА направления, бинарь под именем .md исключается, текст под именем .pdf по-прежнему блокируется. AC-4: ✓ негативный сценарий выполнен — шесть новых тестов дали 6 failed до правки, 115 passed после; фикстура _write_binary_pdf собирает настоящий маленький бинарный файл (magic PDF, реальные нулевые байты), а не мок. AC-5: ✓ tested via tests/test_gates.py::TestGateRunner::test_long_text_file_still_violates_the_cap — длинный текстовый .py по-прежнему нарушает лимит, послабление гейт с исходников не снимает. AC-6: ✓ tested via ::test_utf8_cyrillic_source_is_not_mistaken_for_binary и ::test_multibyte_char_straddling_the_sniff_boundary_is_not_binary. Domain: прогон по НАСТОЯЩИМ файлам, которые вызвали отказ в #177 — TAUSIK-report-survey.pdf (count_lines 9897, ровно число из отказа) и TAUSIK-report-survey-full.pdf (45795, ровно число из отказа) — гейт возвращает All files within line limit; на настоящем исходнике scripts/gate_filesize.py при лимите 100 гейт по-прежнему отказывает 295 lines.
