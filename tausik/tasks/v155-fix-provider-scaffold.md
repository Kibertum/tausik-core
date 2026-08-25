---
slug: v155-fix-provider-scaffold
title: "Fix & rearchitect provider scaffold (axis-1)"
status: done
epic: v155-kilo-zai
story: v155-provider-abstraction
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/providers/*.py, scripts/model_routing.py"
scope_exclude: "scripts/model_routing_matrix.py (next task), bootstrap/*"
relevant_files:
  - "scripts/providers/__init__.py"
  - "scripts/providers/_registry.py"
  - "scripts/providers/base.py"
  - "scripts/providers/claude.py"
  - "scripts/providers/kilo.py"
  - "scripts/providers/cursor.py"
  - "scripts/providers/qwen.py"
  - "scripts/model_routing.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:14:42Z"
---

## Goal

Rewrite the broken scaffold: claude.py IndentationError, inconsistent register(), double/circular auto-register, delete zai.py, and fix model_routing.py import path (scripts.providers fails under MCP sys.path -> silent None). Provider package imports cleanly and registers claude/cursor/kilo/qwen. No silent model-detection regression.

## Acceptance Criteria

1. `import providers; providers.available()` lists ['claude','cursor','kilo','qwen'] (no 'zai'), no exceptions. 2. scripts/providers/zai.py deleted. 3. claude.py has no duplicated/dead block and imports cleanly. 4. Single registration path, no circular/double auto-register. 5. model_routing.read_active_model_from_transcript still returns the claude transcript model via provider (no silent None regression) — existing test_model_routing passes. 6. ruff + mypy clean. NEGATIVE: providers.get('zai') raises KeyError (not silently returns a stub); read_active_model_from_transcript(None) returns None without raising; importing the package when a provider module is malformed must not crash the whole registry (other providers still register).

## Plan

## Rollback

git checkout scripts/providers scripts/model_routing.py — all changes are within the untracked providers/ dir + one tracked file diff; revert restores prior (pre-branch) state.

## Journal

- 2026-06-19T08:14:10Z [implementation] — Rewrote providers package: lazy single-path registration via _register_self() called by _registry.auto_register (fixes double/circular register + reset() re-population). claude.py delegates to model_routing parser (no dup block). kilo.py reads KILO_MODEL env / .kilocode config. Deleted zai.py. Reverted model_routing.read_active_model_from_transcript to pure JSONL parser (removed broken 'from scripts.providers' top import that silently nulled detection). Smoke: available=[claude,cursor,kilo,qwen], zai->KeyError, reset re-registers, broken module skipped, claude detects live transcript (opus-4-8).
- 2026-06-19T08:14:41Z [implementation] — AC1 ✓ providers.available()==[claude,cursor,kilo,qwen], no zai, no exc. AC2 ✓ zai.py deleted. AC3 ✓ claude.py rewritten, no dup block, imports clean. AC4 ✓ single lazy registration via _register_self/auto_register, no double/circular. AC5 ✓ read_active_model_from_transcript restored to pure JSONL parser; test_model_routing+test_task_start_model_banner+test_routing_adherence 82 passed (no silent None regression). AC6 ✓ ruff + mypy clean on 8 files. NEG ✓ get('zai')→KeyError; read_active_model_from_transcript(None/absent)→None no raise; broken module skipped, registry intact (smoke-tested).
