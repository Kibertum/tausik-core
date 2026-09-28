---
slug: handoff-is-generated-from-the-journal
title: "Handoff порождается из журнала, а не сочиняется агентом: SessionEnd пишет его сам, /checkpoint и /end зовут генератор"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: complex
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/handoff_generate.py"
  - "scripts/service_session.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_session.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/skills/checkpoint/SKILL.md"
  - "harness/skills/end/SKILL.md"
  - "tests/test_handoff_generated.py"
  - "tests/test_tausik_service.py"
  - "tests/test_e2e_workflow.py"
  - "docs/ru/sessions.md"
  - "docs/en/sessions.md"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/handoff_generate.py"
  - "scripts/service_session*.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_session.py"
  - "scripts/render_session.py"
  - "scripts/hooks/session_metrics.py"
  - "harness/claude/mcp/project/*.py"
  - "harness/skills/start/SKILL.md"
  - "harness/skills/checkpoint/SKILL.md"
  - "harness/skills/end/SKILL.md"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - handoff-of-any-past-session-is-unreadable
  - one-live-handoff-slot-supersedes-the-previous
  - session-is-the-host-session-not-a-ritual
completed_at: "2026-09-23T17:34:39Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#173"
started_model_id: claude-fable-5-1
started_model_version: null
done_model_id: claude-fable-5-1
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

SENAR 1.5 §3.45: handoff — единственный маршрут, которым контекст одной сессии достигает следующей; §7.3 требует его от каждой сессии. У нас он существует только когда агент исполнил /checkpoint или /end и сам составил JSON (completed, in_progress, next_steps, warnings). Автономный агент, упёршийся в компакцию или закрытый хостом, handoff не пишет — и смены #252–#260 закрыты без итогов. При этом всё содержимое handoff уже лежит в записях: task log (append-only), статусы задач, квитанции verify, решения, память, dead ends, открытая разведка. Цель: handoff — ПРОЕКЦИЯ журнала за окно сессии, порождаемая командой session handoff без аргумента (и MCP), с необязательными авторскими полями next_steps/warnings поверх; SessionEnd-хук пишет его автоматически; /checkpoint и /end становятся вызовом генератора. Закрывает связку: один живой держатель (#126), читаемость прошлых handoff (#137).

## Acceptance Criteria

1. session handoff без JSON порождает документ из записей окна сессии: задачи, закрытые в окне; активные задачи с последней строкой журнала и шагом плана; квитанции verify окна; решения/память/dead ends окна; открытая разведка. Тест на фикстуре с известным журналом сравнивает поле в поле.
2. Авторские поля (next_steps, warnings, in_progress[].state) принимаются поверх порождённого и помечаются как авторские; порождённое их не затирает.
3. SessionEnd-хук записывает порождённый handoff до закрытия сессии; сбой генератора не блокирует закрытие (best-effort) и оставляет явное событие о сбое, а не тишину.
4. НЕГАТИВНЫЙ: сессия без единой записи в журнале даёт handoff с явным «в окне записей нет» — не пустой объект и не выдуманные шаги.
5. НЕГАТИВНЫЙ: порождённый handoff не называет задачу закрытой, если её статус не done; тест с задачей в review.
6. Прошлые handoff читаются: session handoff --show N (CLI и MCP) для любой сессии, а не только последней (#137); последний — единственный живой держатель, предыдущие помечены superseded (#126).
7. Скиллы start/checkpoint/end: раздел «Build handoff JSON» заменён вызовом генератора; размер скиллов не растёт (тест на количество строк не нужен — тест на присутствие вызова и отсутствие ручного JSON-шаблона).
8. docs/ru+en sessions.md, cli.md, mcp.md; CHANGELOG EN+RU.

## Plan

## Rollback

git revert; схема не меняется, если superseded выражается существующим полем; иначе — миграция вниз задокументирована в задаче.

## Journal

- 2026-09-23T17:34:34Z [implementation] — AC verified: 1 — session handoff без JSON порождает документ из окна (tests/test_handoff_generated.py::test_the_handoff_is_projected_from_the_window). Domain: на живой базе смена #266 — 7 закрытых задач, 1 активная с последней строкой журнала, 33 квитанции verify, 6 решений, 8 записей памяти, авторские next_steps/warnings поверх. 2 — ::test_authored_fields_sit_on_top_and_are_marked (authored_fields; конфликтующее авторское уходит в authored). 3 — ::test_session_end_writes_the_handoff_when_none_was; НЕГАТИВ ::test_a_failing_generator_does_not_keep_the_session_open (событие handoff_generate_failed). 4 — НЕГАТИВ ::test_an_empty_window_says_so_in_words. 5 — НЕГАТИВ ::test_a_task_in_review_is_not_called_completed. 6 — прошлые handoff читаются (задача handoff-of-any-past...), единый держатель (one-live-handoff-slot...). 7 — скиллы checkpoint/end зовут генератор, ::test_the_skills_call_the_generator_instead_of_a_json_template. 8 — docs sessions.md, cli.md ru/en; CHANGELOG EN+RU. Verify #2703 зелёный.
- 2026-09-23T17:34:35Z [implementation] — verify #2703 green; tests/test_handoff_generated.py 7 tests incl. 3 negatives; live handoff of session #266 generated
