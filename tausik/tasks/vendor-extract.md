---
slug: vendor-extract
title: "Fix vendor tarball extraction — symlinks, data dirs, multi-path skills"
status: done
epic: frai-v24
story: vendor-skills-fix
complexity: medium
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
completed_at: "2026-03-26T14:19:59Z"
---

## Goal

Vendor-скиллы с data/scripts (ui-ux-pro-max) корректно извлекаются: symlinks разрешаются в файлы, skill_dirs поддерживает data_dirs, поддержка .claude-plugin/plugin.json

## Acceptance Criteria

1. Tarball extraction разрешает symlinks — копирует target файлы вместо создания symlink. 2. skills.json поддерживает data_dirs — дополнительные директории для извлечения в skill dir. 3. ui-ux-pro-max извлекается с data/ и scripts/ (не пустые). 4. .claude-plugin/plugin.json читается для метаданных (версия, описание). 5. Скиллы без symlinks/data продолжают работать как раньше. 6. Тесты покрывают extraction с symlinks и data_dirs.

## Plan

[{"step": "Tarball extraction: \u0440\u0430\u0437\u0440\u0435\u0448\u0430\u0442\u044c symlinks (\u0447\u0438\u0442\u0430\u0442\u044c target, \u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043a\u0430\u043a \u0444\u0430\u0439\u043b)", "done": true}, {"step": "skills.json: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0443 data_dirs \u0434\u043b\u044f \u0434\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0445 \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0438\u0439", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c _extract_skill_dirs: \u0438\u0437\u0432\u043b\u0435\u043a\u0430\u0442\u044c data_dirs \u0432 skill subdir", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0447\u0442\u0435\u043d\u0438\u0435 .claude-plugin/plugin.json \u0434\u043b\u044f \u043c\u0435\u0442\u0430\u0434\u0430\u043d\u043d\u044b\u0445", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c skills.json \u0434\u043b\u044f ui-ux-pro-max: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c data_dirs \u0441 src/ui-ux-pro-max", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: extraction \u0441 symlinks, data_dirs, \u043e\u0431\u0440\u0430\u0442\u043d\u0430\u044f \u0441\u043e\u0432\u043c\u0435\u0441\u0442\u0438\u043c\u043e\u0441\u0442\u044c", "done": true}]

## Rollback

## Journal
