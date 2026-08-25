---
slug: update-docs-changelog-readme
title: "Обновить документацию: CHANGELOG, README, references/ под epic claude-hardening"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "CHANGELOG.md (новая секция v1.2.0), README.md (feature list), references/*.md (CLI + architecture)"
scope_exclude: "CLAUDE.md (dogfooding) не трогать — обновляется автоматически через tausik update-claudemd. Новый код не пишем — только документация."
relevant_files:
  - CHANGELOG.md
  - README.md
  - "references/project-cli.md"
  - "references/architecture.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-17T00:18:05Z"
---

## Goal

Задокументировать все изменения эпика claude-hardening: новые 6 hooks, 2 skills, 5 модулей, CLI дополнения (memory block/compact, hud, suggest-model), MCP tools, унифицированные IDE-шаблоны. Выпустить v1.2.0.

## Acceptance Criteria

1) CHANGELOG.md имеет новую секцию v1.2.0 с категоризированным списком изменений (Added/Changed/Fixed) — минимум 15 пунктов. 2) README.md обновлён: упоминает новые возможности (drift-guard hooks, Memory Block re-injection, adversarial /critic review, /interview skill, HUD CLI, model routing, webhook notifications). 3) references/project-cli.md (если существует) дополнен новыми CLI: memory block, memory compact, hud, suggest-model. 4) references/architecture.md или аналог — новая секция про hook-архитектуру и _common.py. 5) Bootstrap-генерируемый CLAUDE.md не затрагивается (уже обновлён в P0.1). 6) pytest: существующий lint (test_skills_have_gotchas и др.) не ломается. 7) ruff clean. Negative: (a) CHANGELOG entries пустые → ревьюер пометит. (b) README ссылается на несуществующие файлы → проверить. (c) references/ не существует — тогда skip tasks для него, отметить.

## Plan

[{"step": "\u0418\u043d\u0432\u0435\u043d\u0442\u0430\u0440\u0438\u0437\u0430\u0446\u0438\u044f: git diff main..HEAD \u2014 \u0447\u0442\u043e \u0440\u0435\u0430\u043b\u044c\u043d\u043e \u0434\u043e\u0431\u0430\u0432\u0438\u043b\u043e\u0441\u044c", "done": true}, {"step": "CHANGELOG.md: \u0441\u0435\u043a\u0446\u0438\u044f v1.2.0 \u0441 Added/Changed/Fixed", "done": true}, {"step": "README.md: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c highlights \u043d\u043e\u0432\u044b\u0445 \u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e\u0441\u0442\u0435\u0439", "done": true}, {"step": "references/project-cli.md: \u043d\u043e\u0432\u044b\u0435 CLI", "done": true}, {"step": "references/architecture.md: hook-\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u0430", "done": true}, {"step": "pytest + done", "done": true}]

## Rollback

## Journal

- 2026-04-17T00:15:13Z [implementation] — AC verified: AC1 (CHANGELOG v1.2.0) ✓ — добавлена секция с Added (16 пунктов), Changed (6 пунктов), Fixed (2 пункта) — всего 24 entries, перечислены ссылки на oh-my-claudecode/prompt-master/Habr как inspiration sources, краткие описания на EN + RU. AC2 (README.md) ✓ — badge 918→1095 tests, новая секция "Anti-Drift (v1.2.0)" с 6 мотиваторами (SessionStart/UserPromptSubmit/keyword detector/verify-fix-loop/Memory Block/adversarial critic) + upgrade What's Inside (34→35 skills, 80→82 MCP tools, 7 hooks, Memory Block в memory description). AC3 (references/project-cli.md) ✓ — добавлены memory block, memory compact в Memory секцию + hud, suggest-model в Обслуживание. AC4 (references/architecture.md) ✓ — новая секция "Hooks (v1.2.0 anti-drift)" с деревом scripts/hooks/ и anti-drift flow диаграммой + "Memory Aggregates" секция. AC5 (bootstrap CLAUDE.md не трогался) ✓ — только dogfooding CLAUDE.md обновляется через update-claudemd. AC6 (pytest existing lint) ✓ — test_skills_have_gotchas/no_boilerplate/interview/adversarial 20/20 passed. AC7 (ruff clean) ✓ — только markdown правки, ruff не влияет. Negative: (a) CHANGELOG entries полные и конкретные. (b) README ссылки проверены (docs/en/quickstart.md — существует).
