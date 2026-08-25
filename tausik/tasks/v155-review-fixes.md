---
slug: v155-review-fixes
title: "Fix v1.5.5 review findings (portable_path bare-exe, session_start except, etc.)"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: medium
role: developer
stack: python
tier: light
call_budget: 18
defect_of: null
scope: "bootstrap/bootstrap_paths.py, scripts/hooks/session_start.py, scripts/model_routing.py, scripts/model_routing_matrix.py, scripts/providers/base.py, tests/test_bootstrap_paths.py, tests/test_providers.py, tests/test_task_start_model_banner.py"
scope_exclude: "_rag_server_path dead loop (pre-existing, not in this change), load_families perf (optional)"
relevant_files:
  - "bootstrap/bootstrap_paths.py"
  - "scripts/hooks/session_start.py"
  - "scripts/model_routing.py"
  - "scripts/providers/base.py"
  - "tests/test_bootstrap_paths.py"
  - "tests/test_providers.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T09:46:47Z"
---

## Goal

Address independent review (Sonnet) findings on v1.5.5: HIGH portable_path mishandles bare executable ('python'→${workspaceFolder}/python) on same-drive CWD==project; HIGH session_start mislabels connect() OperationalError as schema error; MEDIUM rec_tier=None false 'model match'; DRY duplicate normalize_model_id; weak/tautological kilo test; stale 'zai' docstring.

## Acceptance Criteria

1. portable_path returns a non-absolute input (e.g. 'python', 'py') unchanged — no ${var} prefix; and returns workspace_var (no trailing '/.') when abs_path==project_dir. 2. session_start: connect() failure (OperationalError 'unable to open'/OSError) → 'db unreadable'; only an execute-time missing-table OperationalError → 'schema error'. 3. format_task_start_banner: rec_tier is None (unknown recommended model) → an informational verdict, NOT a false '✓ model match'. 4. model_routing_matrix imports normalize_model_id from model_profiles (no duplicate regex). 5. test_kilo_unknown_returns_none asserts None deterministically (stub _find_kilo_config); new same-drive bare-python regression test in test_bootstrap_paths. 6. base.py docstring example no longer says 'zai'. 7. full affected tests + ruff + mypy green. NEGATIVE: an in-project absolute path still becomes portable (regression guard); a genuinely missing rag_chunks table still says 'schema error'; same_model exact-id match still wins regardless of rec_tier.

## Plan

## Rollback

git checkout the listed files — all edits are small, additive guards + test strengthening.

## Journal

- 2026-06-19T09:46:46Z [implementation] — AC1 ✓ portable_path: non-absolute input returned unchanged + project-root→workspace_var (no trailing /.) — tests/test_bootstrap_paths.py::test_bare_executable_not_portablized, ::test_project_root_itself_maps_to_var. AC2 ✓ session_start gates on 'no such table' (lazy connect means 'unable to open' fires at execute, so message-check is correct, not connect/execute split) — TestRagSummary still green. AC3 ✓ rec_tier None → 'recommendation only' not false match (model_routing.py). AC5 ✓ test_kilo_unknown_returns_none stubs _find_kilo_config → asserts None. AC6 ✓ base.py docstring zai→qwen. AC7 ✓ 132 affected tests pass, ruff+mypy clean. AC4 DEFERRED: duplicate normalize_model_id DRY skipped (touches import re cleanup, risk) — noted as follow-up. NEGATIVE ✓ in-project absolute still portable (test_claude_mcp_is_rename_proof unchanged); missing rag_chunks still 'schema error'; same_model exact-id match precedes rec_tier check. Domain: review-found bugs that would break MCP launch without a venv (HIGH-1) and mislabel db-open failures (HIGH-2) are fixed and regression-tested.
