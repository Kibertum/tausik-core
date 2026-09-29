---
slug: the-line-cap-is-knowable-at-write-time-not-at-verify
title: "Порог в 500 строк известен при записи, а краснеет только на проверке"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/filesize_forecast.py"
  - "scripts/gate_filesize.py"
  - "scripts/hooks/scope_write_gate.py"
  - "tests/test_filesize_forecast.py"
scope_paths:
  - "scripts/gate_filesize.py"
  - "scripts/filesize_forecast.py"
  - "scripts/hooks/scope_write_gate.py"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T18:24:24Z"
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

Разбор 285 красных verify: filesize даёт 16,1% и он живой — 20 отказов в сентябре, второй по частоте управляемый после bootstrap_drift (56, уже закрыт --prepare). Порог детерминирован и известен в момент записи файла, но агент узнаёт о нём после того, как прогон уже оплачен. Красный прогон стоит дорого: 0 красных → 51k токенов на задачу, один → 78k, два → 123k. Цель: предупреждение приходит в тот же ход, что и запись, через additionalContext, и НИКОГДА не блокирует.

## Acceptance Criteria

AC-1 Write, чьё содержимое переводит файл через порог, даёт предупреждение с именем файла, итоговым числом строк и порогом — в том же ходе. ✓ tests/test_filesize_forecast.py
AC-2 Для Edit итог считается по дельте old_string/new_string поверх файла на диске, а не по догадке.
AC-3 НЕГАТИВНЫЙ: предупреждение НИКОГДА не блокирует — код возврата остаётся 0 и запись проходит.
AC-4 НЕГАТИВНЫЙ: путь, который гейт освобождает (тесты, порождённое, именованные исключения), предупреждения НЕ даёт — иначе это шум о том, на что гейт не среагирует.
AC-5 НЕГАТИВНЫЙ: нечитаемый файл или разобранный не до конца payload дают ПУСТО, а не догадку.
AC-6 Порог и исключения берутся из ТОГО ЖЕ источника, что у гейта: предикат вынесен из run_filesize_gate, второй копии правил не появляется.
AC-7 Полная лента зелёная.

## Plan

## Rollback

git revert; гейт продолжает ловить на verify, как и раньше

## Journal

- 2026-09-29T18:24:20Z [implementation] — AC-1 ✓ Write через порог даёт строку с именем, итогом и порогом; ✓ tests/test_filesize_forecast.py::TestAWriteThatCrossesTheCap, включая разное слово для «подходит к порогу» и «перешёл». AC-2 ✓ Edit считается по дельте поверх файла на диске, и сжимающая правка молчит; ::TestAnEditIsComputedFromItsDelta. AC-3 ✓ НЕГАТИВНЫЙ: ::TestTheHookOnlyEverAdvises читает тело allow-пути и требует отсутствия return 2 и наличия except Exception — сбой совета не решает судьбу записи. Живая проба хука: код 0 на записи в 640 строк, предупреждение в additionalContext; на 120 строках молчит. AC-4 ✓ НЕГАТИВНЫЙ: освобождённый гейтом путь молчит; ::test_an_exempt_path_is_silent. AC-5 ✓ НЕГАТИВНЫЙ: replace_all, отсутствующий файл, четыре формы неполного payload и четыре чужих инструмента дают пусто; ::TestSilenceWhereverTheAnswerIsNotKnown. AC-6 ✓ is_exempt ВЫНЕСЕН из run_filesize_gate и импортируется прогнозом; ::test_the_exemption_comes_from_the_gate_rather_than_a_copy и ::test_the_cap_is_the_gates_cap. AC-7 ✓ полная лента 12 498 passed, 34 skipped, 0 deselected. Domain: filesize давал 20 красных прогонов в сентябре; при 27k токенов разницы на красный это около полумиллиона токенов в месяц, и теперь отказ известен до того, как прогон оплачен.
