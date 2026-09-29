---
slug: cli-reference-is-cut-by-measured-use
title: "Справочник CLI разрезан по замеренному использованию: 12 команд из 6930 вызовов ведут страницу, остальное — по задачам читателя"
status: done
epic: release-110-deferred-from-19
story: release110-docs-are-legible-to-an-outsider
complexity: medium
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "docs/en/cli-admin.md"
  - "docs/en/cli-knowledge.md"
  - "docs/en/cli-quality.md"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-admin.md"
  - "docs/ru/cli-knowledge.md"
  - "docs/ru/cli-quality.md"
  - "docs/ru/cli-tasks.md"
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - "docs/en/skill-ecosystem.md"
  - "docs/ru/skill-ecosystem.md"
  - "docs/en/task-archive-spec.md"
  - "docs/ru/task-archive-spec.md"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - "docs/en/verify-glossary.md"
  - "docs/ru/verify-glossary.md"
  - "docs/_generated/doc-map.md"
  - "scripts/gate_doc_coverage.py"
  - "tests/test_doc_coverage_gate.py"
  - "tests/test_doc_internal_refs.py"
  - "tests/test_mcp_cli_only.py"
  - "tests/test_direct_edit_recognized_case.py"
  - "tests/test_gates_catch_their_violation.py"
  - "tausik/gates.json"
scope_paths:
  - "docs/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/gate_doc_coverage.py"
  - "tests/test_doc_coverage_gate.py"
  - "tests/test_doc_internal_refs.py"
  - "tests/test_mcp_cli_only.py"
  - "tests/test_direct_edit_recognized_case.py"
  - "tests/test_gates_catch_their_violation.py"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T16:07:37Z"
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

Читатель, открывший справочник CLI, за первый экран видит команды, которыми реально пользуются, а не 899 строк, где 74 команды весят одинаково. Замер: 12 инструментов дают 81% из 6930 вызовов поверхности, 28 дают 95%.

## Acceptance Criteria

AC-1 docs/ru/cli.md и docs/en/cli.md не длиннее 200 строк каждая и начинаются с замеренного рабочего набора: 12 команд, 81% из 6930 вызовов, с названным основанием замера.
AC-2 Остальные разделы перенесены ДОСЛОВНО в четыре страницы по задачам читателя (задачи, качество, знания, обслуживание) на каждом языке; документация ни одной команды не потеряна.
AC-3 gate_doc_coverage проверяет поверхность CLI против ГРУППЫ страниц на язык, а не против одного файла; независимость ru и en сохранена.
AC-4 НЕГАТИВНЫЙ СЛУЧАЙ: команда, удалённая из ВСЕЙ группы страниц, даёт ОШИБКУ гейта с названным именем и языком — иначе группа делает гейт зелёным по построению. Тест доказывает это на подложенном дереве.
AC-5 НЕГАТИВНЫЙ СЛУЧАЙ: страница группы, которой нет на диске, даёт ошибку гейта, а не молчаливый пропуск.
AC-6 Все якорные ссылки с других страниц ведут в раздел на его новой странице.
AC-7 Полная лента тестов зелёная.

## Plan

## Rollback

git revert коммита; страницы и гейт возвращаются к одному файлу

## Journal

- 2026-09-29T15:53:22Z [implementation] — Справочник разрезан: cli.md (899 строк) -> вход 56 строк + четыре страницы по задачам читателя на каждом языке, текст перенесён дословно скриптом. Гейт doc_coverage научен ГРУППЕ страниц на язык; причина, по которой файл был один, была именно в гейте — отсюда раздел «Команды, не попавшие в разделы выше». Якоря с 10 страниц перенацелены. Храповик ссылок затянут 52/26 -> 45/24.
- 2026-09-29T16:05:32Z [implementation] — AC-1 ✓ docs/ru/cli.md 59 строк, docs/en/cli.md 60 (было 900 и 905); первый экран — замеренный рабочий набор: 12 команд, 81% из 6930 вызовов поверхности, основание названо (usage_events этого проекта, 74 разных инструмента). AC-2 ✓ 30 разделов перенесены СКРИПТОМ дословно на cli-tasks/quality/knowledge/admin на каждом языке; doc_coverage зелёный на живом дереве = ни одна из 54 команд не потеряна. AC-3 ✓ COVERED принимает страницу ИЛИ группу; CLI_PAGES_RU/EN — две независимые группы. AC-4 ✓ test_a_command_on_no_page_of_the_group_is_refused на подложенном дереве; плюс test_the_two_languages_do_not_cover_for_each_other — язык, документировавший команду, не обвиняется. AC-5 ✓ test_a_page_of_the_group_that_is_absent_is_a_gap: пропавшая страница — пробел, а не группа поменьше. AC-6 ✓ 12 якорных ссылок с 10 страниц перенацелены, grep 'cli.md#' даёт 0. AC-7 ✓ полная лента 12400 passed, 34 skipped, 0 deselected. НАЙДЕНО: причина, по которой справочник был одним файлом на 899 строк — ЭТОТ ЖЕ ГЕЙТ, он требовал упоминания каждой команды в ОДНОМ файле, отсюда раздел «Команды, не попавшие в разделы выше» на 57 строк. ПОБОЧНО: четыре теста адресовали справочник как один файл и покраснели на ПЕРЕЕЗД, а не на предмет охраны — добавлен общий адрес gate_doc_coverage.cli_reference_text(root, lang); тест test_mcp_cli_only требовал номера решения на пользовательской странице, требование снято, остался scripts/mcp_cli_only.py — адрес, который читатель может открыть. Храповик doc_internal_refs затянут 52/26 → 45/24.
- 2026-09-29T16:07:33Z [implementation] — AC-1 ✓ docs/ru/cli.md 59 строк, docs/en/cli.md 60 (было 900 и 905); первый экран — замеренный рабочий набор: 12 команд, 81% из 6930 вызовов поверхности, основание названо (usage_events этого проекта, 74 разных инструмента). AC-2 ✓ 30 разделов перенесены СКРИПТОМ дословно на cli-tasks/quality/knowledge/admin на каждом языке; doc_coverage зелёный на живом дереве — ни одна из 54 команд не потеряна. AC-3 ✓ COVERED принимает страницу ИЛИ группу; CLI_PAGES_RU/EN — две независимые группы. AC-4 ✓ test_a_command_on_no_page_of_the_group_is_refused на подложенном дереве; плюс test_the_two_languages_do_not_cover_for_each_other — язык, документировавший команду, не обвиняется. AC-5 ✓ test_a_page_of_the_group_that_is_absent_is_a_gap: пропавшая страница — пробел, а не группа поменьше. AC-6 ✓ 12 якорных ссылок с 10 страниц перенацелены, grep 'cli.md#' даёт 0. AC-7 ✓ полная лента 12400 passed, 34 skipped, 0 deselected. НАЙДЕНО: причина, по которой справочник был одним файлом на 899 строк — ЭТОТ ЖЕ ГЕЙТ, он требовал упоминания каждой команды в ОДНОМ файле, отсюда раздел «Команды, не попавшие в разделы выше» на 57 строк, который сам себя объясняет замером. ПОБОЧНО: четыре теста адресовали справочник как один файл и покраснели на ПЕРЕЕЗД, а не на предмет охраны — добавлен общий адрес gate_doc_coverage.cli_reference_text(root, lang); тест test_mcp_cli_only требовал номер решения на пользовательской странице, требование снято, остался scripts/mcp_cli_only.py — адрес, который читатель может открыть. Храповик doc_internal_refs затянут 52/26 → 45/24.
