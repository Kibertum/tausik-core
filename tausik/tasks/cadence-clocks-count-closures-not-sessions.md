---
slug: cadence-clocks-count-closures-not-sessions
title: "Каденция аудита считает сессии — последняя зависимость правила качества от ритуала"
status: planning
epic: release-19-agent-effectiveness
story: evidence-is-durable
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР #189: каденция аудита SENAR 9.5 считает СЕССИИ ровно в одном месте — scripts/service_session_metrics.py:142 («sessions since last audit when >=3, else 0»). Это единственная оставшаяся зависимость правила качества от ритуала: пока сессии открывают и закрывают руками, правило «раз в N сессий» можно и обойти, и переисполнить, ничего не нарушив формально.
ЧТО ДЕЛАЕТСЯ: часы каденции переводятся на ЗАКРЫТИЯ задач (или календарные дни — выбрать замером, что лучше ложится на историю 1239 закрытий, а не по вкусу). Калибровка и так живёт на окне закрытий (n=10), а не сессий, — то есть половина системы уже считает правильно.
НЕГАТИВНОЕ: при переносе нельзя потерять уже отмеченные аудиты — история отметок обязана продолжать читаться, а не начаться заново с нуля. И новое правило не имеет права стать НИКОГДА не наступающим: сегодня «3 сессии» без сессий не наступает вовсе (docs/ru/sessions.md:75), и замена обязана снять именно это.

## Acceptance Criteria

## Plan

## Rollback

Правка одной функции подсчёта. Откат — git revert; отметки аудита в БД не трогаются.

## Journal
