---
slug: redact-exists-in-cli-and-is-absent-from-mcp
title: "redact есть в CLI и отсутствует в MCP: поверхности разошлись на новой команде"
status: planning
epic: release-19-renar-conformance
story: github-primary-gitlab-mirror
complexity: simple
role: backend
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/mcp_*.py"
  - "tests/*.py"
  - "docs/ru/cli.md"
  - "docs/ru/agent-contract.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, сессия #180: команда tausik redact (dry-run, --apply, redact list) построена только в CLI. В MCP её нет — это было НАМЕРЕННО через scope_exclude задачи nothing-can-redact-the-memory-the-framework-publishes, то есть пропуск осознанный, а не забытый. Но правило проекта гласит MCP-first, и потому осознанный пропуск всё равно оставляет расхождение поверхностей — ровно тот класс, который обязана ловить ratchet-for-mcp-cli-surface-parity. Задача заводится, чтобы расхождение было ЗАПИСАНО и закрыто явно, а не жило молча до тех пор, пока ratchet его не найдёт. Вопрос, который задача обязана задать до работы: выносится ли необратимая половина (--apply) в MCP вообще, или в MCP уезжает только сухой прогон и redact list, а необратимое остаётся ручным.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита; инструменты MCP аддитивны

## Journal
