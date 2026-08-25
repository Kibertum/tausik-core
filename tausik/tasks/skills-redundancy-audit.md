---
slug: skills-redundancy-audit
title: "Ревизия skills на избыточность"
status: done
epic: claude-hardening
story: p2-quality-loops
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/skills/*/SKILL.md (точечные правки), tests/test_skills_no_boilerplate.py (новый lint), TAUSIK memory (audit findings)"
scope_exclude: "Логика skills не меняется, только текстовые редундантности. Другие файлы не трогать."
relevant_files:
  - "agents/skills/checkpoint/SKILL.md"
  - "agents/skills/commit/SKILL.md"
  - "agents/skills/debug/SKILL.md"
  - "agents/skills/end/SKILL.md"
  - "agents/skills/explore/SKILL.md"
  - "agents/skills/plan/SKILL.md"
  - "agents/skills/review/SKILL.md"
  - "agents/skills/ship/SKILL.md"
  - "agents/skills/skill-test/SKILL.md"
  - "agents/skills/start/SKILL.md"
  - "agents/skills/task/SKILL.md"
  - "agents/skills/test/SKILL.md"
  - "tests/test_skills_no_boilerplate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T22:58:35Z"
---

## Goal

Проверить каждый SKILL.md и убрать очевидные инструкции, которые Claude и так знает. Фокус на уникальном знании проекта. Из memory #25

## Acceptance Criteria

1) Аудит всех agents/skills/*/SKILL.md — поиск 3 типов избыточности: (a) повторяющееся boilerplate "Always respond in the user's language" присутствующее и в SKILL.md и в генерируемом CLAUDE.md, (b) объяснения очевидного (что такое task, markdown, python), (c) перекрывающийся контент между skills. 2) Документ audit-report.md с findings и обоснованием что оставить / что убрать. 3) Явные удаления boilerplate где 100% дубликат CLAUDE.md hard constraints — убрать из skills чтобы не тратить токены. 4) pytest existing + новый test_skills_no_boilerplate.py проверяет отсутствие конкретных known-redundant phrases в SKILL.md. 5) ruff clean. Negative: (a) удаление не должно сломать логику skill (тест каждого skill работает). (b) minimum 2 skill.md обновлено (иначе audit бесполезен). (c) audit-report сохранён в TAUSIK memory как convention — не в файловой системе, чтобы не засорять.

## Plan

[{"step": "\u0421\u043a\u0430\u043d\u0438\u0440\u043e\u0432\u0430\u0442\u044c skill.md \u043d\u0430 known redundant phrases", "done": true}, {"step": "\u0423\u0431\u0440\u0430\u0442\u044c \u0442\u0440\u0438 \u0441\u0430\u043c\u044b\u0445 \u043f\u043e\u0432\u0442\u043e\u0440\u044f\u044e\u0449\u0438\u0445\u0441\u044f boilerplate-\u0444\u0440\u0430\u0437", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c lint-\u0442\u0435\u0441\u0442 \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u0435\u0434\u043e\u0442\u0432\u0440\u0430\u0442\u0438\u0442\u044c \u0432\u043e\u0437\u0432\u0440\u0430\u0442", "done": true}, {"step": "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c audit findings \u0432 TAUSIK memory", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T22:55:28Z [implementation] — AC verified: AC1 (audit 3 типов) ✓ — сканирование показало boilerplate "Always respond in the user's language" в 12 файлах (checkpoint, commit, debug, end, explore, plan, review, ship, skill-test, start, task, test). Объяснения очевидного и перекрытия не обнаружены в массе. AC2 (audit-report) ✓ — сохранён как TAUSIK memory #32 (convention) вместо файловой системы, как и указано в AC. AC3 (удалено 12 дубликатов) ✓ — python one-liner через regex убрал строки. AC4 (lint-тест) ✓ — tests/test_skills_no_boilerplate.py проверяет отсутствие фраз; 4 теста в сумме с gotchas-тестами passed. AC5 (ruff clean) ✓. Negative: (a) логика skills не изменилась — только удаление одной строки, не ломает структуру (тесты на contents других секций не падают). (b) 12 файлов обновлено — ≥2 минимум. (c) audit сохранён в memory, не в файловой системе.
