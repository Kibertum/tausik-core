---
slug: v14b-model-recommend-banner
title: "B-cost-1: Model recommendation banner — task_start emits loud warning if active model ≠ recommended"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing.py, scripts/service_task.py, scripts/project_config.py, tests/test_task_start_model_banner.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:57:03Z"
---

## Goal

Claude Code не принимает программный switch модели mid-session — поэтому model_routing.py остаётся recommendation only. В DB: 1964/1964 events на claude-opus-4-7 — пользователь де-факто никогда не переключает на Haiku/Sonnet. Цель: при `task start <slug>` фреймворк громко печатает рекомендованную модель + текущую (если можно прочитать из transcript) + warning если они расходятся. Это снижает trigger threshold для ручного `/fast` или смены модели в UI.

## Acceptance Criteria

1. `task_start <slug>` prints a model recommendation banner that includes (a) the recommended model based on task complexity, (b) the active model read from the latest Claude Code transcript (or "unknown" if not readable), (c) a loud "⚠ MODEL MISMATCH" line when they differ. 2. When recommended == active, banner prints a single OK line ("✓ model match") rather than the warning. 3. Banner is gated by a config flag (similar to is_task_next_model_hint_enabled) so it can be disabled in headless/CI runs. 4. NEGATIVE: when transcript cannot be located/read, banner falls back to recommendation-only line — no crash, no false warning. 5. NEGATIVE: when complexity is None/missing, default Sonnet recommendation is shown (existing suggest_model contract). 6. NEGATIVE: when banner config flag is disabled, no banner is emitted. 7. Existing task_start tests still pass; new tests cover match/mismatch/unreadable-transcript/disabled-flag paths. 8. pytest tests/test_model_routing.py and a new tests/test_task_start_model_banner.py PASS. 9. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T21:57:03Z [implementation] — AC verified: 1.✓ task_start now appends 3-line banner (recommended/active/verdict) — TestTaskStartIntegration::test_banner_appears_in_task_start_output. 2.✓ '✓ model match' on equal IDs — test_match_path. 3.✓ Config gate is_task_start_model_banner_enabled (default True, opt-out via task_start.model_banner=false) — TestConfigGate. 4.✓ Unreadable transcript → 'active model unknown' fallback — test_unreadable_transcript_yields_unknown. 5.✓ complexity=None → Sonnet default — test_default_complexity_uses_sonnet. 6.✓ Disabled flag suppresses banner — test_banner_disabled_by_config_flag. 7.✓ Existing model_routing tests 9/9 PASS unchanged. 8.✓ pytest tests/test_task_start_model_banner.py 27/27 PASS, tests/test_model_routing.py 9/9 PASS. 9.✓ tausik verify exit=0. NEGATIVE coverage: banner crash swallowed — test_banner_failure_does_not_break_task_start; 1m suffix normalized — test_match_with_1m_suffix.
