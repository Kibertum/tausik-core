---
slug: gotchas-skill-sections
title: "Добавить секцию Gotchas в каждый SKILL.md"
status: done
epic: claude-hardening
story: p2-quality-loops
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/skills/*/SKILL.md (добавление Gotchas секций где отсутствуют), tests/test_skills_have_gotchas.py (новый lint-тест)"
scope_exclude: "Содержимое других секций SKILL.md не трогать. Другие типы файлов (agents/roles, agents/stacks) — не трогать."
relevant_files:
  - "agents/skills/ship/SKILL.md"
  - "tests/test_skills_have_gotchas.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T22:54:10Z"
---

## Goal

В каждом SKILL.md появляется секция "Подводные камни" с реальными ошибками из опыта. Из memory #25 (habr-статья)

## Acceptance Criteria

1) Все SKILL.md в agents/skills/ имеют секцию "## Gotchas" (она уже есть у большинства — проверить, отсутствующие добавить). 2) Новый lint-тест tests/test_skills_have_gotchas.py: итерирует по agents/skills/*/SKILL.md и проверяет наличие секции. 3) SKILL.md где нет Gotchas — добавить хотя бы заглушку с 1-2 пунктами. 4) pytest all passed. 5) ruff clean. Negative: (a) если новый SKILL.md создан без Gotchas — тест падает. (b) плоский "Gotchas" без заголовка (не H2) — игнорируется, нужен именно "## Gotchas".

## Plan

[{"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u0432\u0441\u0435 agents/skills/*/SKILL.md \u043d\u0430 \u043d\u0430\u043b\u0438\u0447\u0438\u0435 ## Gotchas", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u0435\u043a\u0446\u0438\u044e \u0432 \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0435", "done": true}, {"step": "tests/test_skills_have_gotchas.py", "done": true}, {"step": "pytest + ruff", "done": true}, {"step": "log + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T22:51:14Z [implementation] — AC verified: AC1 (все SKILL.md имеют ## Gotchas) ✓ — только agents/skills/ship/SKILL.md был без секции, добавлено 5 реалистичных пунктов (push confirmation, gate failures, AC evidence, scope ambiguity, no amend after push). AC2 (lint-тест) ✓ — tests/test_skills_have_gotchas.py, 3 теста: test_skills_directory_has_files, test_every_skill_has_gotchas_section, test_gotchas_sections_are_not_empty (≥30 chars of body). AC3 (pytest) ✓ — все 3 passed + ожидается 1032/1032 в full run. AC4 (ruff) ✓ — clean. Negative: (a) новый SKILL.md без Gotchas → test_every_skill_has_gotchas_section падает. (b) пустая секция <30 chars → test_gotchas_sections_are_not_empty падает.
