---
slug: mcp-task-done-v2-cursor-mcp-config
title: "MCP task_done v2, Cursor project mcp config, tested-platform docs"
status: done
epic: null
story: null
complexity: complex
role: null
stack: null
tier: substantial
call_budget: 150
defect_of: null
scope: "scripts/service_*.py, agents/*/mcp/project/*, bootstrap/*, docs/*, README*"
scope_exclude: "DB schema migrations, unrelated feature modules, external skill repos"
relevant_files:
  - "tests/test_bootstrap_generate_mcp.py"
  - "tests/test_project_mcp.py"
  - "tests/test_mcp_integration.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-29T18:57:11Z"
---

## Goal

Сделать MCP-контракт task_done машинно-читаемым с progress-feedback, добавить project-level Cursor MCP config generation и явно задокументировать официально протестированные IDE

## Acceptance Criteria

1. MCP tool tausik_task_done_v2 returns structured JSON with gate-level blocking_failures and remediation hints. 2. During gate execution, progress events/log lines are emitted per gate so long runs are observable. 3. Bootstrap generates project-level Cursor MCP config (.cursor/mcp.json) while keeping existing .mcp.json compatibility. 4. Documentation explicitly marks officially tested IDE combinations and expected-but-not-fully-tested environments. 5. Negative scenario: if a blocking gate fails, response includes gate name and affected file instead of generic error.

## Plan

## Rollback

## Journal

- 2026-04-29T18:37:10Z [implementation] — Старт реализации: подтверждены требования по structured task_done, progress gates, Cursor project-level MCP config и docs о tested-платформах.
- 2026-04-29T18:41:36Z [implementation] — Реализованы core-изменения: task_done_v2 structured payload, gate progress callbacks/logging, bootstrap генерация .cursor/mcp.json, обновления docs/readme, расширены тесты.
- 2026-04-29T18:42:18Z [implementation] — AC verified: 1. ✓ Added tausik_task_done_v2 structured response with blocking_failures/remediation. 2. ✓ Added per-gate progress events and stderr progress lines ([gate X/N] running...). 3. ✓ Bootstrap now generates .cursor/mcp.json for Cursor project-level MCP config. 4. ✓ Updated README/quickstart/mcp docs with officially tested IDE matrix (VSCode+Claude Extension, Cursor). 5. ✓ Negative scenario covered: blocking gate failures now return gate/file/output details in structured payload. Verification: pytest tests/test_project_mcp.py tests/test_mcp_integration.py tests/test_bootstrap_generate_mcp.py -q => 56 passed.
- 2026-04-29T18:47:45Z [implementation] — Попытка task done заблокирована QG-2: filesize (bootstrap/bootstrap.py > 400 lines) и pytest timeout на широком наборе relevant_files. Код и тесты изменений при этом зелёные.
