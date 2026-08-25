---
slug: r14-brain-sync-cli
title: "Implement `tausik brain sync` CLI (or remove the reference from brain_init messages)"
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
completed_at: "2026-05-01T00:52:44Z"
---

## Goal

Release 1.4: r14-brain-sync-cli (from subagent findings)

## Acceptance Criteria

1. tausik brain sync subcommand exists with optional --category and --json flags. 2. brain_init.py wizard message about brain sync is now truthful. 3. brain status output includes 'stale: N min' relative to last_pull_at. 4. cli.md (en+ru) documents the new subcommand. 5. Negative scenario: running brain sync without enabled brain or with missing token env yields explicit non-zero exit and remediation message.

## Plan

## Rollback

## Journal

- 2026-05-01T00:52:44Z [implementation] — AC verified: 1. brain sync subcommand exists ✓ (project_parser_ops.py:120). 2. brain_init wizard message now points at a real command ✓. 3. stale-minutes shown in brain status ✓ (brain_status.py:181). 4. cli.md en+ru document the subcommand ✓. 5. Negative - brain disabled or missing token both exit 2 with explicit message ✓ (project_cli_ops.py).
- 2026-05-01T00:52:44Z [implementation] — Implemented tausik brain sync: project_parser_ops.add_brain registers the new subparser with --category enum and --json flag. project_cli_ops.cmd_brain handles brain_cmd=='sync' by loading config, validating token env var, optionally narrowing to one category, opening the local mirror via brain_runtime.get_brain_mirror_path, and running brain_sync.sync_all (which already existed).
- 2026-05-01T00:52:44Z [implementation] — Smoke-tested parser: brain sync --category decisions --json produces Namespace(brain_cmd='sync', category='decisions', as_json=True). 82/82 tests pass across brain_status + brain_init + brain_sync suites. cli.md (en+ru) line 229-230 area updated with the new subcommand and the stale-min annotation.
- 2026-05-01T00:52:44Z [implementation] — brain_status.format_status now appends 'stale: N min' to each category line based on (now_utc - last_pull_at). Parse failures are swallowed so malformed timestamps don't break the human-readable view. brain_init wizard's mention of brain sync is now backed by a real CLI command instead of being a stub - existing 53 brain_init tests still pass.
