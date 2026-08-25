---
slug: v14b-rag-nudge-replay-benchmark
title: "Замер AC8 из v14b-rag-first-nudges: расход токенов на исследование до и после rag-first подсказок"
status: planning
epic: arch-debt-post-18
story: adp18-quality-signals
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Принимает на себя критерий, отложенный при закрытии v14b-rag-first-nudges 2026-05-03: «AC 8 (replay benchmark) deferred: requires running an exploration session both before AND after the change, then diffing per-turn token burn from usage_events. Cannot be done within a single session». Критерий отложен законно — он физически требует двух сессий, — но оставался без владельца и без срока, что и обнаружила новая проверка doctor «Deferred AC». ВАЖНАЯ ОГОВОРКА, выясненная в v14b-followup-subagent-remeasure-quant (решение #201): прежний прибор для этого не годится. scripts/hooks/token_metrics.py помечен deprecated собственными словами «PostToolUse payload carried per-tool API usage. It does not — usage is message-level», и данные это подтверждают — input_tokens равен 2 у 7116 строк из 8046, а сумма cache_read даёт 568 млн для Bash за 26 сессий, потому что один кэшированный контекст пересчитывается на каждом вызове. Значит эта задача обязана начинаться с выбора прибора, а не с прогона: либо парсер транскрипта уровня сессии, либо usage_events, если он действительно несёт подушевую атрибуцию. Мерить «до и после» несуществующим прибором значит получить красивое число ни о чём — ровно та ошибка, которой в v14b уже стоила одна цепочка задач.

## Acceptance Criteria

## Plan

## Rollback

## Journal
