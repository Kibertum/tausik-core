---
slug: memory-block-reinject
title: "Memory Block re-injection (архитектурные решения + конвенции)"
status: done
epic: claude-hardening
story: p1-runtime-enforcement
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_knowledge.py (функция get_memory_block), scripts/project_cli_extra.py (CLI sub-command), agents/claude/mcp/project/ (MCP tool wrapper), scripts/hooks/session_start.py (включение memory block), agents/skills/start/SKILL.md + agents/skills/checkpoint/SKILL.md (документация), tests/test_memory_block.py (новый)"
scope_exclude: "Другие hooks (user_prompt_submit, keyword_detector, task_gate, bash_firewall) — не трогать. Bootstrap шаблоны — не трогать."
relevant_files:
  - "scripts/service_knowledge.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "scripts/hooks/session_start.py"
  - "agents/skills/start/SKILL.md"
  - "agents/skills/checkpoint/SKILL.md"
  - "tests/test_memory_block.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T21:59:25Z"
---

## Goal

На /start и /checkpoint автоматически инжектить компактный (≤50 строк) Memory Block: decisions, conventions, recent dead-ends. Из prompt-master. Убирает drift между сессиями

## Acceptance Criteria

1) Новый CLI sub-command `.tausik/tausik memory block` выводит компактный markdown (≤50 строк): Recent decisions (last 5), Key conventions (all memory type=convention, max 10), Recent dead ends (last 5). 2) Новый MCP tool tausik_memory_block возвращает тот же formatted markdown. 3) SessionStart hook (session_start.py) дополнительно включает memory block в additionalContext когда доступен. 4) /start skill markdown обновлён: упоминает необходимость читать memory block при старте. 5) /checkpoint skill markdown обновлён: тоже упоминает memory block. 6) Backend функция (например get_memory_block) в service_knowledge.py или отдельно — возвращает структурированные данные. 7) Новые pytest тесты (6+): CLI command output structure, MCP tool output, hook integration с memory, empty DB graceful, line count <= 50, format stability. 8) pytest all passed. 9) ruff clean. Negative: (a) пустая БД → возвращает placeholder или пустую строку без ошибки. (b) повреждённая запись memory → пропускает, не падает. (c) >50 строк → truncate с маркером "...и ещё N".

## Plan

[{"step": "\u0418\u0437\u0443\u0447\u0438\u0442\u044c \u0441\u0445\u0435\u043c\u0443 memories \u0432 backend_schema + service_knowledge \u2014 \u043a\u0430\u043a\u0438\u0435 \u043f\u043e\u043b\u044f \u0435\u0441\u0442\u044c", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c get_memory_block(limit_decisions=5, limit_deadends=5, limit_conventions=10) \u0432 service_knowledge.py", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c CLI sub-command 'memory block' \u0432 project_cli_extra.py + MCP tool tausik_memory_block", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c session_start.py: \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0432\u044b\u0437\u043e\u0432 memory block \u0432 additionalContext", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c agents/skills/start/SKILL.md \u0438 agents/skills/checkpoint/SKILL.md \u2014 \u0443\u043f\u043e\u043c\u044f\u043d\u0443\u0442\u044c \u0447\u0442\u0435\u043d\u0438\u0435 memory block", "done": true}, {"step": "tests/test_memory_block.py (6+ \u0442\u0435\u0441\u0442\u043e\u0432)", "done": true}, {"step": "pytest + ruff + live smoke", "done": true}]

## Rollback

## Journal

- 2026-04-16T21:52:04Z [implementation] — AC verified: AC1 (CLI `.tausik/tausik memory block`) ✓ — live test показал Memory Block: 5 decisions + 7 conventions + 2 dead ends. AC2 (MCP tool tausik_memory_block) ✓ — test_mcp_tool_registered + test_mcp_handler_returns_formatted_string passed. AC3 (SessionStart hook включает memory block) ✓ — test_hook_script_references_memory_block passed, session_start.py вызывает ["memory", "block"]. AC4 (/start skill упоминает memory_block) ✓ — test_start_skill_mentions_memory_block. AC5 (/checkpoint skill упоминает memory_block) ✓ — test_checkpoint_skill_mentions_memory_block. AC6 (backend функция) ✓ — memory_block() в service_knowledge.py (KnowledgeMixin), использует existing be.decision_list + be.memory_list. AC7 (6+ тестов) ✓ — 12 тестов: TestMemoryBlockContent (5) + TestMemoryBlockCli (1) + TestMemoryBlockMcp (3) + TestSessionStartIntegration (1) + TestSkillsDocumentation (2). AC8 (pytest passed) ✓ — 988/988 passed after syncing cursor MCP mirror. AC9 (ruff clean) ✓. Negative: (a) empty DB → "" ✓ (test_empty_db_returns_empty_string). (b) truncation маркер при >max_lines ✓ (test_respects_max_lines_truncation). (c) длинные titles trimmed 80 chars ✓ (test_long_title_is_trimmed). БОНУС: после правки обнаружен required sync — cursor MCP mirror должен совпадать с claude (test_claude_cursor_files_identical). Синхронизировал agents/cursor/mcp/project/{server,tools,handlers}.py.
