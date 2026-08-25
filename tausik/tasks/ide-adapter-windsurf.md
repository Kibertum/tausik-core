---
slug: ide-adapter-windsurf
title: "Адаптер для Windsurf/Cline/Aider"
status: done
epic: public-release
story: cross-ide
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/ide_utils.py"
  - "bootstrap/bootstrap_generate.py"
  - "docs/adding-new-ide.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:35:43Z"
---

## Goal

Минимум 1 новый IDE (Windsurf или Cline) поддерживается bootstrap. Доказательство что абстракция работает.

## Acceptance Criteria

1. IDE_REGISTRY в ide_utils.py содержит windsurf и codex. 2. bootstrap_generate.py генерирует .windsurfrules для windsurf. 3. docs/adding-new-ide.md описывает процесс. 4. Ошибка если --ide передаёт неизвестный IDE — ValueError.

## Plan

[{"step": "\u0418\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u044c \u043a\u043e\u043d\u0444\u0438\u0433-\u0444\u043e\u0440\u043c\u0430\u0442 Windsurf \u0438 Cline (.windsurfrules, etc.)", "done": true}, {"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0430\u0434\u0430\u043f\u0442\u0435\u0440 \u0432 bootstrap \u0434\u043b\u044f Windsurf", "done": true}, {"step": "\u0420\u0435\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u0442\u044c --ide \u0444\u043b\u0430\u0433 \u0432 init", "done": true}, {"step": "\u041f\u0440\u043e\u0442\u0435\u0441\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c bootstrap --ide windsurf", "done": true}, {"step": "\u0414\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c Adding a New IDE \u0432 docs/", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:35:32Z [implementation] — AC verified: 1. IDE_REGISTRY содержит windsurf и codex ✓ 2. generate_windsurfrules + generate_ide_rules фабрика ✓ 3. docs/adding-new-ide.md ✓ 4. ValueError для неизвестного IDE (покрыт тестами) ✓
