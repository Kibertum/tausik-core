---
slug: session-usage-record-is-three-commits-not-one-transaction
title: "Запись итога смены коммитит три оператора порознь: падение между ними навсегда теряет зеркало завершённой смены"
status: planning
epic: landscape-2026-h2
story: agent-output-discipline
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_queries_usage.py"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО РЕВЬЮ ПЯТИ ЗАКРЫТЫХ ЗАДАЧ, СМЕНА #228, чтением собственных правок против механизма транзакций.

session_usage_record описывает ОДИН факт — итог смены — тремя операторами: UPSERT в session_usage_metrics, DELETE прежнего зеркала в usage_events, INSERT нового зеркала. Каждый из них проходит через SQLiteBackend._ex, который коммитит НЕМЕДЛЕННО, если не открыта явная транзакция (project_backend.py:140-144, if not self._in_tx: self._conn.commit()). Явная транзакция здесь не открывается.

ПОСЛЕДСТВИЕ: падение процесса между DELETE и INSERT оставляет авторитетную таблицу с итогом, а зеркало — БЕЗ строки этой смены. Для завершённой смены второго шанса нет: record_to_db больше не вызовется, и зеркало останется пустым навсегда. Отчёт LLM Usage by Model читает теперь именно зеркало (задача usage-events-sums-cumulative-snapshots-as-if-they-were-events), то есть расход такой смены молча выпадет из разбивки по моделям.

ЧЕСТНО О ПРОИСХОЖДЕНИИ: окно существовало и ДО той задачи — UPSERT коммитился, затем INSERT, и падение между ними теряло зеркало точно так же. Добавленный DELETE окно расширил, но не создал. Это не оправдание: три оператора, описывающие один факт, обязаны быть одной транзакцией, и раньше это было не менее верно.

МЕХАНИЗМ УЖЕ ЕСТЬ И ЕГО НАДО ВЗЯТЬ, А НЕ ПИСАТЬ ЗАНОВО: backend_transaction.transaction() — контекстный менеджер, который открывает транзакцию или вкладывается SAVEPOINT в чужую, и его docstring прямо предостерегает от ручного owns_tx = not be._in_tx вокруг begin/commit/rollback.

## Acceptance Criteria

## Plan

## Rollback

git revert <commit>. Правка оборачивает существующие операторы в имеющийся контекстный менеджер; ни схема, ни данные не меняются.

## Journal
