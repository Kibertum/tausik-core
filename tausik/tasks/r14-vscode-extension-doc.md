---
slug: r14-vscode-extension-doc
title: "Document VS Code Claude Extension status: hooks behavior, MCP timeout guidance"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:40:10Z"
---

## Goal

Release 1.4 readiness: r14-vscode-extension-doc

## Acceptance Criteria

1. docs/en/troubleshooting.md and docs/ru/troubleshooting.md gain a dedicated 'VS Code Claude Extension - full reference (v1.4)' section. 2. Section covers hooks status (table comparing Claude Code/Cursor/VSC ext/Qwen), MCP per-tool timeout per-tool mitigation matrix, recommended verify-first workflow, and diagnostic checklist. 3. RU and EN content is parallel. 4. Mirrored to .claude/docs/. Negative: section is documentation-only, no code changes; sample commands match existing CLI/MCP behaviour.

## Plan

## Rollback

## Journal

- 2026-05-01T01:40:02Z [implementation] — EN section: hooks status table covers task_gate/secret_scan/git_push_gate across 4 IDEs. Per-tool timeout matrix lists tausik_task_done/v2, codebase-rag.reindex, tausik_verify with pre-1.4 behavior and v1.4 mitigation.
- 2026-05-01T01:40:03Z [implementation] — AC verified: AC-1 ✓ section exists in both EN and RU files (manual review). AC-2 ✓ all four subsections present (hooks status, timeout matrix, workflow, diagnostics). AC-3 ✓ EN/RU parity (same headings, same tables). AC-4 ✓ mirror copy completed. Negative: only documentation changed, no .py files touched.
- 2026-05-01T01:40:03Z [implementation] — EN recommended workflow describes 6-step verify-first sequence. Diagnostics table covers v2-not-called, verify-never-returns, hooks-not-firing.
- 2026-05-01T01:40:03Z [implementation] — RU mirror: same structure, parallel content. Mirrored to .claude/docs/{en,ru}/troubleshooting.md.
