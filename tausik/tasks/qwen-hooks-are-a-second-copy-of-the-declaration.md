---
slug: qwen-hooks-are-a-second-copy-of-the-declaration
title: "Профиль qwen строит хуки своим списком вместо общего объявления — разойдётся молча и не сразу"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_hooks.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - "scripts/gate_cross_model_parity.py"
  - "tests/test_cross_model_parity_gate.py"
  - "tests/test_host_session_table.py"
scope_paths:
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_hooks.py"
  - "scripts/gate_cross_model_parity.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
  - "docs/en/*.md"
  - "docs/ru/*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:49:10Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР, смена #241, найдено при подключении Codex. Набор хуков объявлен один раз в bootstrap_hooks.build_hooks_dict и параметризован тем, КАК строится строка команды. Профиль claude им пользуется (bootstrap_generate.py:62), новый профиль codex тоже. Профиль qwen - НЕТ: bootstrap_qwen.py строит собственный список, повторяя имена скриптов вручную (task_gate.py, scope_write_gate.py, read_ledger_gate.py, memory_pretool_block.py, secret_scan.py, bash_firewall.py и далее по строкам 99-160).

ПОЧЕМУ ЭТО ДЕФЕКТ, А НЕ СТИЛЬ. Хук, добавленный в общее объявление, у qwen молча не появится. Расхождение не проявится сразу: оно проявится через несколько релизов и на чужой машине, где гейт, объявленный обязательным, просто не сработает. Ровно этот класс только что стоил Codex тринадцати мёртвых гейтов, и ровно против него написан AC-5 задачи codex-bootstrap-writes-hooks-that-actually-fire - но у qwen такой охраны нет.

СВЕРИТЬ ПЕРЕД ПРАВКОЙ: списки могут уже РАСХОДИТЬСЯ. Первый шаг - замер, какие хуки есть у claude и отсутствуют у qwen; если расхождение есть, оно и есть находка, а унификация - её починка.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРВЫМ: названо, какие хуки есть у claude и отсутствуют у qwen на момент правки - число и имена, а не 'расхождений нет'. AC-2 qwen строит набор из build_hooks_dict, как claude и codex. AC-3 Способ построения команды у qwen остаётся СВОИМ - унифицируется набор, а не путь. AC-4 НЕГАТИВ: тест краснеет, если у любого из трёх хостов набор событий или матчеров разошёлся с общим объявлением - той же формы, что TestНаборОдинНаДваХоста у codex, но на все три.

## Plan

## Rollback

Замена собственного списка qwen на общее объявление; откат - git revert. Развёрнутые профили пересоздаются bootstrap-ом, поэтому откат не оставляет мусора.

## Journal

- 2026-09-23T23:42:12Z [implementation] — AC-1: ✓ measurement — before the change (triples event/matcher/script, claude = build_hooks_dict, qwen = generate_settings_qwen into a tmp dir): PreToolUse identical; PostToolUse differs 9 claude-only / 6 qwen-only. Qwen registers activity_event, posttool_usage, task_call_counter, task_cost_budget_check, tool_output_truncation_nudge under a catch-all '*' where claude has specific matchers; qwen lacks the external-MCP-write registrations (serena/windows-mcp) for activity_event, task_call_counter and the truncation nudge; task_done_verify matches tausik_task_done|tausik_task_done_v2|Bash|PowerShell on qwen, tausik_task_done only on claude. The existing tests/test_bootstrap_hooks_parity.py compared script NAMES only, which is why none of this was red.
- 2026-09-23T23:43:25Z [implementation] — AC-2: ✓ tests/test_bootstrap_hooks_parity.py::test_every_host_registers_the_one_declared_set — bootstrap_qwen.generate_settings_qwen now does hooks = build_hooks_dict(_hook_cmd); with_mcp_registrations is no longer applied twice; the file went 367 -> 124 lines; re-measured triples: 0 claude-only, 0 qwen-only.
- 2026-09-23T23:43:25Z [implementation] — AC-3: ✓ review — Qwen keeps its own _hook_cmd (absolute deployed path, python -X utf8); only the SET is shared.
- 2026-09-23T23:43:25Z [implementation] — Root cause: bootstrap_qwen.py kept its own literal hook list (lines 90-330) instead of calling build_hooks_dict, and the only guard (test_bootstrap_hooks_parity) compared script basenames, which the drift in matchers left identical.
- 2026-09-23T23:43:26Z [implementation] — AC-4: ✓ tests/test_bootstrap_hooks_parity.py::test_every_host_registers_the_one_declared_set — negative, parametrized over claude_settings, qwen_settings, codex_hooks: events and ordered matchers must equal build_hooks_dict; mutation (HEAD copy of bootstrap_qwen.py restored) -> 1 failed, 2 passed; restored. 43 bootstrap tests green.
- 2026-09-23T23:43:26Z [implementation] — Decision inside the task: the qwen-only task_done_verify shell matcher was the CORRECT one — scripts/hooks/task_done_verify.py documents and implements the Bash CLI path (is_task_done_invocation) — so the shared declaration took it (|SHELL_MATCHER) and dropped the dead tausik_task_done_v2 alternation; docs/*/hooks.md say so.
- 2026-09-23T23:44:24Z [implementation] — Verify #2844 red on tests/test_host_session_table.py::test_each_claim_matches_the_profile: it grepped bootstrap_qwen.py for the literal 'SessionStart' — true only of the hand-kept copy. Updated to the new truth: Qwen, like Codex, must call build_hooks_dict, and the shared set must hold both session events; the hook branch now also refuses a host other than claude/codex/qwen claiming 'hook'.
- 2026-09-23T23:48:27Z [implementation] — NO-DEAD-END: each red was a guard doing its job on a real consequence of the unification (regex matcher semantics, stale accepted differences), fixed at the cause.
- 2026-09-23T23:48:27Z [implementation] — Two further reds on the way, both the fix reaching pinned text: (1) tests/test_pr5_hook_coverage.py refused 'mcp__tausik-project__tausik_task_done|Bash|PowerShell' — a hyphen makes the whole matcher a regex and Bash would match BashOutput; the shell audit is now its OWN entry on SHELL_MATCHER. (2) tests/test_cross_model_parity_gate.py: the four DECLARED_DIFFERENCES no longer existed; withdrawn under decision #389, and the 'motivation' test now pins that they stay gone. docs/*/session-active-time.md no longer claim activity_event runs on every tool.
