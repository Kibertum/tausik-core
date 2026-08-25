---
slug: docs-enforcement-drift-matrix
title: "Доки описывают ЗАЩИТУ СЛАБЕЕ, чем применяет код: матрица SENAR зовёт Hard-гейты Warning, hooks.md не знает двух блокирующих хуков"
status: done
epic: shared-knowledge
story: kb-docs
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "docs/{ru,en}/senar-compliance-matrix.md, docs/{ru,en}/hooks.md, docs/{ru,en}/senar.md, scripts/doc_drift_common.py, scripts/doc_drift_scanners.py, scripts/doc_drift_fixes.py, tests/test_doc_drift_scanners.py"
scope_exclude: ".claude/**, .cursor/**, .kilo/**, .opencode/**, .qwen/** (генерируются bootstrap-синком), любые несвязанные счётчики (skills 12/38, метрики), нумерация/enforcement других SENAR-правил вне 2/4/5/6"
relevant_files:
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_scanners.py"
  - "scripts/doc_drift_fixes.py"
  - "tests/test_doc_drift_scanners.py"
  - "docs/en/hooks.md"
  - "docs/ru/hooks.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/senar.md"
  - "docs/ru/senar.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T18:56:43Z"
---

## Goal

Класс дефекта опаснее обычного doc-drift: свежий агент читает контракт и считает, что защиты нет там, где она есть (и наоборот). Конкретно: docs/{ru,en}/senar-compliance-matrix.md:14 зовёт QG-0 scope «Warning», код (gate_qg0_check.py:148-156) бросает ServiceError для medium/complex; :32 зовёт Rule 2 «Warning», реально — жёсткий PreToolUse-блок (scope_write_gate + bash_write_gate); :34 зовёт Rule 5 checklist «Warning», реально блок для tiers substantial/deep (gate_ac_check.py:198-213); Rules 4 и 6 в таблице ОТСУТСТВУЮТ, хотя оба реализованы и жёсткие; заголовок файла говорит «SENAR v1.5», футер — «v1.3». docs/{ru,en}/hooks.md заявляет «20 Python + 1 shell = 21» и не содержит scope_write_gate и bash_write_gate — ровно двух хуков-флагманов 1.8; реально зарегистрировано 22+1. docs/ru/senar.md:98 («правила 4 и 5 пока НЕ применяются как жёсткие блокировки») прямо противоречит docs/en/senar.md:97 («as of v1.5 these ARE enforced») — код на стороне EN. И дрейф-гейт этого НЕ ловит: doc_drift_scanners.py:166 матчит \b(\d+)\s+hooks\b, а в README написано «21 real-time hooks» — \s+hooks не совпадает; русский паттерн \b(\d+)\s+хуков\b не ловит «21 real-time-хук»; hooks.md вообще нет в CROSS_FILE_SCAN_TARGETS. Значит gen_doc_constants --check возвращает OK при устаревших числах. Чинить надо И доки, И слепоту сканера — иначе повторится.

## Acceptance Criteria

1. senar-compliance-matrix.md (ru+en): Rule 2 enforcement исправлен с "Warning" на Hard (hook scope_write_gate/bash_write_gate + QG-0 hard-gate для medium/complex); Rule 5 — "Hard для substantial/deep, Warning ниже"; QG-0 scope-строка отражает hard-gate для medium/complex; строки Rules 4 (внешняя проверка) и 6 (rollback plan) ДОБАВЛЕНЫ; итоги пересчитаны (Rules → 13/13, Total → 35); заголовок и футер приведены к одной версии SENAR (v1.5).
2. hooks.md (ru+en): строка scope_write_gate.py добавлена в PreToolUse; счётчик в шапке исправлен на актуальные 22 Python + 1 shell, в форме с ОДНИМ ловимым числом "hooks".
3. senar.md ru:98 переписан под код (сторона EN): Rules 4-6 применяются как жёсткие с v1.5; RU/EN таблицы правил согласованы (нет расхождения по наличию Rule 6).
4. Слепота сканера закрыта: hooks.md добавлен в code-count target-список, который обходит scan_code_counts; паттерны hooks расширены allow-list-квалификатором (python/active/активн) — ловят "N Python hooks"/"N активных хук".
НЕГАТИВНЫЙ СЦЕНАРИЙ: тест вставляет заведомо устаревшее "20 Python hooks" в fixture и утверждает, что scan_code_counts теперь ВОЗВРАЩАЕТ drift-сообщение (раньше возвращал пусто) — доказывая, что слепота закрыта, а не просто текущее число сверено. Плюс: расширенные паттерны НЕ дают ложных срабатываний на существующих доках (grep-проверка + зелёные тесты сканера).
5. gen_doc_constants --check возвращает OK на исправленном дереве; полная суита зелёная.

## Plan

[{"step": "Scanner: add CODE_COUNT_EXTRA_TARGETS (hooks.md ru+en) + broaden hooks patterns (python/active/\u0430\u043a\u0442\u0438\u0432\u043d qualifier) in doc_drift_common.py", "done": true}, {"step": "Scanner: wire scan_code_counts + write_cross_file_fixes to walk CODE_COUNT_EXTRA_TARGETS", "done": true}, {"step": "hooks.md ru+en: add scope_write_gate row, fix header count to canonical single catchable form", "done": true}, {"step": "senar-compliance-matrix.md ru+en: fix Rule2/Rule5/QG-0 enforcement, add Rules 4&6, recompute totals, version coherence", "done": true}, {"step": "senar.md ru:98 rewrite to match code (EN); align RU/EN rule tables", "done": true}, {"step": "Tests: negative-scenario test (stale count detected) + broadened-pattern coverage in test_doc_drift_scanners.py", "done": true}, {"step": "Verify: gen_doc_constants --check OK, run scanner tests, then scoped verify + full suite", "done": true}, {"step": "Sync mirrors via bootstrap refresh", "done": true}]

## Rollback

git revert коммита задачи — изменения чисто в docs/*.md и scripts/doc_drift_*.py + один тест-файл, без миграций БД и без изменения runtime-поведения гейтов; откат восстанавливает прежние тексты и regex-таблицу.

## Journal

- 2026-07-26T18:52:30Z [implementation] — Реализовано: (scanner) CODE_COUNT_EXTRA_TARGETS=hooks.md ru+en, scan_code_counts+fixer обходят их; hooks-паттерны расширены allow-list-квалификатором (real-time/python/active/активн) + RU дефис-префикс. (docs) hooks.md ru+en: +scope_write_gate строка, шапка 22 Python+1 shell (одно ловимое число); senar-compliance-matrix ru+en: Rule2/5/QG-0 enforcement исправлены, +Rules 4&6, итоги 13/13 и Total 35, версия v1.5 coherent; senar.md ru:98 переписан под код (EN), RU/EN таблицы правил согласованы (+Rules 4,5,6). Тесты: +2 класса (11 тестов) в test_doc_drift_scanners — квалификаторы, hooks.md в scan-set, негативный сценарий (stale 20/19 ловится), version-иммунитет, авто-фикс. Все 23 зелёные. gen_doc_constants --check OK. docs_lint OK (1 предсущ. warning не мой). Grep-свип: ложных FP нет.
- 2026-07-26T18:55:59Z [implementation] — AC verified: 1. ✓ senar-compliance-matrix.md ru+en: Rule 2 Warning->Hard(hook+QG-0), Rule 5 Warning->Hard(substantial/deep), QG-0 scope->Hard(medium/complex); +Rule 4 & Rule 6 rows; Result 11/11->13/13, Total 33->35; header/footer оба v1.5. Verify scoped pytest PASS incl tests/test_senar.py 2. ✓ hooks.md ru+en: +scope_write_gate.py строка в PreToolUse; шапка '22 Python hooks + 1 shell' (одно ловимое число). scan_code_counts подтверждает EN '22 Python hooks'->22, RU '22 Python-хука'->22, дрейфа нет 3. ✓ docs/ru/senar.md:98 переписан под код(EN): Rules 4-6 применяются как жёсткие с v1.5; +Rules 4,5,6 в обе таблицы правил (RU/EN согласованы). tests/test_senar.py PASS 4. ✓ tests/test_doc_drift_scanners.py::TestHooksMdInScanSet::test_stale_count_in_hooks_md_is_detected (НЕГАТИВНЫЙ: stale '20 Python hooks'/'19 активных хука' ловится) + TestHooksCountQualifiers (python/active/активн) + test_qualifier_is_allowlist_not_greedy (нет FP). 23 passed. Grep-свип: ложных FP нет 5. ✓ python scripts/gen_doc_constants.py --check -> OK; tausik verify --task standard -> passed=True, [PASS] pytest scoped 4 файла; docs_lint exit 0 (1 предсущ. warning не мой)
- 2026-07-26T18:56:42Z [implementation] — AC verified: 1. ✓ senar-compliance-matrix.md ru+en: Rule2 Warning->Hard(hook+QG-0), Rule5 Warning->Hard(substantial/deep), QG-0 scope->Hard(medium/complex); +Rule4 & Rule6; 11/11->13/13, Total 33->35; header/footer v1.5. Verify pytest PASS incl test_senar.py 2. ✓ hooks.md ru+en: +scope_write_gate строка; шапка 22 Python+1 shell. scan_code_counts: EN '22 Python hooks'->22, RU '22 Python-хука'->22, дрейфа нет 3. ✓ docs/ru/senar.md:98 переписан под код(EN); +Rules4,5,6 в обе таблицы (RU/EN согласованы). test_senar.py PASS 4. ✓ test_doc_drift_scanners.py::TestHooksMdInScanSet::test_stale_count_in_hooks_md_is_detected (негативный: stale 20/19 ловится) + TestHooksCountQualifiers + test_qualifier_is_allowlist_not_greedy. 23 passed 5. ✓ gen_doc_constants --check OK; tausik verify --task standard passed=True [PASS] pytest 4 файла; docs_lint exit 0
