---
slug: attempts-counter-never-increments
title: "Счётчик попыток всегда равен единице: поле утверждает, что всё сделано с первого раза"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "backend_queries_metrics.py и backend_tier_metrics.py: формула FPSR (attempts=1) НЕ меняется — меняется правдивость её входа; отказ task done по стадиям ac/plan (забытый флаг) попыткой НЕ считается — только записанная красная верификация"
relevant_files:
  - "scripts/service_task.py"
  - "scripts/verify_run_record.py"
  - "tests/test_attempts_counter.py"
  - "tests/test_tausik_service.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_task.py"
  - "scripts/verify_run_record.py"
  - "tests/test_attempts_counter.py"
  - "tests/test_tausik_service.py"
  - "docs/ru/agent-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-03T16:17:49Z"
---

## Goal

ЗАМЕР #189: поле tasks.attempts существует и заполняется единицей. Из 1239 закрытых задач attempts > 1 ровно у ОДНОЙ. Счётчик попыток не двигается никогда — при повторном заходе, при разблокировке, при возобновлении после провала.
ПОЧЕМУ ЭТО НЕ МЕЛОЧЬ, А ТИХАЯ ОШИБКА: поле показывается в выводе `task show` и читается как факт («attempts: 1»), то есть утверждает, что задача сделана с первой попытки — даже когда попыток было три. Это ложное утверждение о собственной истории, выданное машиной, а не человеком.
ЦЕНА, УЖЕ ЗАПЛАЧЕННАЯ: в этой же сессии я едва не построил на нём триггер записи отрицательного знания («спроси на второй попытке») — механизм оказался бы мёртвым с рождения, и обнаружилось бы это не скоро. Замер спас, но следующий может не померить.
ЧТО ДЕЛАЕТСЯ: либо счётчик начинает считать (инкремент при повторной активации, при разблокировке, при провале verify по активной задаче), либо поле УДАЛЯЕТСЯ вместе с его выводом. Третьего не дано: поле, которое всегда показывает единицу, обязано либо стать правдой, либо исчезнуть.
НЕГАТИВНОЕ: если выбран инкремент — существующие 1239 закрытий НЕ переписываются задним числом; историческое значение остаётся единицей и это честно, потому что данных о прошлых попытках нет. Различать «одна попытка» и «не считалось» обязано само поле.

## Acceptance Criteria

AC1 ПЕРЕДИАГНОЗ ЗАПИСАН (память #530): инкремент при task start существует с v1.0.0 (service_task.task_start, «attempt #N»); не считаются РАЗБЛОКИРОВКА (task_unblock ставит active напрямую) и КРАСНАЯ ВЕРИФИКАЦИЯ активной задачи (verify --task с exit != 0, включая отказ гейтов task-done) — именно они и есть повторные попытки.
AC2 ВЫБРАН ИНКРЕМЕНТ, НЕ ИЗЪЯТИЕ. Попытка = активация (start, unblock) ИЛИ проваленная верификация активной задачи; единственная точка записи verification_runs (_record_verification) двигает счётчик, чтобы CLI и MCP не разошлись. Зелёная верификация, верификация неактивной задачи, отсутствие таблицы tasks (фикстура) — счётчик не трогают.
AC3 ИСТОРИЯ НЕ ПЕРЕПИСЫВАЕТСЯ: существующие значения остаются; attempts=0 значит «не активировалась/не считалось», attempts=1 — одна активация без красной верификации. Задокументировано в docs/ru/agent-contract.md у строки FPSR (FPSR по смыслу становится строже — сказано в CHANGELOG).
AC4 ТЕСТЫ tests/test_attempts_counter.py через ProjectService и реальную запись verification_runs: start=1; unblock=+1; красная верификация активной=+1; зелёная=0; красная по done-задаче=0; повторный start после block через unblock даёт последовательность 1,2; FPSR-запрос читает результат.
AC5 МУТАЦИИ: снять инкремент в unblock; снять условие exit_code != 0; снять условие status='active' — каждая убита названным тестом.
AC6 scoped verify зелёный, полная лента один раз со строкой passed/failed, ruff/mypy чисто, CHANGELOG.md и CHANGELOG.ru.md синхронно, bootstrap --ide all перед done.

## Plan

## Rollback

Инкремент существующего поля либо его изъятие вместе с выводом. Откат — git revert; исторические значения не переписываются ни в одну сторону.

## Journal

- 2026-09-03T16:12:17Z [implementation] — ИНВЕНТАРЬ ПО ВЫЗОВУ: точки, меняющие tasks.attempts — service_task.task_start (+1, с v1.0.0); точки, где происходит повторная попытка без счёта — service_task.task_unblock (status=active напрямую) и verify_run_record._record_verification (единственная точка записи verification_runs; сюда приходят verify --task из CLI и MCP, и прогон гейтов task-done через verify_cached_run). Читатели: backend_queries_metrics (FPSR attempts=1), backend_tier_metrics, project_cli_task (task show печатает только ненулевое), state_export (не едет в git). Существующий тест test_multiple_attempts ЗАКРЕПЛЯЛ дефект: ожидал 2 при start-block-unblock-start; теперь 3 — ожидание переписано с объяснением, файл добавлен в рамки.
- 2026-09-03T16:14:12Z [implementation] — МУТАЦИИ 4/4 УБИТЫ: (1) unblock не считает — test_unblock_is_a_re_activation_and_counts + test_multiple_attempts; (2) снято условие exit_code != 0 — test_a_green_run_does_not; (3) снято условие status='active' — test_a_red_run_after_close_leaves_history_alone, test_a_red_run_on_a_task_not_in_flight_does_not; (4) вызов счётчика снят из точки записи — 3 теста, включая FPSR-запрос. Оговорка #536: мутации автора. Root cause (logic-error): понятие «попытка» было реализовано как «активация через task start» и только; разблокировка и красная верификация — две обычные формы повторной попытки — счётчик не двигали, а метрика FPSR читала поле как правду. Prevention: у поля, которое печатается как факт, перечислять СОБЫТИЯ, его меняющие, по вызову; каждое событие — тест; метрику проверять на входе с известной историей.
- 2026-09-03T16:16:48Z [implementation] — Verification checklist: AC-1: ✓ передиагноз в журнале (инвентарь по вызову). AC-2: ✓ tests/test_attempts_counter.py::TestRedVerificationCounts::test_a_red_run_on_the_active_task_counts. AC-3: ✓ tests/test_attempts_counter.py::TestRedVerificationCounts::test_a_red_run_after_close_leaves_history_alone. AC-4: ✓ tests/test_attempts_counter.py::TestActivationsCount::test_unblock_is_a_re_activation_and_counts. AC-5: ✓ мутации 4/4 в журнале. AC-6: ✓ verification_run #1995 green; полная лента 8618 passed / 25 skipped / 0 failed (строка прочитана); ruff и mypy чисто. Domain: следующая задача, дважды провалившая verify, покажет attempts 3 в task show и не войдёт в FPSR как «с первой попытки» — ровно то, что триггер отрицательного знания из #189 хотел прочитать.
