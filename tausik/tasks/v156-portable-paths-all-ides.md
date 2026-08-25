---
slug: v156-portable-paths-all-ides
title: "Rename-proof Qwen paths (no workspace var — needs design)"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: complex
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "Дизайн-артефакт: tausik decide + docs/research/v156-qwen-portable-paths.md. Чтение bootstrap_qwen.py / bootstrap_paths.py."
scope_exclude: "НЕ менять bootstrap_qwen.py в этой задаче (нужна Qwen-верификация) — реализация = follow-up."
relevant_files:
  - "docs/research/v156-qwen-portable-paths.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T11:54:45Z"
---

## Goal

Claude/Cursor/Kilo are rename-proof as of v1.5.5 (v155-portable-paths-ide + kilo). Qwen Code's settings.json has no documented workspace-folder variable (only $VAR/${VAR} env expansion), so its MCP server + hook paths stay absolute and break on folder rename. Investigate: a TAUSIK-set env var the user exports, relative-path + CWD assumption, or a Qwen feature request. Don't ship blind.

## Acceptance Criteria

1. Зафиксирована суть проблемы: bootstrap_qwen.py встраивает абсолютные пути (MCP server, --project, hook-команды); формат Qwen settings.json не имеет workspace-переменной (${workspaceFolder}/${CLAUDE_PROJECT_DIR}); _stdio_mcp_server не поддерживает cwd → переименование папки ломает конфиг. 2. Спроектированы ≥2 решения с trade-offs: (A) относительные пути + --project . (зависит от CWD=project root), (B) self-locating launcher (.qwen/scripts, резолвит project_dir из __file__, CWD-независимо). 3. Дана рекомендация + ключевой открытый вопрос (CWD Qwen при запуске MCP/хуков), от которого зависит выбор A vs B. 4. Решение записано (tausik decide) + краткий design-doc в docs/research/. 5. Ошибка/abort (негатив): НЕ внедрять код в генератор Qwen без подтверждения runtime-семантики Qwen (нет живого Qwen для верификации) — иначе риск тихой поломки; реализация отложена до подтверждения.

## Plan

## Rollback

Удалить design-doc; decision можно пометить superseded.

## Journal

- 2026-06-19T11:54:35Z [implementation] — AC verified: 1.✓ проблема зафиксирована (bootstrap_qwen абс.пути, нет workspace-var, _stdio_mcp_server без cwd) в design-doc. 2.✓ 2 решения с trade-offs: A (relative + --project ., CWD-зависимо) и B (self-locating launcher, CWD-независимо). 3.✓ рекомендация=B + открытый вопрос (CWD Qwen при запуске MCP/хуков). 4.✓ decision #121 записан + docs/research/v156-qwen-portable-paths.md создан. 5.✓ negative: код в генератор Qwen НЕ внедрён (реализация отложена до Qwen-верификации) — scope_exclude соблюдён. verify green (hadolint+pytest). Domain: дизайн отражает реальные ограничения формата Qwen settings.json.
- 2026-06-19T11:54:44Z [implementation] — AC verified: 1.✓ проблема зафиксирована (bootstrap_qwen абс.пути, нет workspace-var, _stdio_mcp_server без cwd). 2.✓ 2 решения с trade-offs: A (relative + --project ., CWD-зависимо) и B (self-locating launcher, CWD-независимо). 3.✓ рекомендация=B + открытый вопрос (CWD Qwen). 4.✓ decision #121 + docs/research/v156-qwen-portable-paths.md. 5.✓ negative: код в генератор НЕ внедрён (отложено). Knowledge: decision #121 (Solution B). verify green.
