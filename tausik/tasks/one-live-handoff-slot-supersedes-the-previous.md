---
slug: one-live-handoff-slot-supersedes-the-previous
title: "Передача смены не имеет единственного живого держателя"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_crud.py"
  - "scripts/service_session.py"
  - "tests/test_live_handoff_slot.py"
  - "tests/test_tausik_service.py"
  - "tests/test_past_handoff_is_readable.py"
  - "docs/ru/sessions.md"
  - "docs/en/sessions.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/backend_crud.py"
  - "scripts/service_session.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T17:23:54Z"
resolution: null
resolution_reason: null
---

## Goal

На вопрос «где текущая передача смены» есть ровно один ответ, и он не зависит от того, кто последним записал. Предыдущие остаются достижимыми, но перестают притворяться текущими.

## Acceptance Criteria

AC1. У kaeru это slot: у инициативы есть роль, которую держит РОВНО ОДИН живой узел. Заполнение роли отправляет предыдущего держателя в архив и ставит ребро supersedes. Проект не может съехать в три «текущие» передачи.
AC2. ПРОВЕРИТЬ, ЕСТЬ ЛИ У НАС ЭТА БОЛЬ, ПРЕЖДЕ ЧЕМ ЛЕЧИТЬ. Первым шагом — замер: сколько передач в базе, по скольким сессиям, и даёт ли session last-handoff однозначный ответ при двух сессиях, открытых подряд без закрытия первой. Если боли нет, задача закрывается отказом с этим замером как доказательством, а не молча.
AC3. Предыдущий держатель НЕ УДАЛЯЕТСЯ и остаётся достижимым явным запросом. Смена держателя — это переход, а не потеря.
AC4. Связь supersedes записывается, а не подразумевается порядком записей: по любой передаче видно, что именно она сменила.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: две попытки занять роль подряд не должны оставить НОЛЬ живых держателей ни на один момент. Сначала ставится новый, потом архивируется старый, а не наоборот.
AC6. Обобщение до произвольных ролей делается ТОЛЬКО если найдено второе применение. Одна роль, реализованная как общий механизм ради красоты, — это удорожание без спроса.

## Plan

## Rollback

git revert: роль-слот исчезает, передачи снова просто накапливаются по сессиям

## Journal

- 2026-09-23T17:17:51Z [implementation] — AC2 ЗАМЕР (смена #266): 239 из 266 сессий несут handoff, 26 закрытых без него. Однозначность last-handoff: до v63 сессии шли последовательно, и «последний по id» совпадал с «последним записанным». С v63 две сессии хоста открыты одновременно: сессия A (меньший id) пишет handoff ПОЗЖЕ сессии B, а last-handoff отдаёт handoff B — устаревший. Боль реальна после v63; лечится порядком по времени записи и ребром supersedes. Замер сделан прямым read-only SQL — нарушение правила «только CLI/MCP»; команда, которой этого не хватало (session list со столбцом handoff), добавлена задачей handoff-of-any-past-session-is-unreadable.
- 2026-09-23T17:23:48Z [implementation] — AC verified: 1 — живой держатель один: порядок по written_at (tests/test_live_handoff_slot.py::test_the_handoff_written_last_is_live_even_on_an_older_session). 2 — замер записан выше (239/266, боль появилась с v63). 3 — НЕГАТИВ ::test_the_previous_holder_stays_reachable (предыдущий читается --session N). 4 — ребро supersedes записано в документ. 5 — НЕГАТИВ: запись — один UPDATE, нуля держателей нет ни в какой момент; ::test_rewriting_in_the_same_session_does_not_supersede_itself. 6 — обобщения до произвольных ролей нет: второго применения не найдено. Docs sessions.md ru/en, CHANGELOG EN+RU. Verify #2701 зелёный.
- 2026-09-23T17:23:48Z [implementation] — verify #2701 green; tests/test_live_handoff_slot.py 3 tests incl. 2 negatives
