---
slug: no-file-changes-unreachable-journaling-dirties-the-tree
title: "Флаг --no-file-changes недостижим: обязательное журналирование само пачкает дерево"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_verify_first.py"
  - "scripts/state_triggers.py"
  - "scripts/verify_git_diff.py"
  - "tests/test_fileless_close.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-25T13:34:57Z"
---

## Goal

Задачу, не менявшую ни одного файла в репозитории, можно закрыть флагом --no-file-changes, не совершая перед этим коммит ради самого закрытия. Проверка отличает РАБОТУ задачи от бухгалтерии, которую пишет сам фреймворк.

## Acceptance Criteria

AC1. ВОСПРОИЗВЕДЕНИЕ (сессия #177, наблюдено вживую): дерево чистое -> tausik task log <slug> '...' -> tausik task done <slug> --no-file-changes -> ОТКАЗ 'git reports uncommitted changes in the working tree: tausik/tasks/<slug>.md'. Файл в отказе — это ЖУРНАЛ ТОЙ ЖЕ ЗАДАЧИ, который фреймворк только что записал сам, выполняя собственное жёсткое правило о непрерывном журналировании.
AC2. Проверка НЕ считает изменением работы задачи то, что записал сам фреймворк: авто-экспорт проекции tausik/ (tasks, stories, memory, decisions, journal). Всё остальное дерево проверяется как раньше.
AC3. ФЛАГ НЕ ОСЛАБЛЯЕТСЯ. Смысл --no-file-changes — 'git доказывает, что работы в коде нет'. Исключение касается ТОЛЬКО каталога, который пишет сам фреймворк, и перечень исключаемых путей выводится из места проекции, а не из списка-литерала.
AC4. НЕГАТИВНЫЙ СЦЕНАРИЙ: тест обязан сначала ПОКРАСНЕТЬ на воспроизведении из AC1. Затем — второй тест, который обязан ОСТАТЬСЯ КРАСНЫМ: правка в scripts/ при --no-file-changes по-прежнему блокирует закрытие. Послабление, которое пропускает настоящий код, хуже недостижимого флага.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: незакоммиченная правка ВНУТРИ tausik/, сделанная РУКАМИ (а не авто-экспортом), не должна тихо проезжать. Если отличить руку от экспорта невозможно, это записывается как названная граница исключения, а не умалчивается.
AC6. Обходной путь, которым пользовались до сих пор — коммит ради закрытия, — назван в документации как БОЛЬШЕ НЕ НУЖНЫЙ. Иначе следующий агент повторит его по инерции.

## Plan

## Rollback

git revert коммита: проверка возвращается к сравнению по всему дереву

## Journal

- 2026-08-25T13:33:51Z [implementation] — AC-1: ✓ tested via tests/test_fileless_close.py::TestProjectionIsNotTheTasksWork::test_own_journal_projection_does_not_block_the_close — воспроизведение сессии #177: dirty=[tausik/tasks/t.md] давало отказ, теперь закрытие проходит. AC-2: ✓ tested via ::test_every_projected_kind_is_excluded_not_just_tasks — исключены все пять проецируемых видов, не только tasks. AC-3: ✓ tested via ::test_prefixes_are_derived_from_entity_dirs_not_a_literal_list — перечень выводится из state_triggers.projection_dirs (адрес проекции берётся у того же _tree_root, которым пользуется экспортёр) и из state_serialize.ENTITY_DIRS; литерального списка нет ни в одном из трёх модулей. AC-4: ✓ негативный сценарий выполнен — 5 тестов красные до правки; ::test_source_edit_still_blocks_under_the_flag остаётся требованием блокировки: смешанная область (scripts/real_work.py + журнал) блокирует и называет ИСХОДНИК, а журнал в сообщении не упоминается. AC-5: ✓ tested via ::test_hand_written_file_under_tausik_but_outside_the_projection_blocks — tausik/gates.json блокирует; граница названа в докстринге _projection_prefixes и закреплена тестом ::test_the_boundary_of_the_exclusion_is_named_in_the_docstring: ручная правка ВНУТРИ пяти каталогов побайтово неотличима от авто-экспорта, у незакоммиченной правки нет автора. AC-6: ✓ docs/ru/agent-contract.md, тесты ::test_contract_retires_the_commit_for_the_sake_of_closing_workaround и ::test_contract_names_the_exclusion_and_its_boundary. Регрессия: 1590 passed по срезу state/verify/fileless/gate. ruff clean, mypy clean.
