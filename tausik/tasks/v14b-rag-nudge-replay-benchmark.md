---
slug: v14b-rag-nudge-replay-benchmark
title: "Замер AC8 из v14b-rag-first-nudges: расход токенов на исследование до и после rag-first подсказок"
status: blocked
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "Read-only investigation of token/usage/transcript instrumentation, protocol documentation and focused tests only; no change to RAG behavior in the baseline phase."
scope_exclude: "Do not use deprecated per-tool PostToolUse counters as session usage; do not claim savings from one session; do not alter RAG behavior, release, tag or push."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Принимает на себя критерий, отложенный при закрытии v14b-rag-first-nudges 2026-05-03: «AC 8 (replay benchmark) deferred: requires running an exploration session both before AND after the change, then diffing per-turn token burn from usage_events. Cannot be done within a single session». Критерий отложен законно — он физически требует двух сессий, — но оставался без владельца и без срока, что и обнаружила новая проверка doctor «Deferred AC». ВАЖНАЯ ОГОВОРКА, выясненная в v14b-followup-subagent-remeasure-quant (решение #201): прежний прибор для этого не годится. scripts/hooks/token_metrics.py помечен deprecated собственными словами «PostToolUse payload carried per-tool API usage. It does not — usage is message-level», и данные это подтверждают — input_tokens равен 2 у 7116 строк из 8046, а сумма cache_read даёт 568 млн для Bash за 26 сессий, потому что один кэшированный контекст пересчитывается на каждом вызове. Значит эта задача обязана начинаться с выбора прибора, а не с прогона: либо парсер транскрипта уровня сессии, либо usage_events, если он действительно несёт подушевую атрибуцию. Мерить «до и после» несуществующим прибором значит получить красивое число ни о чём — ровно та ошибка, которой в v14b уже стоила одна цепочка задач.

## Acceptance Criteria

AC-1: approved session-level source and its attribution limits are demonstrated against real records; deprecated per-tool metrics are rejected. AC-2: replay protocol fixes query corpus, baseline/post condition, metric formula and raw evidence location. AC-3: paired sessions use the same protocol; result reports both absolute tokens and delta, or explicitly records why comparison is invalid. AC-4: no token-saving claim is made without paired attributable evidence.

## Plan

[{"step": "Inventory candidate session-level token sources and reject known per-tool misattribution.", "done": true}, {"step": "Define a reproducible before/after replay protocol with a stable query corpus and attribution boundary.", "done": false}, {"step": "Run the first baseline session and preserve raw evidence without claiming an effect.", "done": false}, {"step": "Run the post-change session in a later session, compare the same metrics, and close only with the paired result.", "done": false}]

## Rollback

No product mutation in instrument-selection phase; revert any later protocol/test commit.

## Journal

- 2026-09-11T13:15:08Z [implementation] — Instrument audit: rejected usage_events/posttool and token_metrics.jsonl for token-delta because both stamp message usage onto tool calls and re-count cache. Candidate session_usage_metrics has authoritative-per-session contract in backend_queries_usage, but live DB rows for sessions 241 and 242 are identical (input=10948, output=5053334, total=5064282), so actual per-session attribution is unproven and cannot support a baseline. Next: trace session_metrics transcript/session resolver and determine whether the duplication is expected or a defect.
- 2026-09-11T13:20:20Z [implementation] — Debug trace confirmed a state/attribution defect: session_metrics.main parses the entire latest project transcript, then --record calls record-session without --session-id; ProjectService resolves that to the current session. The later timestamp-window resolver applies only to token_metrics.jsonl, not session_usage_metrics. Thus every SessionEnd can UPSERT a full multi-session transcript total into the current session row; the equal rows for #241/#242 are reproducible by control flow, not a valid baseline. Benchmark is blocked until this meter is repaired and regression-tested in a separate defect task.
