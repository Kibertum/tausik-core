---
slug: vendor-persist
title: "Fix vendor skill persistence and activation lifecycle"
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
completed_at: "2026-03-26T14:15:29Z"
---

## Goal

skill activate пишет в config.json, bootstrap не удаляет активированные vendor-скиллы, skill deactivate чистит config

## Acceptance Criteria

1. skill activate добавляет скилл в extension_skills в .frai/config.json. 2. skill deactivate удаляет из extension_skills и из .claude/skills/. 3. bootstrap НЕ удаляет vendor-активированные скиллы из .claude/skills/. 4. skill list корректно показывает ACTIVE для активированных vendor-скиллов. 5. Повторный bootstrap сохраняет vendor-скиллы. 6. Тесты покрывают activate/deactivate/bootstrap lifecycle.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c activated_vendor_skills \u0432 config.json schema", "done": true}, {"step": "skill_activate: \u043f\u043e\u0441\u043b\u0435 \u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f \u2014 \u0437\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0432 config extension_skills + vendor_activated", "done": true}, {"step": "skill_deactivate: \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0438\u0437 config vendor_activated + extension_skills", "done": true}, {"step": "bootstrap_copy: cleanup loop \u043f\u0440\u043e\u043f\u0443\u0441\u043a\u0430\u0435\u0442 vendor_activated \u0441\u043a\u0438\u043b\u043b\u044b", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b: activate\u2192bootstrap\u2192skill survives, deactivate\u2192cleanup", "done": true}]

## Rollback

## Journal
