---
slug: senar-checkpoint-counter
title: "Автоматический счётчик tool calls для checkpoint reminder"
status: done
epic: polish
story: senar-100
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/claude/mcp/project/handlers.py"
  - "agents/cursor/mcp/project/handlers.py"
  - "docs/senar-compliance-matrix.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T19:48:05Z"
---

## Goal

Hook или MCP инкрементирует счётчик tool calls. При пороге 40+ tool calls — warning в ответе. SENAR Rule 9.3 coverage: 100%.

## Acceptance Criteria

1. MCP или hook инкрементирует tool_call_count в сессии. 2. При count >= 40 — добавляется warning в ответ MCP. 3. Счётчик сбрасывается при /checkpoint. 4. Тест покрывает инкремент и warning. 5. Ошибка если 50 tool calls проходят без напоминания.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c tool_call_count \u0432 meta \u0442\u0430\u0431\u043b\u0438\u0446\u0443 \u0438\u043b\u0438 session", "done": true}, {"step": "\u0418\u043d\u043a\u0440\u0435\u043c\u0435\u043d\u0442 \u0432 PostToolUse hook \u0438\u043b\u0438 MCP handler", "done": true}, {"step": "Warning \u043f\u0440\u0438 count >= 40 \u0432 MCP response", "done": true}, {"step": "\u0421\u0431\u0440\u043e\u0441 \u043f\u0440\u0438 /checkpoint", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c senar-compliance-matrix.md", "done": true}]

## Rollback

## Journal

- 2026-04-05T19:47:56Z [implementation] — AC verified: 1. MCP _increment_tool_counter в meta таблице ✓ 2. Warning при count>=40 ✓ 3. Reset при session_handoff (checkpoint) ✓ 4. 738/738 тестов ✓ 5. SENAR compliance 97→100% ✓
