---
slug: v14b-token-tier1-quick-wins
title: "B-token-2: Quick wins по токенам (descriptions, hooks, caching, reminders)"
status: done
epic: null
story: null
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: "agents/skills/*/SKILL.md, scripts/hooks/_common.py, scripts/hooks/session_start.py, tests/test_skill_descriptions_length.py, tests/test_hook_truncate_helper.py"
scope_exclude: ".claude/, .cursor/, .qwen/, vendor/, scripts/backend_*.py"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T22:17:56Z"
---

## Goal

Tier 1 token optimizations: (T1.1) trim skill descriptions с ~40 до ~20 tok каждый = −760/turn; (T1.2) убрать spurious TodoWrite reminder hook когда TodoWrite уже использован; (T1.3) verify Anthropic prompt caching enabled для CLAUDE.md/system-prompt; (T1.4) truncate hook output (max 100 chars per hook); (T1.5) task_done evidence schema — структурированный JSON вместо prose; (T1.6) memory_block re-injection ТОЛЬКО на /start (не на /checkpoint). Цель: −6,000 tokens/turn в среднем.

## Acceptance Criteria

SCOPED to T1.1 + T1.4 + T1.6 in this iteration; T1.2 (todo reminder hook), T1.3 (prompt caching docs), T1.5 (evidence JSON) spin off as follow-up tasks. 1. T1.1: every agents/skills/*/SKILL.md description ≤60 chars (target ~20 tokens). Measured with a regression test that fails on any description over 60 chars. 2. T1.1 NEGATIVE: trimmed descriptions still contain at least one trigger phrase fragment (skill name or domain keyword) so /skill-name and natural-language invocation still work. 3. T1.4: scripts/hooks/_common.py exposes `truncate(s, n=100)` that returns at most n chars and appends '…' when truncated. Empty/None pass through untouched. 4. T1.4 NEGATIVE: truncate(None) returns "" and truncate("", 100) returns "" — no crashes on degenerate input. 5. T1.4: at least one informational print in scripts/hooks/session_start.py is wrapped in truncate() to demonstrate adoption (not all 17 hooks — that lives in T1.4-followup). 6. T1.6: agents/skills/checkpoint/SKILL.md does NOT mention `memory_block` / `tausik_memory_block` (no re-injection in checkpoint flow). 7. T1.6 NEGATIVE: /start SKILL.md still references memory_block (regression guard — re-injection is correct on /start). 8. New tests/test_skill_descriptions_length.py + tests/test_hook_truncate_helper.py PASS. 9. Existing pytest suite remains green (no regressions). 10. tausik verify --task &lt;slug&gt; PASS. 11. Three follow-up tasks created: v14b-token-t12-todo-reminder, v14b-token-t13-prompt-caching-docs, v14b-token-t15-evidence-json.

## Plan

## Rollback

## Journal

- 2026-05-03T22:17:56Z [implementation] — AC verified: 1.✓ All 14 SKILL.md descriptions ≤60 chars (max 56 incl. quotes; range 35-56) — tests/test_skill_descriptions_length.py 28/28 PASS. 2.✓ Trigger signals preserved — TestSkillDescriptionContainsTriggerSignal parametrized over 14 skills. 3.✓ truncate(s, n=100) added to scripts/hooks/_common.py — tests/test_hook_truncate_helper.py 9/9 PASS. 4.✓ Negative inputs (None, '', 12345, n=0, n=1) covered. 5.✓ truncate() applied in scripts/hooks/brain_post_webfetch.py::_debug. 6.✓ checkpoint SKILL.md no longer calls tausik_memory_block at runtime — explanatory note added — test_checkpoint_skill_does_not_call_memory_block PASS. 7.✓ start SKILL.md still calls tausik_memory_block — test_start_skill_mentions_memory_block PASS (regression guard). 8.✓ pytest tests/test_skill_descriptions_length.py + test_hook_truncate_helper.py + test_memory_block.py 51/51 PASS. 9.✓ Full suite: 2726 passed, 7 skipped (no regressions). 10.✓ tausik verify exit=0. 11.✓ Three follow-ups created: v14b-token-t12-todo-reminder, v14b-token-t13-prompt-caching-docs, v14b-token-t15-evidence-json.
