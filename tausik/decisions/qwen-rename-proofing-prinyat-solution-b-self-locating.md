---
slug: qwen-rename-proofing-prinyat-solution-b-self-locating
task: v156-portable-paths-all-ides
date: "2026-06-19"
edges: []
---

## Decision

Qwen rename-proofing: принять Solution B — self-locating launcher (.qwen/scripts/tausik_launch.py, резолвит project_dir из __file__, CWD-независимо). Реализация отложена в follow-up до подтверждения live-семантики Qwen (launch CWD + допустимость относительного command).

## Rationale

Qwen settings.json не имеет workspace-переменной (в отличие от ${workspaceFolder}/${CLAUDE_PROJECT_DIR} у Cursor/Kilo/Claude), _stdio_mcp_server не поддерживает cwd → абсолютные пути ломаются при переименовании папки. Solution A (относительные пути + --project .) минимален, но корректен только если CWD Qwen = project root — не подтверждено. Solution B корректен независимо от CWD (__file__ всегда абсолютен и движется вместе с папкой) и обобщается на будущие host без workspace-переменной. Без живого Qwen внедрять код в генератор нельзя (риск тихой поломки старта MCP). Дизайн: docs/research/v156-qwen-portable-paths.md.
