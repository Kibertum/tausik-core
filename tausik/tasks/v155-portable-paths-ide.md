---
slug: v155-portable-paths-ide
title: "Rename-proof paths: Claude .mcp.json + Cursor + Claude hooks"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "bootstrap/bootstrap_paths.py (new), bootstrap/bootstrap_generate.py, bootstrap/bootstrap_kilo.py, tests/test_bootstrap_generate_mcp.py, tests/test_bootstrap_kilo.py, tests/test_bootstrap_paths.py (new)"
scope_exclude: "bootstrap_qwen.py (Qwen has no workspace var — deferred), scripts/*"
relevant_files:
  - "bootstrap/bootstrap_paths.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_kilo.py"
  - "tests/test_bootstrap_paths.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T09:10:30Z"
---

## Goal

Eliminate absolute project paths from generated Claude .mcp.json, Cursor .cursor/mcp.json, and Claude settings.json hooks so a project-folder rename no longer breaks them. Use ${CLAUDE_PROJECT_DIR:-.} (Claude .mcp.json — not available at parse, needs fallback), ${CLAUDE_PROJECT_DIR} (Claude hooks), ${workspaceFolder} (Cursor). Shared helper portable_path; refactor Kilo onto it. Qwen unchanged (no workspace var — separate follow-up).

## Acceptance Criteria

1. New bootstrap/bootstrap_paths.py::portable_path(abs_path, project_dir, workspace_var) returns workspace_var+'/'+relpath when abs_path is inside project_dir, else the absolute forward-slashed path. 2. generate_mcp_json (Claude) emits ${CLAUDE_PROJECT_DIR:-.}-prefixed server paths + python (when in-project) and --project=${CLAUDE_PROJECT_DIR:-.}. 3. generate_cursor_mcp_json emits ${workspaceFolder}-prefixed in-project paths + --project=${workspaceFolder}. 4. generate_settings_claude hooks reference ${CLAUDE_PROJECT_DIR}/.../hook.py (no quotes — preserves parity tokenizer) when hooks dir is in-project, else absolute. 5. bootstrap_kilo refactored to use the shared helper (still ${workspaceFolder}); its tests pass. 6. Existing test_bootstrap_generate_mcp + hooks_parity + bootstrap tests pass (paths outside project stay absolute); ruff+mypy clean. NEGATIVE: an external venv python / external lib hooks dir (outside project) stays ABSOLUTE — no workspace var misapplied (verified by test); cross-drive path (ValueError on relpath) returns absolute, no crash.

## Plan

## Rollback

git checkout bootstrap/bootstrap_generate.py bootstrap/bootstrap_kilo.py tests/ && rm bootstrap/bootstrap_paths.py tests/test_bootstrap_paths.py — isolated to bootstrap generators; defaults outside-project keep prior absolute behaviour.

## Journal

- 2026-06-19T09:10:29Z [implementation] — AC1 ✓ bootstrap_paths.portable_path — tests/test_bootstrap_paths.py::test_in_project_becomes_var_relative + ::test_outside_project_stays_absolute. AC2 ✓ Claude .mcp.json ${CLAUDE_PROJECT_DIR:-.} — ::test_claude_mcp_is_rename_proof (server+venv-in-project+--project). AC3 ✓ Cursor ${workspaceFolder} — ::test_cursor_mcp_uses_workspacefolder. AC4 ✓ Claude hooks ${CLAUDE_PROJECT_DIR}, no quotes — ::test_claude_hooks_are_rename_proof. AC5 ✓ kilo refactored to shared helper, test_bootstrap_kilo passes. AC6 ✓ 150 bootstrap/hooks/session tests pass; ruff+mypy clean. NEGATIVE ✓ external python stays absolute — ::test_claude_mcp_external_python_stays_absolute; cross-drive ValueError→absolute handled in helper. Domain: renaming the project folder no longer breaks Claude/Cursor/Kilo MCP launch or Claude hooks — directly resolves the user complaint. Qwen deferred (v156, no workspace var).
