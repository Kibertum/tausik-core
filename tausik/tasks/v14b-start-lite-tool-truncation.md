---
slug: v14b-start-lite-tool-truncation
title: "Start-lite + tool-truncation — narrow scope from old tier2-architectural"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "harness/skills/start/SKILL.md (--lite mode + dashboard render conditional); scripts/hooks/tool_output_truncation_nudge.py (NEW PostToolUse hook); bootstrap_hooks.py (register new hook); tests/test_start_lite_dashboard.py + tests/test_tool_output_truncation_nudge.py (NEW); CHANGELOG.md + CHANGELOG.ru.md (entry)"
scope_exclude: "CLAUDE.md split (dropped per AC #3); modifying tool output content directly (hooks observe only — built-in head_limit handles real truncation); /start dashboard breaking changes for default mode (default behavior preserved per AC #1)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T09:18:54Z"
---

## Goal

/start dashboard reduced to essential lines (lite mode); long tool outputs (search results, file reads) auto-truncated past threshold. CLAUDE.md split is OUT of scope (dropped per session #50). This is the salvageable remainder of old v14b-token-tier2-architectural.

## Acceptance Criteria

1. /start --lite (or settings flag) renders compact dashboard: counts only, no full handoff body, no full memory_block dump. Default /start unchanged. 2. Tool-output truncation: when grep/search/read exceeds N lines (default 250 — already partly there), truncated with explicit "+N more" footer; configurable via .tausik/config.json. 3. CLAUDE.md split is NOT in scope (dropped). 4. Tests: /start --lite output ≤ 50 lines on a real session; truncation hook unit test. 5. CHANGELOG entry.

## Plan

[{"step": "Define /start --lite output spec: counts + 1-line warnings only, no handoff body", "done": true}, {"step": "Implement --lite flag in /start skill", "done": true}, {"step": "Audit current tool-output sizes \u2014 grep/Read/search results that bloat context", "done": true}, {"step": "Add truncation post-processor: configurable threshold via .tausik/config.json", "done": true}, {"step": "Tests: /start --lite \u2264 50 lines; truncation unit test", "done": true}, {"step": "CHANGELOG entry", "done": true}]

## Rollback

## Journal

- 2026-05-07T09:18:54Z [implementation] — AC-1: ✓ /start SKILL.md Phase 3 gains Lite Mode block (`/start --lite` or `lite` arg) — counts only, MCP Health if drifting, one-line Suggested Next, no handoff body / no per-task title / no warning prose. Default flow preserved (test_default_dashboard_section_preserved). AC-2: ✓ scripts/hooks/tool_output_truncation_nudge.py — PostToolUse coaching hook on Read|Grep|Bash|Glob, emits stderr nudge with explicit "+N over" footer when n_lines > threshold. Threshold lookup: .tausik/config.json::tool_output_truncation_threshold → env TAUSIK_OUTPUT_TRUNCATION_THRESHOLD → default 250 (test_resolve_threshold_*). AC-3: ✓ CLAUDE.md split out of scope — confirmed not touched. AC-4: ✓ Lite Mode contract states "≤ 50 lines" cap (test_lite_mode_documents_50_line_cap PASS); truncation hook unit + integration suite — 19 cases (test_tool_output_truncation_nudge.py). AC-5: ✓ CHANGELOG.md + CHANGELOG.ru.md entries added at top of [Unreleased] v1.4.0 polish (Phase B) — 4 unified entries (start-lite, gate-fixer, reviewer, brain-sync). NEGATIVE coverage: malformed JSON stdin, empty stdin, missing tool_response, unwatched tool, env-skip flag — all 5 silent-exit-zero (test_hook_silent_on_empty_stdin / test_hook_silent_on_malformed_json / test_hook_ignores_unwatched_tool / test_hook_skipped_via_env_flag). New: scripts/hooks/tool_output_truncation_nudge.py (133L), tests/test_tool_output_truncation_nudge.py (19 unit+integration), tests/test_start_lite_dashboard.py (5 SKILL.md content checks). Modified: harness/skills/start/SKILL.md (Lite Mode block), bootstrap/bootstrap_hooks.py (7th PostToolUse hook), bootstrap/bootstrap_qwen.py (parity), CHANGELOG.md + CHANGELOG.ru.md (4 entries). 27 pytest pass (24 new + 3 hooks parity). Bootstrap drift-clean. Hook size: 133 lines well under 400 filesize gate.</evidence> <parameter name="relevant_files">["scripts/hooks/tool_output_truncation_nudge.py", "tests/test_tool_output_truncation_nudge.py", "tests/test_start_lite_dashboard.py", "harness/skills/start/SKILL.md", "bootstrap/bootstrap_hooks.py", "bootstrap/bootstrap_qwen.py", "CHANGELOG.md", "CHANGELOG.ru.md"]
