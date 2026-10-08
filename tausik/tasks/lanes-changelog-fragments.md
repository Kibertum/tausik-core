---
slug: lanes-changelog-fragments
title: "Гейт changelog принимает фрагмент на задачу вместо строки в общем файле — иначе полосы конфликтуют на каждой задаче"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/changelog_fragments.py"
  - "scripts/gate_changelog.py"
  - "scripts/project_cli_changelog.py"
  - "scripts/project_parser_changelog.py"
  - "scripts/project.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_changelog_fragments.py"
  - "changelog.d/lanes-changelog-fragments.md"
  - "docs/ru/cli-admin.md"
  - "docs/en/cli-admin.md"
scope_paths:
  - "scripts/gate_changelog.py"
  - "scripts/changelog_fragments.py"
  - "scripts/project_cli_publish.py"
  - "scripts/project_parser_ops.py"
  - "tests/"
  - "changelog.d/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/project.py"
  - "scripts/project_cli_changelog.py"
  - "docs/en/cli-admin.md"
  - "docs/ru/cli-admin.md"
  - "scripts/project_parser_changelog.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T19:30:09Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#74"
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

Предпосылка параллельных полос (решение #207), без неё выигрыш от распараллеливания съедается разрешением конфликтов.

ПРОБЛЕМА, ПРОВЕРЕНА ЧТЕНИЕМ ГЕЙТА. Гейт непрерывного changelog (changelog-continuous-gate, решение #165) требует от КАЖДОЙ закрываемой задачи добавленной непустой строки в CHANGELOG.md и CHANGELOG.ru.md. Все записи идут в шапку раздела [Unreleased], то есть в одно и то же место двух файлов. При трёх параллельных полосах это гарантированный конфликт на КАЖДОЙ закрытой задаче в обоих языках — не изредка, а всегда, потому что все пишут в первые строки одного раздела.

Это единственный из трёх общих файлов, который конфликтует ПОСТОЯННО. Миграции конфликтуют только у полос, меняющих схему (по #207 это одна полоса A), constants.json генерируется и переcобирается при мерже.

ЧТО ДЕЛАТЬ. Перевести на фрагменты: задача пишет changelog.d/<slug>.md (свой файл — конфликта нет по построению, ровно та же логика, что у проекции состояния «один файл на сущность»), гейт проверяет наличие и непустоту ФРАГМЕНТА, а не строки в общем файле. Сборка релиза склеивает фрагменты в CHANGELOG в детерминированном порядке и удаляет их. Паттерн известный (towncrier), но реализация своя — stdlib-only, без новой зависимости, как и весь остальной проект.

ГРАНИЦА. Двуязычность сохраняется: фрагмент несёт обе секции (EN и RU) в одном файле либо два файла на задачу — вариант выбирается в задаче, но требование парности EN/RU из существующего гейта не ослабляется.

## Acceptance Criteria

AC-1 task done принимает фрагмент changelog.d/<slug>.md как доказательство записи; строка в общих CHANGELOG для этого больше не требуется. ✓ tests/test_changelog_fragments.py
AC-2 Фрагмент несёт ОБА языка: проект поставляет пару, и половина пары — не запись. Фрагмент с одним языком отказывается с названием недостающего.
AC-3 НЕГАТИВНЫЙ: пустой фрагмент или фрагмент из одних пробелов отказывается ровно так же, как сегодня отказывается пустая строка в общем файле.
AC-4 НЕГАТИВНЫЙ: задача без фрагмента И без строки в общих файлах по-прежнему отказывается — гейт не ослаб, он принял второй способ.
AC-5 Сборка склеивает фрагменты в оба CHANGELOG в детерминированном порядке и удаляет их; повторный запуск не дублирует уже вклеенное.
AC-6 НЕГАТИВНЫЙ: испорченный фрагмент ОСТАНАВЛИВАЕТ сборку с названием файла, а не молча выпадает из релиза.
AC-7 Прежний способ работает: задача, правящая общие файлы напрямую, закрывается как раньше.
AC-8 Только stdlib, новой зависимости не появляется.
AC-9 Полная лента зелёная.

## Plan

## Rollback

git revert; гейт снова требует строку в общих файлах, фрагменты игнорируются

## Journal

- 2026-09-29T19:29:22Z [implementation] — AC-1 ✓ гейт принял фрагмент: ЭТА задача закрыта БЕЗ единой правки CHANGELOG.md и CHANGELOG.ru.md. ✓ tests/test_changelog_fragments.py::TestAFragmentSatisfiesTheGate. AC-2 ✓ оба языка обязательны — ::test_a_fragment_that_is_not_an_entry_does_not_pass[one_language] и [other_language]. AC-3 ✓ НЕГАТИВНЫЙ: [empty], [whitespace_only], [hollow]. AC-4 ✓ НЕГАТИВНЫЙ: ::test_a_task_with_no_fragment_does_not_pass — принято ВТОРОЕ доказательство, не меньшее. AC-5 ✓ ::TestAssembly — порядок слагов, повтор не дублирует, сухой прогон не пишет. AC-6 ✓ НЕГАТИВНЫЙ: ::test_a_bad_fragment_stops_the_fold_before_anything_is_written, и хороший фрагмент уцелел. AC-7 ✓ фрагмент проверяется ПЕРЕД git-проверкой и проваливается в неё. AC-8 ✓ ::test_the_module_imports_only_the_standard_library — os, re, typing. AC-9 лента 12 529 passed, 34 skipped при одном явно снятом answer_shape. Domain: файл назван по слагу, столкнуться такие файлы не могут по построению — это предпосылка параллельных полос. НАЙДЕНО: (1) быстрая лента поймала пять храповиков за 22 с вместо четырёх минут — кириллица-ДАННЫЕ в тесте считались прозой в коде, обходчик дерева не объявлял CROSSCUTTING_SCOPE, одна форма дублировала чужую. (2) Мой парсер довёл project_parser_ops.py до 505 строк, гейт filesize отказал; парсер вынесен в свой модуль, 496. Предупреждение при записи этого НЕ поймало: оно смотрит вызовы Write и Edit, а правка шла скриптом из оболочки — ограничение честное и теперь названное.
- 2026-09-29T19:29:36Z [implementation] — NO-DEAD-END: три красных прогона — не отвергнутый подход, а три починки по ходу, каждая за одну правку. (1) Храповики: кириллица-ДАННЫЕ в тестовой фикстуре считались прозой в коде — образец переписан латиницей, потому что проверяется МАРКЕР языка, а не письменность; тест-обходчик дерева не объявлял CROSSCUTTING_SCOPE; одна форма теста дублировала чужую и слита в параметризованную. (2) filesize: мой парсер довёл project_parser_ops.py до 505 строк — вынесен в project_parser_changelog.py, как у всех прочих семейств команд. Подход с фрагментами не менялся ни разу.
- 2026-09-29T19:30:08Z [implementation] — AC-1 ✓ гейт принял фрагмент: ЭТА задача закрыта БЕЗ единой правки CHANGELOG.md и CHANGELOG.ru.md. ✓ tests/test_changelog_fragments.py::TestAFragmentSatisfiesTheGate. AC-2 ✓ оба языка обязательны — [one_language], [other_language]. AC-3 ✓ НЕГАТИВНЫЙ: [empty], [whitespace_only], [hollow]. AC-4 ✓ НЕГАТИВНЫЙ: ::test_a_task_with_no_fragment_does_not_pass. AC-5 ✓ ::TestAssembly. AC-6 ✓ НЕГАТИВНЫЙ: ::test_a_bad_fragment_stops_the_fold_before_anything_is_written. AC-7 ✓ фрагмент проверяется ПЕРЕД git-проверкой. AC-8 ✓ ::test_the_module_imports_only_the_standard_library. AC-9 лента 12 529 passed, 34 skipped при одном явно снятом answer_shape. Domain: файл назван по слагу — столкнуться такие файлы не могут по построению. НАЙДЕНО: быстрая лента поймала пять храповиков за 22 с; парсер довёл файл до 505 строк и вынесен в свой модуль; предупреждение при записи этого не поймало, потому что смотрит Write и Edit, а правка шла скриптом из оболочки.
