---
slug: memory-record-does-not-say-where-its-claim-came-from
title: "Запись памяти не говорит, откуда взялось её утверждение: выведенное агентом неотличимо от проверенного"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/memory_provenance.py"
  - "scripts/backend_migrations_v65.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_crud_knowledge.py"
  - "scripts/service_knowledge.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/render_memory.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers_knowledge.py"
  - "tests/test_memory_provenance.py"
  - "tests/test_memory_injection_flattening.py"
scope_paths:
  - "scripts/**"
  - "harness/**"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:54:05Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#30"
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

Каждая запись памяти несёт происхождение утверждения — наблюдалось, выведено или сказано человеком, — и session-блок различает их, потому что тезис «слова превращаются в проверяемое» обязан распространяться и на память, а не только на квитанции.

## Acceptance Criteria

1. Колонка provenance со значениями observed | inferred | told; миграция ставит существующим записям inferred, потому что задним числом доказать наблюдение нельзя, а объявить его — значит соврать про весь прошлый корпус.
2. Параметр проброшен в CLI `memory add` и в MCP tausik_memory_add; значение по умолчанию inferred, а не observed — умолчание обязано быть СЛАБЫМ утверждением.
3. ЗУБ, без которого задача не делается вовсе: memory_posttool_audit проверяет, что запись с provenance=observed ссылается на проверяемое — лог задачи, квитанцию или прогон. Не ссылается — понижается до inferred, и об этом сказано вслух. Без этой проверки поле выродится в шум за неделю, и тогда лучше не заводить его совсем.
4. Session-блок помечает inferred-записи маркером, чтобы будущий агент видел разницу между «мы это померили» и «кто-то так решил».
5. `memory lint` показывает старые inferred-записи без подтверждения как долг.
6. НЕГАТИВНЫЙ сценарий: тест доказывает, что запись observed БЕЗ ссылки на проверяемое действительно понижается, — иначе зуб декларативный.
7. НЕГАТИВНЫЙ сценарий: миграция не переписывает и не теряет ни одной существующей записи; проверяется счётом до и после и сверкой контрольной выборки.

## Plan

## Rollback

git revert коммита и миграции; колонка остаётся с дефолтом inferred

## Journal

- 2026-09-23T19:46:47Z [implementation] — Сделано: миграция v65 (memory.provenance NOT NULL DEFAULT inferred CHECK observed|inferred|told; во fresh-схеме колонка последней); scripts/memory_provenance.py (backing: тест/verify #N/задача с журналом; settle понижает observed без опоры и говорит об этом); backend/service/CLI --provenance/MCP provenance (описание инструмента сокращено, чтобы оплатить параметр: поверхность в пределах 56907); блок памяти помечает inferred знаком ≈; memory lint — строка 'Provenance debt'. Отступление от формулировки AC-3: проверка стоит в memory_add (в момент записи), а не в хуке memory_posttool_audit — тот хук проверяет файлы auto-memory Claude, а не записи TAUSIK. Живая миграция: до — schema 64, 711 записей, хэш содержимого 2e3a7679de0c4e22; после — schema 65, 711 записей, тот же хэш, provenance inferred у всех 711.
- 2026-09-23T19:46:48Z [implementation] — AC-1: ✓ tests/test_memory_provenance.py::test_the_migration_keeps_every_row_and_marks_it_inferred
- 2026-09-23T19:46:48Z [implementation] — AC-2: ✓ tests/test_memory_provenance.py::test_the_default_is_the_weak_claim
- 2026-09-23T19:46:48Z [implementation] — AC-3: ✓ tests/test_memory_provenance.py::test_observed_naming_a_test_or_a_run_stays_observed
- 2026-09-23T19:46:49Z [implementation] — AC-3: ✓ tests/test_memory_provenance.py::test_observed_linked_to_a_task_with_a_journal_stays_observed
- 2026-09-23T19:46:49Z [implementation] — AC-4: ✓ tests/test_memory_provenance.py::test_the_block_marks_inferred_records_and_not_observed_ones
- 2026-09-23T19:46:49Z [implementation] — AC-5: ✓ tests/test_memory_provenance.py::test_lint_counts_inferred_records_as_debt
- 2026-09-23T19:46:50Z [implementation] — AC-6: ✓ tests/test_memory_provenance.py::test_observed_backed_by_nothing_is_downgraded_out_loud
- 2026-09-23T19:46:50Z [implementation] — AC-7: ✓ tests/test_memory_provenance.py::test_the_migration_keeps_every_row_and_marks_it_inferred (25 строк, хэш до=после) и живой замер 711=711
- 2026-09-23T19:48:33Z [implementation] — NO-DEAD-END: красный verify — тест test_memory_injection_flattening перечисляет собственные строки блока памяти, а легенда ≈ — новая собственная строка; добавлена в перечень
