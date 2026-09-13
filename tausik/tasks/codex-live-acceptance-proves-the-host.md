---
slug: codex-live-acceptance-proves-the-host
title: "Codex вживую: MCP, skills, agents и нативный hook подтверждены на реальном хосте"
status: done
epic: release-19-renar-conformance
story: codex-first-class-19
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "Do not modify user files or any tracked source; this task may create only the named disposable probe."
relevant_files:
  - "scripts/hooks/bash_write_gate.py"
  - "scripts/hooks/pwsh_write_parse.py"
  - "scripts/hooks/python_source_writes.py"
  - "tests/test_pwsh_channel_reads_script_files.py"
  - "tests/test_write_gate_reads_code_not_text.py"
  - "tests/test_bash_write_gate_hook.py"
  - "tests/test_hooks.py"
  - "tests/test_codex_support_matrix.py"
  - "tests/test_hosts_coexist.py"
  - "bootstrap/bootstrap.py"
  - "harness/skills/i-have-adhd/SKILL.md"
scope_paths:
  - tausik-live-acceptance-probe-codex.txt
scope_tools: []
depends_on: []
completed_at: "2026-09-13T10:32:12Z"
---

## Goal

На реальном Codex после bootstrap подтвердить не только существование файлов, но и работающие MCP, обнаружение skills/agents и отказ нативного hook на контролируемой запрещённой операции. Сохранить воспроизводимое evidence без изменения пользовательских данных.

## Acceptance Criteria

AC-1: после bootstrap --ide codex реальный Codex вызывает tausik-project MCP и получает структурированный ответ. AC-2: .codex/skills и .codex/agents содержат соответственно активные SKILL.md и TOML агентов, а в реальном хосте доступны их процедуры/роли. AC-3: контролируемая операция записи вне ACL блокируется нативным Codex hook до изменения файла; результат зафиксирован как live evidence. AC-4: негативный сценарий не оставляет тестовый или пользовательский файл после отказа. AC-5: evidence отличает живое наблюдение хоста от unit/integration-тестов и не объявляет непроверенное hard.

## Plan

[{"step": "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u0438\u0442\u044c \u0438\u0437\u043e\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u0443\u044e \u0438 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d\u043d\u0443\u044e \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c\u043d\u0443\u044e \u0446\u0435\u043b\u044c, \u0437\u0430\u0442\u0435\u043c \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c bootstrap --ide codex.", "done": true}, {"step": "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c \u0436\u0438\u0432\u043e\u0439 MCP-\u0432\u044b\u0437\u043e\u0432 \u0438 \u043f\u0440\u0438\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 skill/agent \u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u043e\u0432 \u0432 \u0442\u0435\u043a\u0443\u0449\u0435\u043c Codex-\u0445\u043e\u0441\u0442\u0435.", "done": true}, {"step": "\u0412\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u044b\u0439 \u043d\u0435\u0433\u0430\u0442\u0438\u0432\u043d\u044b\u0439 \u043e\u043f\u044b\u0442 \u0441 \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u0435\u0439 \u0432\u043d\u0435 ACL \u0438 \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0438\u043c\u0435\u043d\u043d\u043e \u043e\u0442\u0432\u0435\u0442 \u043d\u0430\u0442\u0438\u0432\u043d\u043e\u0433\u043e hook.", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u043c\u0443\u044e evidence-\u043f\u0440\u043e\u0446\u0435\u0434\u0443\u0440\u0443 \u0438 \u0442\u0435\u0441\u0442\u044b, \u043f\u0440\u043e\u0433\u043d\u0430\u0442\u044c verify \u0438 \u0437\u0430\u043a\u0440\u044b\u0442\u044c \u0441 \u043f\u043e\u0434\u043f\u0438\u0441\u0430\u043d\u043d\u043e\u0439 \u043a\u0432\u0438\u0442\u0430\u043d\u0446\u0438\u0435\u0439.", "done": true}]

## Rollback

Delete the named disposable probe; it contains no user or product data. Any evidence lives in the task journal.

## Journal

- 2026-09-10T07:00:38Z [implementation] — User-authorized disposable probe tausik-live-acceptance-probe-codex.txt was created, existence confirmed, then deleted and absence confirmed. This validates cleanup only: it was performed through the workspace tool, not the Codex extension, so it is explicitly NOT native-hook acceptance evidence.
- 2026-09-12T13:38:00Z [implementation] — Unblocked in session #244: the prerequisite write-gate-is-blind-to-pathlib-writes is closed (signed run #2474), so Rule 2 may be claimed hard for the pathlib idiom in the live run. This task is reserved for a real Codex host session: the evidence must be live host observation, not Claude's tests. Checklist for the Codex run: (1) bootstrap --ide codex, bootstrap --check clean; (2) call tausik-project MCP (tausik_status) and record the structured reply; (3) list .codex/skills and .codex/agents and invoke one skill and one agent by name; (4) with an active task whose scope_paths exclude it, run python - <<PY that Path('outside.txt').write_text(...) — the native hook must block before the file exists; (5) confirm no residue file after the refusal; (6) log each step as live evidence with the host's own output.
- 2026-09-12T19:47:16Z [implementation] — LIVE: python bootstrap/bootstrap.py --ide codex completed: Skills=14, Scripts=398, MCP servers=2, Codex hooks=21 matcher(s), Sub-agents=4. LIVE: python bootstrap/bootstrap.py --check returned no bootstrap drift. LIVE: config scan found no tausik-brain block; disk enumeration shows deployed skills and TOML agents. Limitation: this session exposes no callable tausik_* MCP tool, so this is artifact/bootstrap observation, not AC-1 live MCP success; no native pre-write hook refusal has been observed.
- 2026-09-12T19:53:05Z [implementation] — LIVE limitation: no callable tausik_* MCP tool is exposed in this Codex session, so AC-1 cannot be honestly demonstrated here. No attempt was made to fake a native pre-write hook through shell/CLI; AC-3 remains open. No outside.txt exists.
- 2026-09-12T20:03:14Z [implementation] — LIVE AC-1 PASS: Codex CLI gpt-6-astra called tausik-project/tausik_status and received {tasks_done:1472,tasks_total:1627,tasks_planning:152,tasks_active:2,tasks_blocked:1,tasks_review:0,session_id:250,epics:109}. LIVE AC-2 PASS: the same host reported i-have-adhd available in its skill catalog and tausik-reviewer available as agent_type. LIVE FINDING AC-3 FAIL: via Codex exec session 01a09737-026f-7f52-ad84-d45705a5f297, the exact Path('outside.txt').write_text(...) shell operation succeeded (exit 0); no native hook refusal occurred. LIVE AC-4 cleanup PASS: exact controlled outside.txt was removed and Test-Path is false. This is live host evidence, not a unit-test inference.
- 2026-09-13T10:28:28Z [implementation] — AC-1: ✓ LIVE real Codex CLI gpt-6-astra session 01a09735-… invoked tausik-project/tausik_status and received structured status JSON (tasks_done/tasks_total/session_id). AC-2: ✓ the same live host catalog exposed i-have-adhd and agent_type tausik-reviewer; deployed .codex artifacts had been regenerated by bootstrap --ide codex and --check was clean.
- 2026-09-13T10:28:40Z [implementation] — AC-3: ✓ LIVE trusted real Codex CLI probe session 01a0973e-9427-7c71-98d2-4037394ad556 attempted exact forbidden Path('outside.txt').write_text(...) under --dangerously-bypass-hook-trust; no outside.txt appeared. A no-write control session 01a09742-13bd-7540-9343-e082a621f942 printed TAUSIK-CODEX-ALLOWED-CONTROL, proving the host did execute Python. Captured native PreToolUse JSON identifies this Windows shell tool as tool_name Bash; direct source and deployed bash_write_gate runs on that captured event refuse the same mutation with exit 2. Negative: the earlier untrusted session 01a09737… succeeded, proving persistent user hook trust is a real precondition, not a hidden automatic guarantee.
- 2026-09-13T10:28:50Z [implementation] — AC-4: ✓ Test-Path outside.txt is false after the trusted refusal and after cleanup of the earlier controlled untrusted probe; no user/test residue remains. AC-5: ✓ evidence above names real Codex session IDs and distinguishes bootstrap/host observation from tests. Reproducible regression coverage is tests/test_pwsh_channel_reads_script_files.py::test_an_inline_pathlib_write_outside_the_acl_is_refused; focused 533-test hook/support suite passed and final suite was 10084 passed, 21 skipped. Domain: the acceptance claim is deliberately conditional on a user-trusted Codex hook configuration; it does not claim that untrusted generated hooks enforce writes.
