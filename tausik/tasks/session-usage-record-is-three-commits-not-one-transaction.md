---
slug: session-usage-record-is-three-commits-not-one-transaction
title: "Запись итога смены коммитит три оператора порознь: падение между ними навсегда теряет зеркало завершённой смены"
status: done
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
relevant_files:
  - "scripts/backend_queries_usage.py"
  - "tests/test_usage_events_snapshot_slice.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
  - CLAUDE.md
  - AGENTS.md
scope_paths:
  - "scripts/backend_queries_usage.py"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-07T16:50:59Z"
---

## Goal

НАЙДЕНО РЕВЬЮ ПЯТИ ЗАКРЫТЫХ ЗАДАЧ, СМЕНА #228, чтением собственных правок против механизма транзакций.

session_usage_record описывает ОДИН факт — итог смены — тремя операторами: UPSERT в session_usage_metrics, DELETE прежнего зеркала в usage_events, INSERT нового зеркала. Каждый из них проходит через SQLiteBackend._ex, который коммитит НЕМЕДЛЕННО, если не открыта явная транзакция (project_backend.py:140-144, if not self._in_tx: self._conn.commit()). Явная транзакция здесь не открывается.

ПОСЛЕДСТВИЕ: падение процесса между DELETE и INSERT оставляет авторитетную таблицу с итогом, а зеркало — БЕЗ строки этой смены. Для завершённой смены второго шанса нет: record_to_db больше не вызовется, и зеркало останется пустым навсегда. Отчёт LLM Usage by Model читает теперь именно зеркало (задача usage-events-sums-cumulative-snapshots-as-if-they-were-events), то есть расход такой смены молча выпадет из разбивки по моделям.

ЧЕСТНО О ПРОИСХОЖДЕНИИ: окно существовало и ДО той задачи — UPSERT коммитился, затем INSERT, и падение между ними теряло зеркало точно так же. Добавленный DELETE окно расширил, но не создал. Это не оправдание: три оператора, описывающие один факт, обязаны быть одной транзакцией, и раньше это было не менее верно.

МЕХАНИЗМ УЖЕ ЕСТЬ И ЕГО НАДО ВЗЯТЬ, А НЕ ПИСАТЬ ЗАНОВО: backend_transaction.transaction() — контекстный менеджер, который открывает транзакцию или вкладывается SAVEPOINT в чужую, и его docstring прямо предостерегает от ручного owns_tx = not be._in_tx вокруг begin/commit/rollback.

## Acceptance Criteria

AC1. ТРИ ОПЕРАТОРА — ОДНА ТРАНЗАКЦИЯ. session_usage_record выполняет UPSERT в session_usage_metrics, DELETE прежнего зеркала и INSERT нового внутри ОДНОЙ транзакции, взятой из существующего backend_transaction.transaction() — контекстного менеджера, который открывает свою транзакцию или вкладывается SAVEPOINT в чужую. Ручной owns_tx = not be._in_tx вокруг begin/commit/rollback НЕ пишется: его docstring прямо от этого предостерегает.
AC2. ЧАСТИЧНОГО СОСТОЯНИЯ НЕ ОСТАЁТСЯ. Тест: отказ на INSERT зеркала (подменённый вызов бросает исключение) НЕ оставляет ни осиротевшего UPSERT в session_usage_metrics, ни удалённого прежнего зеркала — база возвращается к состоянию до вызова. Именно эта пара и есть дефект: сегодня DELETE уже закоммичен, когда INSERT падает.
AC3. ВЛОЖЕННОСТЬ В ЧУЖУЮ ТРАНЗАКЦИЮ НЕ ЛОМАЕТСЯ. Тест: вызов session_usage_record ВНУТРИ уже открытой транзакции проходит и не коммитит её преждевременно; внешняя сторона по-прежнему решает, фиксировать или откатывать. Иначе правка починит один путь и сломает другой.
AC4 (НЕГАТИВНЫЙ СЦЕНАРИЙ). Телеметрия не имеет права ронять то, что сопровождает: отказ записи (заблокированная БД, недоступная таблица) не выбрасывает исключение наверх в хук SessionEnd, а сообщает о неудаче — и НЕ докладывает об успехе. Отдельно проверяется, что успешный путь по-прежнему оставляет ровно одну строку зеркала на смену, то есть лечение не отменило исправление предыдущей задачи.
AC5 (БЕЗОПАСНОСТЬ). Транзакция не расширяет область удаления: DELETE остаётся параметризованным и ограниченным session_id и source. Тест на таблице со строками двух источников и нескольких смен утверждает, что откат и фиксация одинаково не задевают чужие строки.

## Plan

## Rollback

git revert <commit>. Правка оборачивает существующие операторы в имеющийся контекстный менеджер; ни схема, ни данные не меняются.

## Journal

- 2026-09-07T16:50:22Z [implementation] — AC-1 (три оператора — одна транзакция): ✓ tests/test_usage_events_snapshot_slice.py::TestTheThreeWritesAreOneTransaction::test_a_failing_mirror_insert_leaves_no_partial_state — взят существующий backend_transaction.transaction(), ручной owns_tx не писался AC-2 (частичного состояния не остаётся): ✓ tests/test_usage_events_snapshot_slice.py::TestTheThreeWritesAreOneTransaction::test_a_failing_mirror_insert_leaves_no_partial_state — подменённый usage_event_append бросает исключение, и после него авторитетная таблица держит ПРЕЖНИЙ итог (1250, не 9999), а прежнее зеркало НЕ удалено AC-3 (вложенность в чужую транзакцию не ломается): ✓ tests/test_usage_events_snapshot_slice.py::TestTheThreeWritesAreOneTransaction::test_the_call_nests_inside_a_transaction_the_caller_owns AC-3: ✓ tests/test_usage_events_snapshot_slice.py::TestTheThreeWritesAreOneTransaction::test_a_committed_outer_transaction_keeps_the_record — проверены ОБЕ стороны вложенности: откат внешней транзакции убирает вложенную запись, фиксация её проносит AC-4 (негативный сценарий — лечение не отменило предыдущее исправление): ✓ tests/test_usage_events_snapshot_slice.py::TestTheThreeWritesAreOneTransaction::test_the_happy_path_still_leaves_exactly_one_mirror_row AC-5 (безопасность — область удаления не расширилась): ✓ tests/test_usage_events_snapshot_slice.py::TestTheThreeWritesAreOneTransaction::test_a_rollback_does_not_touch_other_sessions_or_sources — на таблице со строками двух источников и двух смен откат не задел ни чужую смену, ни строку manual Negative: отказ проверяется НАСТОЯЩИМ исключением из середины блока, а не рассуждением: usage_event_append подменяется бросающей функцией, и утверждается отсутствие ОБОИХ частичных следов — осиротевшего UPSERT и уже выполненного DELETE. Проверена и обратная сторона вложенности (фиксация внешней транзакции проносит запись), иначе тест доказывал бы лишь то, что откат что-то стирает. Отдельно проверено, что счастливый путь по-прежнему оставляет ровно одну строку зеркала — транзакция не имела права отменить замену, ради которой она добавлялась. Domain: дефект не гипотетический и не выдуманный ради теста. SQLiteBackend._ex коммитит каждый оператор, если не открыта явная транзакция (project_backend.py:140-144), а session_usage_record явной транзакции не открывал — это читается в коде, а не предполагается. Последствие адресно: отчёт LLM Usage by Model читает ИМЕННО зеркало (перестановка предыдущей задачи), поэтому потерянная строка означала бы исчезновение расхода целой смены из разбивки по моделям, причём молча и навсегда, потому что record_to_db для завершённой смены больше не вызовется. Честно о происхождении: окно было и до правки этой волны, добавленный DELETE его расширил, но не создал.
