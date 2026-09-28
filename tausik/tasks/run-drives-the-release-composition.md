---
slug: run-drives-the-release-composition
title: "Скилл /run ведёт состав релиза из БД и закрывает задачи в одном ходу"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/skills/run/SKILL.md"
  - "bootstrap/bootstrap_config.py"
  - "tests/test_run_skill_contract.py"
scope_paths:
  - "harness/**"
  - "bootstrap/*.py"
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-27T18:32:04Z"
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

ТРЕТЬЯ ИЗ ПЯТИ ЗАДАЧ АВТОНОМНОСТИ — ядро драйвера (ревью смены #277).

НАЙДЕНО РЕВЬЮ: механизм автономности СУЩЕСТВУЕТ, но в kiberza, а не в core. Там скилл /run (214 строк) разбирает plan.md со слагами и проходит task → реализация → task done последовательно В ОДНОМ ХОДУ, с hard-stop на первом отказе и одним сводным handoff на батч. В core такого скилла нет вовсе: список — checkpoint, commit, debug, end, explore, i-have-adhd, interview, plan, reason, review, ship, start, task, test. То есть автономность у core записана ИНСТРУКЦИЕЙ в CLAUDE.md, а инструкция без механизма — ровно то, против чего проект строит храповики.

ЧТО У KIBERZA УЖЕ ХОРОШО и переносится: контракт разбора плана, hard-stop без авто-повторов, один сводный handoff вместо одного на задачу, прямой запрет применять режим к задачам, требующим суждения владельца.

ЧТО СДЕЛАТЬ ЛУЧШЕ, три отличия. Первое: источник истины — СОСТАВ РЕЛИЗА В БД, а не файл plan.md; у core уже есть `task next` с порядком «релиз первым, затем объявленный порядок», и дублировать его файлом значит заводить вторую правду. Второе: предел не «5 задач», а «пока состав не пуст ИЛИ не исчерпан контекст» — иначе это батч, а не автономность. Третье: перед каждой задачей сверяться с планом заново, потому что состав мог измениться закрытием предыдущей.

ЗАВИСИМОСТИ ЖЁСТКИЕ: без бюджета журнала (journal-and-changelog-have-a-budget) прогон задохнётся на контексте — замер смены #277 даёт 7407 символов журнала на задачу, то есть 20 задач это 150 тысяч символов. Без жёсткого потолка вызовов (call-budget-is-armed-in-autonomous-mode) сожжёт смену на одной задаче. Делать третьей.

## Acceptance Criteria

AC-1 Скилл /run существует в core и ведёт состав ИЗ БД: перед каждой задачей спрашивает у плана, что дальше, а не читает файл. Второй правды в виде plan.md не заводится. AC-2 Предел не пять задач: прогон идёт, пока состав предлагает задачу И не взведён ни один стоп. AC-3 HARD-STOP на первом отказе, без авто-повторов, с названием отказавшей задачи и причины. AC-4 Взводит потолок вызовов на время прогона и проверяет его ПОСЛЕ каждого закрытия командой `task budget-check`; ненулевой код равен отказу. AC-5 Один сводный handoff на прогон, а не один на задачу: у каждой задачи свой уже есть. AC-6 НЕГАТИВ: режим прямо ЗАПРЕЩЁН для задач, требующих суждения владельца, и это написано в скилле, а не подразумевается. AC-7 НЕГАТИВ: скилл не подменяет /task — он его ВЫЗЫВАЕТ, поэтому QG-0, QG-2, бюджет журнала и сигнал плана работают как при ручной работе. Ни одна проверка не обходится. AC-8 Скилл ставится в порождаемый набор, то есть уезжает в каждый проект на TAUSIK, а не живёт только в core.

## Plan

## Rollback

Новый скилл в harness плюс регистрация; откат — git revert, автономного режима снова нет.

## Journal

- 2026-09-27T18:25:19Z [implementation] — AC-1: ✓ tests/test_run_skill_contract.py::TestTheLoopAsksThePlanEveryTime — источник истины `task next`, спрашивается ПЕРЕД КАЖДОЙ задачей; plan.md как вторая правда не заведён.
- 2026-09-27T18:25:19Z [implementation] — AC-2: ✓ все четыре состояния состава разобраны отдельно (test_all_four_backlog_states_are_handled): ready ведёт дальше, all-blocked, all-claimed и empty останавливают по разным причинам. «Всё занято» не то же, что «ничего не осталось».
- 2026-09-27T18:25:20Z [implementation] — AC-3: ✓ tests/test_run_skill_contract.py::TestTheStopsAreNamed — hard-stop и прямой запрет авто-повторов: повтор, сработавший со второго раза, прячет флаки.
- 2026-09-27T18:25:20Z [implementation] — AC-4: ✓ там же — прогон ВЗВОДИТ потолок и ЧИТАЕТ его: взведение без проверки украшение. Проверено и то, что ответ читается кодом выхода, потому что команда молчит при успехе.
- 2026-09-27T18:25:20Z [implementation] — AC-5: ✓ test_one_handoff_per_run_not_per_task.
- 2026-09-27T18:25:20Z [implementation] — AC-6: ✓ test_it_forbids_itself_for_judgement_calls — запрет на задачи, требующие суждения, написан прямо, с перечислением класса: архитектура, миграции, деньги, доступ.
- 2026-09-27T18:25:20Z [implementation] — AC-7: ✓ test_it_does_not_replace_the_task_skill и test_it_forbids_force — драйвер ВЫЗЫВАЕТ /task, поэтому QG-0, ACL области, бюджет журнала и сигнал плана остаются в цикле.
- 2026-09-27T18:25:21Z [implementation] — AC-8: ✓ test_it_is_registered_as_a_core_skill и test_it_reaches_the_deployed_profile — скилл в core_skills и развёрнут в .claude/skills/run, то есть уезжает в каждый проект, а не живёт в core.
- 2026-09-27T18:25:21Z [implementation] — Domain: скилл проверен развёрткой, а не только чтением — `bootstrap --ide all` положил его в .claude/skills/run, и гейты скиллов (spec conformance, gotchas, no-boilerplate, coverage, catalog) зелёные. Первый прогон гейтов отказал на отсутствии раздела Gotchas, и это правильный отказ: скилл без подводных камней в проекте не считается готовым.
- 2026-09-27T18:25:21Z [implementation] — Negative: половина контракта — запреты. Не выбирает задачи сам, не обходит гейты, не передаёт --force, не начинает свои находки, не спрашивает владельца между задачами, не останавливается посередине задачи. Плюс предел на размер самого скилла: драйвер, которого не дочитывают, исполняется наполовину.
- 2026-09-27T18:25:21Z [implementation] — ЗАЩИТА ОТ СОБСТВЕННОГО ДЕФЕКТА: test_it_does_not_start_its_own_findings держит фразу о том, что находку заводить свободно, а начинать — по плану. Если она уйдёт из текста, драйвер станет тем самым механизмом, который дал 82% закрытий из собственных находок.
- 2026-09-27T18:27:55Z [implementation] — ХРАПОВИК ДЕДУПА ПОЙМАЛ МОИ ЖЕ ТЕСТЫ КОНТРАКТА (288>284 групп) — и был прав: семнадцать проверок скилла были одним и тем же вопросом к разным фразам. База НЕ поднималась: таблица PROMISES из (имя, регулярка, ПОЧЕМУ) плюс один параметризованный тест. Причина у каждого обещания не украшение — она говорит следующему читателю, чинить скилл или снимать обещание. Итог 284/673/0, ровно база.
- 2026-09-27T18:28:58Z [implementation] — AC-1: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives (параметры asks_the_plan, asks_every_time)
- 2026-09-27T18:28:58Z [implementation] — AC-2: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_state_has_a_decided_case — все четыре состояния состава
- 2026-09-27T18:28:58Z [implementation] — AC-3: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives (параметры hard_stop, no_auto_retry)
- 2026-09-27T18:28:58Z [implementation] — ПОПРАВКА ЦИТАТ после параметризации: классы TestTheLoopAsksThePlanEveryTime и TestTheStopsAreNamed исчезли, их проверки стали параметрами. Настоящие имена ниже.
- 2026-09-27T18:28:59Z [implementation] — AC-4: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives (параметры arms_the_ceiling, reads_the_ceiling, ceiling_is_an_exit_code)
- 2026-09-27T18:28:59Z [implementation] — AC-5: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives (параметр one_handoff_per_run)
- 2026-09-27T18:28:59Z [implementation] — AC-6: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives (параметры refuses_judgement_work, names_that_class)
- 2026-09-27T18:28:59Z [implementation] — AC-7: ✓ tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives (параметры calls_the_task_skill, does_not_reimplement_it, no_force)
- 2026-09-27T18:29:00Z [implementation] — AC-8: ✓ tests/test_run_skill_contract.py::TestTheDriverIsReachable::test_it_is_registered_as_a_core_skill и ::test_the_source_and_the_deployed_copy_both_exist
- 2026-09-27T18:31:13Z [implementation] — NO-DEAD-END: единственный красный прогон — храповик дедупа на моих же тестах контракта (288>284 групп). Подход не опровергнут: семнадцать проверок скилла действительно были одним вопросом к разным фразам, и храповик потребовал того, что и следовало сделать сразу — параметризации. База не поднималась. Побочно пришлось поправить цитаты AC: классы, на которые они ссылались, после параметризации исчезли, и гейт это поймал строкой «CITED BUT NOT RESOLVED» — то есть реестр цитат работает.
- 2026-09-27T18:32:31Z [done] — EVIDENCE-MOVED: tests/test_run_skill_contract.py::TestTheLoopAsksThePlanEveryTime => tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives
- 2026-09-27T18:32:31Z [done] — EVIDENCE-MOVED: tests/test_run_skill_contract.py::TestTheStopsAreNamed => tests/test_run_skill_contract.py::TestEveryPromiseIsStillInTheText::test_the_promise_survives
