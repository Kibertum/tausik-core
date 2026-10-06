---
slug: zai-local-pricing-telemetry
title: "Телеметрия: прайсы z.ai и локальных, живой GLM-замер"
status: planning
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - kilo-mcp-live-wiring
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

GLM smoke в 1.11 упал с HTTP 402 — live-паритет не подтверждён; прайса zai-coding-plan/* нет, локальные модели не имеют явного 0.0. Задекларировать прайсы через llm_pricing_usd_per_million (config выигрывает), снять живой GLM-замер через metrics tokens --host kilo при рабочей подписке, отделить measured/unknown/free в отчётах.

## Acceptance Criteria

1) metrics различает measured, unknown и free (0.0) для z.ai и локальных моделей. 2) Негативный: незадекларированный провайдер даёт unknown + warning, никогда не .00. 3) Живой GLM-замер записан в evidence с версиями Kilo/провайдера/модели (или задокументирована причина невозможности). 4) Attribution по задачам остаётся unknown там, где источник его не отдаёт — без выдумывания.

## Plan

## Rollback

## Journal
