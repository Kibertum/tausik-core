---
slug: cadence-clocks-count-closures-not-sessions
title: "Каденция аудита считает сессии — последняя зависимость правила качества от ритуала"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_session_metrics.py"
  - "scripts/project_service.py"
  - "scripts/status_view.py"
  - "scripts/tausik_utils.py"
  - "harness/skills/start/SKILL.md"
  - "tests/audit_cadence_helpers.py"
  - "tests/test_audit_cadence_closures.py"
  - "tests/test_status_view.py"
  - "tests/test_project_mcp.py"
  - "tests/test_session_two_halves.py"
scope_paths:
  - "scripts/service_session_metrics.py"
  - "scripts/project_service.py"
  - "scripts/status_view.py"
  - "scripts/tausik_utils.py"
  - "scripts/tausik_constants.py"
  - "scripts/project_config.py"
  - "harness/skills/start/SKILL.md"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - session-is-the-host-session-not-a-ritual
completed_at: "2026-09-23T19:03:37Z"
---

## Goal

ЗАМЕР #189: каденция аудита SENAR 9.5 считает СЕССИИ ровно в одном месте — scripts/service_session_metrics.py:142 («sessions since last audit when >=3, else 0»). Это единственная оставшаяся зависимость правила качества от ритуала: пока сессии открывают и закрывают руками, правило «раз в N сессий» можно и обойти, и переисполнить, ничего не нарушив формально.
ЧТО ДЕЛАЕТСЯ: часы каденции переводятся на ЗАКРЫТИЯ задач (или календарные дни — выбрать замером, что лучше ложится на историю 1239 закрытий, а не по вкусу). Калибровка и так живёт на окне закрытий (n=10), а не сессий, — то есть половина системы уже считает правильно.
НЕГАТИВНОЕ: при переносе нельзя потерять уже отмеченные аудиты — история отметок обязана продолжать читаться, а не начаться заново с нуля. И новое правило не имеет права стать НИКОГДА не наступающим: сегодня «3 сессии» без сессий не наступает вовсе (docs/ru/sessions.md:75), и замена обязана снять именно это.

## Acceptance Criteria

1. Каденция аудита SENAR 9.5 считает закрытия задач после последней отметки (meta last_audit_at); порог — ключ audit_every_closures, по умолчанию 17 с основанием в docs (3 сессии × 5,72 задачи/сессия, замер #266).
2. НЕГАТИВНЫЙ: отметка прошлой версии (только last_audit_session) продолжает читаться — время берётся из старта той сессии; история не обнуляется.
3. НЕГАТИВНЫЙ: без открытой сессии каденция наступает (закрытия идут — счёт идёт), audit mark работает без сессии.
4. status/compact JSON и tausik_audit_check говорят «N закрытий с последнего аудита» (ключ audit_overdue_closures); /start-скилл обновлён.
5. CHANGELOG EN+RU; docs.

## Plan

## Rollback

Правка одной функции подсчёта. Откат — git revert; отметки аудита в БД не трогаются.

## Journal

- 2026-09-23T19:03:32Z [implementation] — AC verified: 1. ✓ test_the_threshold_of_closures_makes_the_audit_overdue, test_under_the_threshold_it_is_not_overdue; DEFAULT_AUDIT_EVERY_CLOSURES=17 с основанием в docs 2. ✓ НЕГАТИВНЫЙ test_a_mark_from_the_session_clock_is_still_read 3. ✓ НЕГАТИВНЫЙ test_the_cadence_arrives_without_any_session 4. ✓ ключ audit_overdue_closures в status/compact и audit_check (tests/test_status_view.py, tests/test_project_mcp.py), /start обновлён 5. ✓ CHANGELOG EN+RU, docs. Verify #2739 зелёный.
