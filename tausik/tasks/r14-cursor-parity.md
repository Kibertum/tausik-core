---
slug: r14-cursor-parity
title: "Document Cursor bootstrap: no Claude hooks file; mitigation path"
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
completed_at: "2026-05-01T00:40:10Z"
---

## Goal

Release 1.4 readiness: r14-cursor-parity

## Acceptance Criteria

1. SENAR_RULES table in bootstrap_templates.py honestly states that Rule 1 PreToolUse hook works in Claude Code/VS Code/Qwen Code but is Instruction-only in Cursor (no hooks API). 2. Cursor caveat callout below the table explains MCP-tool-based mitigation. 3. Negative scenario: Cursor user trying to bypass Rule 1 via raw Edit will not be process-blocked - documented as known gap with code-review mitigation.

## Plan

## Rollback

## Journal

- 2026-05-01T00:40:10Z [planning] — AC verified: 1. Rule 1 enforcement column honestly differentiates Claude/VSCode/Qwen vs Cursor ✓ (bootstrap/bootstrap_templates.py:67). 2. Cursor caveat block describes MCP mitigation ✓. 3. Negative - Cursor user without hooks knows raw Edit is non-conformant and must route through tausik_task_start ✓.
- 2026-05-01T00:40:10Z [planning] — Same template feeds CLAUDE.md, AGENTS.md, .cursorrules and QWEN.md so the disclaimer reaches Cursor users in their primary onboarding doc. Bootstrap regression suite passes: 49/49 in test_bootstrap_generate + qwen + dryrun + frontmatter + skills_coverage.
- 2026-05-01T00:40:10Z [planning] — Updated bootstrap/bootstrap_templates.py SENAR_RULES section: Rule 1 enforcement column now reads 'Hard (PreToolUse hook) in Claude Code, VS Code Claude Extension, Qwen Code; Instruction-only in Cursor (no hooks API)'. Added explicit Cursor caveat callout below the table explaining the gap and the MCP-tool-routing + code-review mitigation.
