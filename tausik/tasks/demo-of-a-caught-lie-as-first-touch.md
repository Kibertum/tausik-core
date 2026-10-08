---
slug: demo-of-a-caught-lie-as-first-touch
title: "Демка пойманной лжи: первое касание перестаёт быть запретом"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: medium
role: tech-writer
stack: null
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_demo.py"
  - "scripts/gate_project_root.py"
  - "scripts/gate_ruff_format.py"
  - "scripts/gate_test_dedupe.py"
  - "scripts/gate_cross_model_parity.py"
  - "scripts/host_mechanisms.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "tests/test_demo_caught_lie.py"
  - "docs/en/cli-tasks.md"
  - "docs/ru/cli-tasks.md"
  - README.md
  - README.ru.md
  - "changelog.d/demo-of-a-caught-lie-as-first-touch.md"
scope_paths:
  - "scripts/**"
  - "docs/**"
  - README.md
  - README.ru.md
  - "tests/*.py"
  - "changelog.d/"
scope_tools: []
depends_on:
  - readme-is-a-wall-not-a-path
completed_at: "2026-09-29T21:37:59Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#118"
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

Человек за минуту видит, как фреймворк ловит ложное «тесты прошли», вместо того чтобы первым делом получить отказ QG-0.

## Acceptance Criteria

1. Команда демонстрации разыгрывает в песочнице сценарий: агент заявляет «тесты зелёные» без прогона, закрытие отклоняется, квитанция показывает, чего не было. Меньше минуты от запуска до результата.
2. Демка работает БЕЗ ключей LLM и БЕЗ сети. Сценарий заскриптован; демка, требующая ключа, убивает саму идею и считается провалом критерия.
3. GIF сценария стоит первым экраном README, ВЫШЕ инструкции по установке.
4. Названа причина хода: сегодня первое, что получает человек после установки, — запрет QG-0. У соседей первое касание дарит, у нас отнимает.
5. НЕГАТИВНЫЙ сценарий: демка не имеет права показывать возможность, которой нет. Каждый кадр сценария воспроизводится реальным TAUSIK; постановочный вывод ЗАПРЕЩЁН.
6. НЕГАТИВНЫЙ сценарий: демка не оставляет мусора в проекте пользователя — песочница удаляется, .tausik целевого проекта не трогается.

## Plan

## Rollback

Команда demo удаляется; остальное не затронуто

## Journal

- 2026-09-29T21:36:39Z [implementation] — AC-1: ✓ tests/test_demo_caught_lie.py::test_the_demo_behaves_as_it_says_and_leaves_nothing_behind (claim refused by verify-first, real pytest red, fix closes with signed receipt; 9-11s). AC-2: ✓ scripted sandbox, only local git + CLI subprocesses, no network/LLM. AC-3: README.md/README.ru.md open with the REAL transcript above Install — as text, not a GIF (no recorder here; owner to decide on a GIF). AC-4: ✓ reason in module docstring: first touch used to be a QG-0 refusal. AC-5: ✓ each step asserts the real CLI's words (verify-first / FAILED tests/test_calc.py::test_add / Task 'fix-add' completed); a refusal for another cause fails the demo — it caught exactly that (cross_model_parity crash). AC-6: ✓ sandbox removed incl. read-only git objects; test asserts no tausik-demo-* left. Found and fixed on the way: 3 gates rooted at __file__ (ruff_format drive error, test_dedupe, cross_model_parity crash) -> gate_project_root.
- 2026-09-29T21:36:39Z [implementation] — NO-DEAD-END: red runs were real defects the demo exposed (drive-mount relpath, parity crash, silent rmtree), each fixed, not wrong approaches.
