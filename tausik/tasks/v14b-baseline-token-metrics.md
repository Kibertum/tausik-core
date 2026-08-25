---
slug: v14b-baseline-token-metrics
title: "Baseline token metrics — per-command input/output measurement infra"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/hooks/token_metrics.py (NEW PostToolUse hook), scripts/service_token_metrics.py (NEW aggregation service), scripts/project_cli_extra.py (extend cmd_metrics with 'tokens' subcommand), scripts/project_parser.py (add 'metrics tokens' parser), tests/test_token_metrics.py (NEW), bootstrap config to register new hook"
scope_exclude: "Existing session_metrics.py and session_usage_metrics table NOT modified — additive only. No auto-commit logic. No API key handling — only API response.usage block. No baseline.json captured in this session (requires ≥10 future sessions to populate per AC #3). No Gate A decision in this session (requires baseline data per AC #6)."
relevant_files:
  - "scripts/hooks/token_metrics.py"
  - "scripts/service_token_metrics.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_ops.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_token_metrics.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T11:18:42Z"
---

## Goal

Per-command input/output token usage recorded to .tausik/token_metrics.jsonl via PostToolUse hook. tausik metrics tokens aggregates per-command medians. Baseline data captured over ≥10 sample sessions for /start, /task, /review, /audit, verify — establishes Gate A reference numbers.

## Acceptance Criteria

1. PostToolUse or session-end hook records {command, input_tokens, output_tokens, cache_read, cache_create, ts, session_id} to .tausik/token_metrics.jsonl (append-only). 2. tausik metrics tokens aggregates per-command medians, p50/p90 over last N sessions; default N=10. 3. Baseline run captured: ≥10 representative sessions documented; per-command medians stored as canonical baseline.json under .tausik/baselines/. 4. Pre-req: prompt caching active per v14b-token-t13 (otherwise measurements noisy). 5. Tests: hook unit test with mocked API response; aggregation query test on synthetic JSONL. 6. Gate A decision recorded as tausik_decide: heavy ops (review+audit+verify) > 20% of input tokens → proceed to Phase B sub-agents. 7. NEGATIVE: malformed/empty PostToolUse payload (missing usage block, non-JSON, IO error writing JSONL) does NOT crash the hook — silent best-effort with stderr warning, hook returns 0 so Claude Code continues normally. 8. NEGATIVE: tausik metrics tokens with N=0 or empty JSONL returns clean 'no data yet' message instead of stack trace; with --last larger than available rows, returns whatever exists.

## Plan

[{"step": "Pre-req confirmed: v14b-token-t13-prompt-caching-docs is done", "done": true}, {"step": "Design JSONL schema {ts, session_id, tool_name, input_tokens, output_tokens, cache_read, cache_create, model}", "done": true}, {"step": "Implement scripts/hooks/token_metrics.py (PostToolUse \u2014 defensive: malformed/missing payload returns 0)", "done": true}, {"step": "Implement scripts/service_token_metrics.py \u2014 read JSONL + aggregate per-tool p50/p90 over last N sessions", "done": true}, {"step": "Wire CLI: add 'tokens' subparser in add_metrics + dispatch in cmd_metrics", "done": true}, {"step": "Register hook in bootstrap_hooks.py + bootstrap config", "done": true}, {"step": "Tests: hook unit (mocked payload, malformed payload, IO error path) + aggregator (synthetic JSONL, empty JSONL, N=0)", "done": true}, {"step": "Bootstrap sync .claude/ + tausik doctor drift-clean", "done": true}, {"step": "task_done with deferred-AC note (#3 baseline \u226510 sessions + #6 Gate A decision require future runs)", "done": true}]

## Rollback

## Journal

- 2026-05-06T11:14:04Z [implementation] — AC-1: ✓ tested via tests/test_token_metrics.py::TestHook::test_full_payload_records_row — JSONL row written with all 8 schema fields (ts, session_id, tool_name, input/output_tokens, cache_read, cache_create, model). Hook in scripts/hooks/token_metrics.py:118-133.
- 2026-05-06T11:14:04Z [implementation] — AC-2: ✓ tested via tests/test_token_metrics.py::TestAggregate::test_aggregates_per_tool_with_p50_p90 + test_filter_keeps_only_last_n_sessions. Implementation in scripts/service_token_metrics.py::aggregate (default last_n=10, returns per-tool input_tokens_p50/p90/total). CLI subcmd: tausik metrics tokens [--last N] [--json] in project_parser_ops.py + project_cli_ops.py.
- 2026-05-06T11:14:04Z [implementation] — AC-3: DEFERRED — baseline ≥10 sessions canonical baseline.json requires future runs. Infrastructure ready: hook registered in bootstrap_hooks.py, drift-clean per tausik doctor. Will accumulate naturally as user runs sessions.
- 2026-05-06T11:14:04Z [implementation] — AC-4: ✓ pre-req v14b-token-t13-prompt-caching-docs is done (verified earlier). Cache fields captured via cache_read_input_tokens / cache_creation_input_tokens.
- 2026-05-06T11:14:04Z [implementation] — AC-5: ✓ tested via tests/test_token_metrics.py — 18 tests pass, includes hook unit (subprocess + mocked payload) and aggregation query (synthetic JSONL).
- 2026-05-06T11:14:05Z [implementation] — AC-6: DEFERRED — Gate A decision via tausik decide requires baseline data (depends on AC-3). Will record once ≥10 sessions accumulate.
- 2026-05-06T11:14:05Z [implementation] — AC-7: ✓ Negative — tested via TestHook::test_empty_stdin_silent_exit_zero, test_malformed_json_silent_exit_zero, test_payload_without_usage_block_skips, test_no_open_session_skips. Hook returns 0 in all error paths; IO failure caught and logged to stderr (token_metrics.py:131-133).
- 2026-05-06T11:14:05Z [implementation] — AC-8: ✓ Negative — tested via TestAggregate::test_no_jsonl_returns_zero_state and test_last_n_zero_returns_empty_window. format_table emits 'No token metrics recorded yet' for empty state. Verified live via .tausik/tausik metrics tokens (clean message, no stack trace).
- 2026-05-06T11:14:21Z [implementation] — Infrastructure complete (AC-1, 2, 4, 5, 7, 8 verified). NEW: scripts/hooks/token_metrics.py (143L, PostToolUse hook, defensive: malformed/missing payload returns 0 silently) + scripts/service_token_metrics.py (167L, p50/p90 aggregator + format_table) + tests/test_token_metrics.py (215L, 18 tests pass). MODIFIED: project_parser_ops.py (tokens subparser), project_cli_ops.py (cmd_metrics tokens dispatch), bootstrap_hooks.py (token_metrics.py registered as 7th PostToolUse hook). Bootstrap drift-clean. ruff clean, mypy clean (5 modified files). 135 pytest pass (incl. all 18 new). Live smoke test: tausik metrics tokens [--json] [--last 0] all return clean output. AC-3 (≥10 baseline sessions) and AC-6 (Gate A decide) DEFERRED — accumulate naturally as user runs future sessions; explicitly logged via task_log.
- 2026-05-06T11:17:27Z [implementation] — Infra complete + filesize follow-up. NEW: scripts/hooks/token_metrics.py + scripts/service_token_metrics.py + scripts/project_cli_metrics.py (extracted to keep project_cli_ops.py under 400) + tests/test_token_metrics.py (18 tests). MODIFIED: project_parser_ops.py, project_cli_ops.py (367L), bootstrap_hooks.py. AC-1/2/4/5/7/8 verified per per-AC task_log entries. AC-3 (≥10 baseline sessions) and AC-6 (Gate A decide) DEFERRED — accumulate as user runs sessions; explicitly logged. 146 pytest pass. Bootstrap drift-clean. ruff/mypy clean on changed files. Live smoke test: tausik metrics tokens [--json] [--last 0] all clean.
- 2026-05-06T11:18:33Z [implementation] — Closed after fixing two filesize+parity follow-ups: (a) project_cli_ops.py hit 408L, fixed by extracting metrics dispatch to NEW scripts/project_cli_metrics.py (now ops 367L); (b) test_qwen_has_every_claude_hook FAIL — added token_metrics.py to bootstrap_qwen.py PostToolUse list. tausik verify pytest now PASS (1000ms). All 8 AC have logged evidence: AC-1/2/4/5/7/8 verified, AC-3/6 deferred (need ≥10 sessions for baseline + Gate A).
- 2026-05-06T11:18:41Z [implementation] — Closed after fixing two filesize+parity follow-ups: extracted scripts/project_cli_metrics.py (cli_ops back to 367L) + added token_metrics.py to bootstrap_qwen.py for cross-IDE parity. tausik verify pytest PASS. AC-1/2/4/5/7/8 verified; AC-3/6 deferred (need ≥10 baseline sessions for Gate A).
