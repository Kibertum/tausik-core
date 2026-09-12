---
slug: v14b-rag-nudge-replay-benchmark
title: "Замер AC8 из v14b-rag-first-nudges: расход токенов на исследование до и после rag-first подсказок"
status: blocked
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: medium
role: qa
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "Read-only investigation of token/usage/transcript instrumentation, protocol documentation and focused tests only; no change to RAG behavior in the baseline phase."
scope_exclude: "Do not use deprecated per-tool PostToolUse counters as session usage; do not claim savings from one session; do not alter RAG behavior, release, tag or push."
relevant_files:
  - "docs/ru/research/rag-nudge-replay-protocol.md"
scope_paths:
  - "docs/ru/research/rag-nudge-replay-protocol.md"
  - "docs/en/research/rag-nudge-replay-protocol.md"
  - "tausik/tasks/v14b-rag-nudge-replay-benchmark.md"
  - "tausik/stories/release19-effective-context.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Принимает на себя критерий, отложенный при закрытии v14b-rag-first-nudges 2026-05-03: «AC 8 (replay benchmark) deferred: requires running an exploration session both before AND after the change, then diffing per-turn token burn from usage_events. Cannot be done within a single session». Критерий отложен законно — он физически требует двух сессий, — но оставался без владельца и без срока, что и обнаружила новая проверка doctor «Deferred AC». ВАЖНАЯ ОГОВОРКА, выясненная в v14b-followup-subagent-remeasure-quant (решение #201): прежний прибор для этого не годится. scripts/hooks/token_metrics.py помечен deprecated собственными словами «PostToolUse payload carried per-tool API usage. It does not — usage is message-level», и данные это подтверждают — input_tokens равен 2 у 7116 строк из 8046, а сумма cache_read даёт 568 млн для Bash за 26 сессий, потому что один кэшированный контекст пересчитывается на каждом вызове. Значит эта задача обязана начинаться с выбора прибора, а не с прогона: либо парсер транскрипта уровня сессии, либо usage_events, если он действительно несёт подушевую атрибуцию. Мерить «до и после» несуществующим прибором значит получить красивое число ни о чём — ровно та ошибка, которой в v14b уже стоила одна цепочка задач.

## Acceptance Criteria

AC-1: approved session-level source and its attribution limits are demonstrated against real records; deprecated per-tool metrics are rejected. AC-2: replay protocol fixes query corpus, baseline/post condition, metric formula and raw evidence location. AC-3: paired sessions use the same protocol; result reports both absolute tokens and delta, or explicitly records why comparison is invalid. AC-4: no token-saving claim is made without paired attributable evidence.

## Plan

[{"step": "Inventory candidate session-level token sources and reject known per-tool misattribution.", "done": true}, {"step": "Define a reproducible before/after replay protocol with a stable query corpus and attribution boundary.", "done": true}, {"step": "Run the first baseline session and preserve raw evidence without claiming an effect.", "done": false}, {"step": "Run the post-change session in a later session, compare the same metrics, and close only with the paired result.", "done": false}]

## Rollback

No product mutation in instrument-selection phase; revert any later protocol/test commit.

## Journal

- 2026-09-11T13:15:08Z [implementation] — Instrument audit: rejected usage_events/posttool and token_metrics.jsonl for token-delta because both stamp message usage onto tool calls and re-count cache. Candidate session_usage_metrics has authoritative-per-session contract in backend_queries_usage, but live DB rows for sessions 241 and 242 are identical (input=10948, output=5053334, total=5064282), so actual per-session attribution is unproven and cannot support a baseline. Next: trace session_metrics transcript/session resolver and determine whether the duplication is expected or a defect.
- 2026-09-11T13:20:20Z [implementation] — Debug trace confirmed a state/attribution defect: session_metrics.main parses the entire latest project transcript, then --record calls record-session without --session-id; ProjectService resolves that to the current session. The later timestamp-window resolver applies only to token_metrics.jsonl, not session_usage_metrics. Thus every SessionEnd can UPSERT a full multi-session transcript total into the current session row; the equal rows for #241/#242 are reproducible by control flow, not a valid baseline. Benchmark is blocked until this meter is repaired and regression-tested in a separate defect task.
- 2026-09-12T16:23:33Z [implementation] — AC-1 evidence, session #249/#250: the session-level source is session_usage_metrics fed by scripts/hooks/session_metrics.parse_transcript through make_session_resolver (fixed in session-rollup-window-attribution). Demonstrated against the REAL transcript 89b9d743 of this Claude session: one file split into seven windows — #243 180,730 / #244 135,941 / #245 176,220 / #246 119,638 / #247 50,592 / #248 120,869 / #249 169,024 tokens_total; sum 953,014 of 954,210, 1,196 unattributed (outside any window). Attribution LIMIT found: tokens_total = uncached input + output only; the transcript usage fields show #248 cache_read_input_tokens 129,334,844 and cache_creation 183,391 against tokens_total 120,869 — the meter is blind to context growth, which is exactly what rag-first nudges are supposed to change. Second limit: exploration tool mix in #248/#249 counted ZERO Read/Grep/Glob/search_code calls because this session explored through Bash (grep/sed/cat) — a tool-mix metric must classify Bash commands too. Deprecated per-tool counters (token_metrics.jsonl, usage_events posttool) stay rejected.
- 2026-09-12T16:24:39Z [implementation] — AC-2 ✓ docs/ru/research/rag-nudge-replay-protocol.md — §1 instrument and its two limits (uncached-only tokens_total; Bash-blind tool mix) with the real-record numbers, §2 fixed 10-prompt read-only corpus, §3 conditions A (deployed harness) / B (four injection sites removed in a git worktree, RAG server kept), §4 metric formula (primary Σ cache_creation + Σ output per window; secondary cache_read; tool mix with Bash classification; cross-check against session_usage_metrics) and the invalidity rule, §5 evidence location under docs/ru/research/_internal/rag-replay/<date>/{A,B}/ without the transcript itself, §6 no-claim rule (AC-4) and the cost of the two runs. AC-3/AC-4: NOT claimable now — the paired runs are two owner-scheduled sessions; blocking again on exactly that.
