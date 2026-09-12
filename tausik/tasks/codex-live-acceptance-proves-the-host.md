---
slug: codex-live-acceptance-proves-the-host
title: "Codex вживую: MCP, skills, agents и нативный hook подтверждены на реальном хосте"
status: active
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
  - tausik-live-acceptance-probe-codex.txt
scope_paths:
  - tausik-live-acceptance-probe-codex.txt
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

На реальном Codex после bootstrap подтвердить не только существование файлов, но и работающие MCP, обнаружение skills/agents и отказ нативного hook на контролируемой запрещённой операции. Сохранить воспроизводимое evidence без изменения пользовательских данных.

## Acceptance Criteria

AC-1: после bootstrap --ide codex реальный Codex вызывает tausik-project MCP и получает структурированный ответ. AC-2: .codex/skills и .codex/agents содержат соответственно активные SKILL.md и TOML агентов, а в реальном хосте доступны их процедуры/роли. AC-3: контролируемая операция записи вне ACL блокируется нативным Codex hook до изменения файла; результат зафиксирован как live evidence. AC-4: негативный сценарий не оставляет тестовый или пользовательский файл после отказа. AC-5: evidence отличает живое наблюдение хоста от unit/integration-тестов и не объявляет непроверенное hard.

## Plan

[{"step": "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u0438\u0442\u044c \u0438\u0437\u043e\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u0443\u044e \u0438 \u0440\u0430\u0437\u0440\u0435\u0448\u0451\u043d\u043d\u0443\u044e \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u044c\u043d\u0443\u044e \u0446\u0435\u043b\u044c, \u0437\u0430\u0442\u0435\u043c \u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c bootstrap --ide codex.", "done": false}, {"step": "\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c \u0436\u0438\u0432\u043e\u0439 MCP-\u0432\u044b\u0437\u043e\u0432 \u0438 \u043f\u0440\u0438\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 skill/agent \u0430\u0440\u0442\u0435\u0444\u0430\u043a\u0442\u043e\u0432 \u0432 \u0442\u0435\u043a\u0443\u0449\u0435\u043c Codex-\u0445\u043e\u0441\u0442\u0435.", "done": false}, {"step": "\u0412\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u044c \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u044b\u0439 \u043d\u0435\u0433\u0430\u0442\u0438\u0432\u043d\u044b\u0439 \u043e\u043f\u044b\u0442 \u0441 \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u0435\u0439 \u0432\u043d\u0435 ACL \u0438 \u0437\u0430\u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0438\u043c\u0435\u043d\u043d\u043e \u043e\u0442\u0432\u0435\u0442 \u043d\u0430\u0442\u0438\u0432\u043d\u043e\u0433\u043e hook.", "done": false}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432\u043e\u0441\u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u043c\u0443\u044e evidence-\u043f\u0440\u043e\u0446\u0435\u0434\u0443\u0440\u0443 \u0438 \u0442\u0435\u0441\u0442\u044b, \u043f\u0440\u043e\u0433\u043d\u0430\u0442\u044c verify \u0438 \u0437\u0430\u043a\u0440\u044b\u0442\u044c \u0441 \u043f\u043e\u0434\u043f\u0438\u0441\u0430\u043d\u043d\u043e\u0439 \u043a\u0432\u0438\u0442\u0430\u043d\u0446\u0438\u0435\u0439.", "done": false}]

## Rollback

Delete the named disposable probe; it contains no user or product data. Any evidence lives in the task journal.

## Journal

- 2026-09-10T07:00:38Z [implementation] — User-authorized disposable probe tausik-live-acceptance-probe-codex.txt was created, existence confirmed, then deleted and absence confirmed. This validates cleanup only: it was performed through the workspace tool, not the Codex extension, so it is explicitly NOT native-hook acceptance evidence.
- 2026-09-12T13:38:00Z [implementation] — Unblocked in session #244: the prerequisite write-gate-is-blind-to-pathlib-writes is closed (signed run #2474), so Rule 2 may be claimed hard for the pathlib idiom in the live run. This task is reserved for a real Codex host session: the evidence must be live host observation, not Claude's tests. Checklist for the Codex run: (1) bootstrap --ide codex, bootstrap --check clean; (2) call tausik-project MCP (tausik_status) and record the structured reply; (3) list .codex/skills and .codex/agents and invoke one skill and one agent by name; (4) with an active task whose scope_paths exclude it, run python - <<PY that Path('outside.txt').write_text(...) — the native hook must block before the file exists; (5) confirm no residue file after the refusal; (6) log each step as live evidence with the host's own output.
