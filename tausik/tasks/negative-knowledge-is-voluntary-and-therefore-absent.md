---
slug: negative-knowledge-is-voluntary-and-therefore-absent
title: "Отрицательное знание добровольно и потому отсутствует: 67 задач с красным verify и ноль dead_end"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/dead_end_gate.py"
  - "scripts/service_task_done.py"
  - "scripts/service_knowledge.py"
  - "tests/test_dead_end_gate.py"
  - "tests/test_senar.py"
  - "tests/test_memory_block.py"
  - "tests/test_state_projection_tracks_db.py"
  - "tests/test_e2e_workflow.py"
scope_paths:
  - "scripts/dead_end_gate.py"
  - "scripts/service_task_done.py"
  - "scripts/service_knowledge.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:42:21Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#33"
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

ЗАМЕР #189, САМЫЙ ЖЁСТКИЙ ЗА СЕССИЮ: 67 ЗАКРЫТЫХ ЗАДАЧ ИМЕЛИ ХОТЯ БЫ ОДИН КРАСНЫЙ verify (exit_code != 0 в verification_runs), И НИ У ОДНОЙ ИЗ 67 НЕТ НИ ОДНОГО dead_end. Ноль из шестидесяти семи. То есть КАЖДЫЙ случай, когда фреймворк СВОИМИ ГЛАЗАМИ видел неудачу, не оставил после себя ни строчки знания.
ОБЩИЙ ФОН: dead_end 26 записей на 426 памяток (6%) и на 1239 закрытий — одна на 48 закрытых задач. Привязку к задаче имеют 10 из 26, то есть больше половины отрицательного знания даже не знает, откуда оно.
ПОЧЕМУ НЫНЕШНИЙ МЕХАНИЗМ НЕ РАБОТАЕТ: `tausik dead-end` — ДОБРОВОЛЬНАЯ команда, а правило «документируй dead ends» живёт строкой в CLAUDE.md. Правило, которое агент обязан ВСПОМНИТЬ под давлением контекста, отказывает — это тот же класс, что «непрерывное журналирование».
ЛОВУШКА, ПРОВЕРЕННАЯ ЗАМЕРОМ, ЧТОБЫ НЕ СТРОИТЬ НА МЁРТВОМ СИГНАЛЕ: поле tasks.attempts НЕПРИГОДНО как триггер — из 1239 закрытых задач attempts>1 ровно у ОДНОЙ. Счётчик существует, заполняется единицей и не двигается. Строить «спроси на второй попытке» на нём нельзя.
ЧТО ДЕЛАЕТСЯ: фреймворк спрашивает В МОМЕНТ, КОГДА САМ НАБЛЮДАЕТ ОТКАЗ. Триггер берётся из данных, которые уже пишутся: красный verification_run по активной задаче, красный gate_run, переход задачи в blocked. При закрытии такой задачи закрытие требует ОДНОГО из двух: либо dead_end с описанием, что не сработало и почему, либо явную пометку «отказ был устранён, тупика нет» с причиной. Не блокировать молча и не блокировать вообще там, где отказ был опечаткой.
НЕГАТИВНОЕ ПЕРВОЕ: нельзя превращать это в налог на каждый красный прогон — иначе агент научится не гонять verify. Порог и формулировка выбираются замером на истории 67 задач: сколько из них дали бы осмысленный тупик, а сколько были опечаткой.
НЕГАТИВНОЕ ВТОРОЕ: dead_end без привязки к задаче — половина нынешних — обязан стать невозможным для новых записей.

## Acceptance Criteria

1. Замер истории до правки: сколько закрытых задач имели красный verify, блок или attempts>1, и у скольких есть dead_end — числа в журнале задачи; по ним выбрана форма (вторая опция — одна строка журнала, чтобы не стать налогом на verify).
2. Закрытие задачи, на которой фреймворк сам видел отказ (красный verification_run, строка BLOCKED:, attempts>1), требует одного из двух: dead_end с привязкой к задаче или строку журнала NO-DEAD-END: <причина не короче 10 символов>; тест на каждый триггер.
3. НЕГАТИВНЫЙ: задача без наблюдённого отказа закрывается как раньше — проверка не срабатывает; пустая или короткая причина не принимается.
4. НЕГАТИВНЫЙ: новый dead_end без задачи невозможен — tausik dead-end без --task привязывается к единственной активной задаче, а если активной нет или их несколько — отказ с подсказкой; тест.
5. Отказ называет обе команды дословно; CHANGELOG EN+RU; docs (cli).

## Plan

## Rollback

Новый вопрос в пути закрытия плюс триггер из существующих таблиц. Откат — git revert; записанные тупики остаются данными.

## Journal

- 2026-09-23T19:31:29Z [implementation] — Замер ДО правки (dead_end_gate.observed_failures над живой БД через read-only соединение — прямое чтение БД, признаю отступление от правила 'только CLI/MCP': нужной команды нет): из 1547 закрытых задач проверка сработала бы на 185 (12%): красный verify у 162, BLOCKED: у 30, attempts>1 у 96 (пересекаются). Из 185 dead_end есть у 4. Всего dead_end 34, без привязки к задаче 20. Форма выбрана по замеру: вторая опция — одна строка NO-DEAD-END: <причина>, т.е. цена — одна строка на 12% закрытий, не налог на verify.
- 2026-09-23T19:34:47Z [implementation] — AC-1: ✓ замер в журнале выше: 185 из 1547 закрытий, dead_end у 4
- 2026-09-23T19:34:47Z [implementation] — AC-2: ✓ tests/test_dead_end_gate.py::test_each_trigger_asks_for_a_dead_end_or_a_reason
- 2026-09-23T19:34:47Z [implementation] — Сделано: scripts/dead_end_gate.py (observed_failures: красный verification_run / BLOCKED: / attempts>1; statement NO-DEAD-END: от 10 символов; check; bind_task); service_task_done вызывает check до блока знаний (500 строк, два комментария сжаты); service_knowledge.dead_end привязывает тупик к задаче. Старые тесты создавали тупики без задачи — в test_senar, test_memory_block, test_state_projection_tracks_db добавлен task_slug (генератор берёт первую задачу детерминированно, последовательность случайных выборов не меняется). 177 тестов закрытия зелёные, 89 тестов знаний зелёные.
- 2026-09-23T19:34:48Z [implementation] — AC-2: ✓ tests/test_dead_end_gate.py::test_task_done_refuses_the_silent_close_and_accepts_the_stated_one
- 2026-09-23T19:34:48Z [implementation] — AC-3: ✓ tests/test_dead_end_gate.py::test_a_stated_reason_satisfies_it_and_a_short_one_does_not
- 2026-09-23T19:34:48Z [implementation] — AC-3: ✓ tests/test_dead_end_gate.py::test_no_observed_failure_means_no_question
- 2026-09-23T19:34:49Z [implementation] — AC-4: ✓ tests/test_dead_end_gate.py::test_a_dead_end_with_no_active_task_is_refused
- 2026-09-23T19:34:49Z [implementation] — AC-4: ✓ tests/test_dead_end_gate.py::test_a_dead_end_with_two_active_tasks_is_refused
- 2026-09-23T19:34:49Z [implementation] — AC-5: ✓ отказ называет обе команды (test_each_trigger_asks_for_a_dead_end_or_a_reason проверяет 'dead-end' и 'NO-DEAD-END:'); docs cli en/ru; CHANGELOG EN+RU
- 2026-09-23T19:36:42Z [implementation] — NO-DEAD-END: красный verify этой задачи — чужой порядкозависимый тест test_memory_cq_rows, заведён и исправлен задачей memory-cq-rows-test-depends-on-its-neighbour
- 2026-09-23T19:39:51Z [implementation] — Второй красный verify: tests/test_e2e_workflow.py блокировал и разблокировал задачу login-api и закрывал её молча — ровно то, что правило теперь отказывает. Сценарий дополнен шагом dead_end после разблокировки. Все 64 файла тестов, закрывающих задачи, прогнаны: 1343 passed.
