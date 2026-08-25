---
slug: rag-auto-incremental-reindex
title: "Auto-incremental RAG reindex on SessionStart + pre-commit"
status: done
epic: v131-blind-review-fixes
story: rag-discoverability
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/pre-commit"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T07:25:45Z"
---

## Goal

Currently session_start.py only surfaces RAG status; agent must run reindex manually. Auto-trigger incremental reindex on session start (in background, non-blocking) and on pre-commit (foreground, ~quick) so the index stays fresh without agent intervention. Closes the second part of the RAG discoverability gap.

## Acceptance Criteria

1. session_start.py spawns incremental reindex in background (subprocess.Popen detached, stdin/stdout/stderr nulled, no wait); 2. Hook itself returns within ~100ms — never blocks SessionStart; 3. First-run case (no rag.db) → spawns FULL reindex once, then session ends — next session uses incremental; 4. pre-commit hook runs incremental reindex (foreground, max 5s timeout) before exit so post-commit index reflects committed changes; 5. Both paths degrade gracefully when codebase-rag MCP isn't installed (no .claude/mcp/codebase-rag/) — no crash, no error to agent; 6. Negative: SessionStart never blocks > 200ms even when reindex is running; 7. Negative: pre-commit reindex timeout doesn't fail the commit (warn-only).

## Plan

## Rollback

## Journal

- 2026-04-28T07:25:44Z [implementation] — AC verified: 1.✓ session_start._spawn_background_reindex() запускает subprocess.Popen с DETACHED_PROCESS (Windows) / start_new_session (Unix), stdin/stdout/stderr → DEVNULL, без wait; 2.✓ Smoke-test: _rag_summary() возвращается за 3 мс (под лимитом 200 мс); 3.✓ First-run path: если нет rag.db — spawn full reindex в фоне, иначе incremental; 4.✓ pre-commit hook добавил блок с timeout 5s на incremental reindex после mypy; 5.✓ Graceful degradation: _rag_server_path returns None если codebase-rag не установлен → _spawn_background_reindex no-ops; pre-commit `[ -n "$RAG_SERVER" ]` skip; 6.✓ Negative — Popen errors caught (OSError, ValueError), session_start никогда не падает; 7.✓ Negative — pre-commit использует `|| echo "skipped"`, timeout не валит коммит. tests/test_v131_blind_review.py + test_hud_cli = 16 passed.
