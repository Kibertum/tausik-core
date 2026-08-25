---
slug: v155-kilo-bootstrap-generator
title: "Bootstrap --ide kilo generator (.kilocode/)"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "bootstrap/bootstrap_kilo.py, bootstrap/bootstrap.py, bootstrap/bootstrap_modes.py, tests/test_bootstrap_kilo.py (new)"
scope_exclude: "scripts/* (done), docs/* (next task), other bootstrap_* generators"
relevant_files:
  - "bootstrap/bootstrap_kilo.py"
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_modes.py"
  - "tests/test_bootstrap_kilo.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:30:43Z"
---

## Goal

Fix bootstrap_kilo.py to write .kilocode/mcp.json (correct Kilo path + mcp key) and .kilocode/commands/*.md; wire _IDE_DIRS kilo into bootstrap.py so `bootstrap.py --ide kilo` produces a working Kilo MCP+commands setup. Tested via test_bootstrap_kilo.py.

## Acceptance Criteria

1. bootstrap.py _IDE_DIRS gains 'kilo':'.kilo'; --ide choices (bootstrap_modes) include 'kilo'; bootstrap_ide dispatches kilo→generate_kilo_config+generate_kilo_commands. 2. generate_kilo_config writes the TAUSIK MCP stanza to BOTH .kilo/kilo.jsonc and .kilocode/mcp.json (Decision #120), key 'mcp', command as ARRAY [python, server.py, --project, dir], type:'local', enabled:true; merges existing servers; includes tausik-project (+rag/brain if present). 3. Server path resolves to the copied .kilo/mcp/project/server.py when present, else lib_dir/harness/claude/mcp/project/server.py. 4. generate_kilo_commands writes .md stubs into target_dir/commands/. 5. tests/test_bootstrap_kilo.py green; ruff+mypy clean; bootstrap_kilo.py <400 lines. NEGATIVE: generate_kilo_config merges (does not clobber) a pre-existing user server in the file; running twice is idempotent (no duplicate/garbage); malformed existing json is replaced, not crashed on; missing server.py → that server omitted, no exception.

## Plan

## Rollback

git checkout bootstrap/bootstrap.py bootstrap/bootstrap_modes.py && git checkout bootstrap/bootstrap_kilo.py (revert to branch scaffold) && rm tests/test_bootstrap_kilo.py — additive IDE target, no effect on other IDEs.

## Journal

- 2026-06-19T08:30:23Z [implementation] — Rewrote bootstrap_kilo.py: generate_kilo_config writes mcp stanza (project+rag+brain if present) to BOTH .kilo/kilo.jsonc and .kilocode/mcp.json (command as array, type:local, enabled), merges existing+preserves user servers, idempotent, replaces malformed json, omits missing servers, config_paths override. generate_kilo_commands writes 11 stubs to commands/. Wired bootstrap.py (_IDE_DIRS kilo=.kilo, import, dispatch, --ide all) + bootstrap_modes choices. 9 new tests + 118 bootstrap tests pass; ruff+mypy clean; 177L<400.
- 2026-06-19T08:30:42Z [implementation] — AC1 ✓ _IDE_DIRS kilo=.kilo, --ide choices include kilo (bootstrap_modes), dispatch wired. AC2 ✓ writes both .kilo/kilo.jsonc + .kilocode/mcp.json, mcp key, command array, type local, enabled — tests/test_bootstrap_kilo.py::test_config_written_to_both_paths, ::test_config_schema_is_kilo_native. AC3 ✓ ::test_prefers_copied_server_over_lib. AC4 ✓ ::test_commands_written. AC5 ✓ 9 new + 118 bootstrap tests pass, ruff+mypy clean, 177L<400. NEGATIVE ✓ ::test_merge_preserves_user_servers, ::test_idempotent, ::test_malformed_existing_is_replaced, ::test_no_server_returns_empty. Knowledge: gotcha Memory #178 + Decision #120 (version-dependent path). Domain: `bootstrap.py --ide kilo` produces a Kilo-native MCP config that loads tausik-project server in real Kilo (addon+CLI), regardless of which config path that Kilo build reads.
