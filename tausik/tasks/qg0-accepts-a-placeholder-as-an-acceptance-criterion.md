---
slug: qg0-accepts-a-placeholder-as-an-acceptance-criterion
title: "QG-0 принимает заглушку за критерий приёмки: он считает ключевые слова, но не вещество"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/ac_placeholder.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_ac_evidence.py"
  - "tests/test_ac_placeholder.py"
  - "tests/test_tausik_cli.py"
  - "tests/conftest.py"
  - pyproject.toml
scope_paths:
  - "scripts/ac_placeholder.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_ac_evidence.py"
  - "tests/*.py"
  - pyproject.toml
  - "CHANGELOG*.md"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:39:05Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#15"
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

Критерий приёмки, состоящий из шаблона, TODO или незаполненной таблицы доказательств, не проходит QG-0 — гейт измеряет вещество, а не наличие строки.

## Acceptance Criteria

1. Детектор ловит три семьи заглушек: шаблонные скобки (<...>, [ВЕРХНИЙ_РЕГИСТР], {{...}}), слова-обещания (TODO, TBD, NEEDS CLARIFICATION, «уточнить», «заглушка») и НЕЗАПОЛНЕННУЮ таблицу доказательств (строка-шапка плюс строка-разделитель без данных). Источник разбиения — check-context-budget.mjs из github.com/kiaquila/unicorn-hub (MIT).
2. Шаблон ВЫЧИЩАЕТСЯ перед измерением вещества, а не считается его частью: раздел, состоящий из одной шапки таблицы, читается как пустой, а не как заполненный.
3. Правило применяется к тем же полям, что уже проверяет QG-0: goal и acceptance_criteria, — и к evidence-строкам, которые читает детектор доказательств при закрытии.
4. Порог вещества назван числом и обоснован замером на ЗАКРЫТЫХ задачах проекта, а не выбран на глаз.
5. НЕГАТИВНЫЙ сценарий: точность измерена на живых данных — прогон по всем закрытым задачам БД. Критерий «1. Работает корректно 2. Ошибка при пустом поле» обязан быть ОТВЕРГНУТ; ни один реальный критерий закрытой задачи не должен получить ложную тревогу (конвенция #351).
6. НЕГАТИВНЫЙ сценарий: детектор проверен мутациями — тест, доказывающий, что он способен УПАСТЬ, а не только зеленеть.
7. НЕГАТИВНЫЙ сценарий: русский и английский текст обрабатываются одинаково; заглушка, написанная по-русски, отвергается наравне с английской (паритет, как в конвенции #170).

## Plan

## Rollback

git revert коммита; детектор отключается ключом конфига

## Journal

- 2026-09-23T22:33:05Z [implementation] — test_full_lifecycle red was NOT this task: the ruff_format gate (closed earlier this session) carries a verify trigger, so a fixture that switched off pytest/ruff/filesize now had a verify gate again and Verify-First refused the fileless close. Fixture tests/test_tausik_cli.py::tausik_env now also disables ruff_format; 31/31 slow CLI tests pass.
- 2026-09-23T22:37:05Z [implementation] — AC-1: ✓ tests/test_ac_placeholder.py::test_each_placeholder_family_carries_no_substance — ten families incl. <...>, [UPPER], {{...}}, TODO/TBD/уточнить/заглушка, empty table
- 2026-09-23T22:37:05Z [implementation] — AC-2: ✓ tests/test_ac_placeholder.py::test_a_table_with_data_keeps_its_rows — the header-only table reads as empty, a table with a data row keeps its words
- 2026-09-23T22:37:06Z [implementation] — AC-3: ✓ tests/test_ac_placeholder.py::test_task_start_refuses_a_placeholder_criterion and tests/test_ac_placeholder.py::test_evidence_is_read_with_placeholders_removed — goal+AC at QG-0 and evidence lines at close (service_ac_evidence reads the stripped unit; a bare manual/review claim under 4 words is checkmark_only)
- 2026-09-23T22:37:06Z [implementation] — AC-4: ✓ measurement — threshold MIN_AC_WORDS=5, MIN_GOAL_WORDS=3 from the closed tasks: thinnest real criteria 9 words, thinnest real goal 3; docstring of scripts/ac_placeholder.py records it
- 2026-09-23T22:37:06Z [implementation] — AC-5: ✓ measurement — live run over 1451 tasks with goal+AC: 1 refused (ddl-parity-marker-leak-and-column-miscount, AC literally $(cat /tmp/ac.txt)); tests/test_ac_placeholder.py::test_refusal_separates_templates_from_terse_real_criteria refuses «1. Работает корректно 2. Ошибка при пустом поле». Evidence side over 1566 done tasks: coverage unchanged, 2 lines downgraded (both bare claims)
- 2026-09-23T22:37:07Z [implementation] — AC-6: ✓ tests/test_ac_placeholder.py::test_task_start_refuses_a_placeholder_criterion — mutation (gate hook disabled with 'if False and') turned it red: 1 failed, 18 passed; restored
- 2026-09-23T22:37:07Z [implementation] — AC-7: ✓ tests/test_ac_placeholder.py::test_refusal_separates_templates_from_terse_real_criteria — RU and EN templates refused alike, terse real RU and EN criteria accepted; negative: placeholder refused at task start
- 2026-09-23T22:37:07Z [implementation] — NO-DEAD-END: the one red run (test_full_lifecycle) was the ruff_format verify trigger from an earlier task meeting a fixture that disabled only pytest/ruff/filesize, not a wrong approach here
