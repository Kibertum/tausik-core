---
slug: session-rollup-window-attribution
title: "Разделить посессионный rollup метрик по временным окнам транскрипта"
status: active
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: v14b-rag-nudge-replay-benchmark
scope: "Change scripts/hooks/session_metrics.py, scripts/service_session.py and directly related session-window helper only if necessary; add focused behavioral tests under tests/test_session_metrics_parse.py and tests/test_session_end_metrics_hook.py; update CHANGELOG.md and CHANGELOG.ru.md plus generated task/story state."
scope_exclude: "Do not claim RAG savings, change RAG behavior, alter historical session_usage_metrics rows, weaken timestamp-containment semantics, release, tag, push, or modify user-owned .agents/."
relevant_files:
  - "scripts/hooks/session_metrics.py"
  - "scripts/service_session.py"
  - "tests/test_session_metrics_parse.py"
  - "tests/test_session_end_metrics_hook.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/v14b-rag-nudge-replay-benchmark.md"
scope_paths:
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/session_windows.py"
  - "scripts/service_session.py"
  - "tests/test_session_metrics_parse.py"
  - "tests/test_session_end_metrics_hook.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/session-rollup-window-attribution.md"
  - "tausik/tasks/v14b-rag-nudge-replay-benchmark.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Устранить дефект, из-за которого SessionEnd записывает суммарные метрики полного много-сессионного транскрипта в session_usage_metrics текущей сессии. Это искажает авторитетный посессионный источник и блокирует честный replay-бенчмарк экономии токенов.

## Acceptance Criteria

AC-1: rollup session_usage_metrics получает только записи транскрипта, чьи timestamps принадлежат целевой сессии по [started_at, ended_at); записи вне окна не приписываются. AC-2: регрессионный тест с одним транскриптом и двумя сессиями доказывает разные totals, а не копию полного транскрипта в последнюю. AC-3: отсутствующий или непарсящийся timestamp не угадывает сессию и не попадает в rollup. AC-4: текущий одно-сессионный путь и token_metrics JSONL сохраняют поведение. AC-5: threat surface: a transcript from another session must not overwrite a session's authoritative accounting; focused pytest, ruff и signed tausik_verify проходят.

## Plan

[{"step": "Reproduce the incorrect full-transcript rollup with a two-session transcript and establish the smallest window-aware metric boundary.", "done": true}, {"step": "Implement a pure per-session transcript aggregation path and make SessionEnd record only the active session's attributable metrics.", "done": true}, {"step": "Add focused behavioral regression coverage for split, missing timestamp, and single-session compatibility.", "done": true}, {"step": "Run focused checks, ruff and signed verify; record evidence without modifying historical measurements.", "done": false}]

## Rollback

Revert the dedicated commit; no historical DB migration or destructive data rewrite is permitted.

## Journal

- 2026-09-11T13:21:17Z [implementation] — Started defect task after reproducing the attribution path in source. Scope is confined to session rollup and its regression tests; no historical metric rewrite will be attempted. Next, establish whether the SessionEnd sequencing exposes a closed target window or requires explicitly binding the active session ID.
- 2026-09-11T13:23:50Z [implementation] — Implemented window-bounded rollup: parse_transcript now filters all accounting fields by an explicit timestamp resolver and target session; missing/unmapped timestamps are excluded. record_to_db forwards an explicit --session-id, and service_session passes the session it just closed. When an IDE hook has no explicit ID, it accepts only the proven newest open window; otherwise it skips authoritative DB recording. Focused parse, session-end and token-attribution tests: 59 passed; ruff passed; pytest dedupe audit passed.
- 2026-09-11T13:25:02Z [implementation] — Review gate run is blocked despite pytest output showing 55 passed: gate reports pytest FAIL without a failing assertion. Treating this as an unexplained gate/infrastructure result, not as passing evidence; investigating before signed verify.
- 2026-09-12T10:17:22Z [review] — The first signed verify was intentionally non-evidence because relevant_files had never been declared (scope_paths is only an edit ACL). Declared the actual source, tests and changelogs now; task export itself is deliberately excluded per verify receipt ownership convention.
- 2026-09-12T10:18:13Z [review] — The lone undeclared path is the parent benchmark's foreign task export, changed when the benchmark was blocked before this defect task. It is a real foreign projection (not this task's own export), so it is now declared rather than subtracted or ignored.
- 2026-09-12T10:51:34Z [implementation] — Commit gate found a concrete type defect in this task's uncommitted implementation: session_metrics.py:77 calls an optional timestamp resolver without a narrowing check. Fix is confined to the existing rollup scope; then rerun focused tests, mypy and signed verify.
- 2026-09-12T10:51:53Z [implementation] — Fixed the optional resolver narrowing required by mypy; focused session rollup tests and mypy now run before retrying the independent backlog-state commit.
