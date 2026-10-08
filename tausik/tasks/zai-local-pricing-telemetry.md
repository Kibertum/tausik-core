---
slug: zai-local-pricing-telemetry
title: "Телеметрия: прайсы z.ai и локальных, живой GLM-замер"
status: done
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Pricing classification for native usage reports and the token_price report path: measured/free(0.0)/unknown for z.ai and local models; bridge llm_pricing_usd_per_million into token_price; config declaration in this project; live GLM measurement via metrics usage --host kilo"
scope_exclude: "usage_codex_report pricing wiring (separate later task); benchmark_cohorts; DB write path semantics (cost_pricing.calculate_cost_usd stays as is); task attribution anywhere (stays unknown)"
relevant_files:
  - "scripts/usage_pricing.py"
  - "scripts/token_price.py"
  - "scripts/usage_kilo.py"
  - "tests/test_usage_pricing.py"
  - "tests/test_usage_kilo.py"
  - "tests/test_token_price.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/token_price.py"
  - "scripts/usage_kilo.py"
  - "scripts/usage_pricing.py"
  - "tests/test_token_price.py"
  - "tests/test_usage_pricing.py"
  - ".tausik/config.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - kilo-mcp-live-wiring
completed_at: "2026-10-06T20:10:42Z"
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

[{"step": "Take the live kilo usage measurement first and record it as AC3 evidence (or document why it is impossible)", "done": true}, {"step": "Bridge llm_pricing_usd_per_million into token_price.builtin_rates so one declaration prices both DB writes and the report", "done": true}, {"step": "New usage_pricing module: classify native report observations into priced/free/unknown per model, warn once for unknown, never print 0.00 for unknown", "done": true}, {"step": "Wire the pricing section into usage_kilo.report with real pricing_applied; task_attribution stays unknown", "done": true}, {"step": "Declare local-model prices 0.0 and leave zai-coding-plan undeclared in this project's .tausik/config.json", "done": true}, {"step": "Tests: parametrized priced/free/unknown + config bridge in test_token_price and new test_usage_pricing", "done": true}, {"step": "Docs check + CHANGELOG en/ru under Unreleased, then verify --task and task done", "done": true}]

## Rollback

Revert the new module and the two call-site wiring diffs via git checkout of changed files; config.json pricing keys are removable lines; native report shape is additive (new 'pricing' key), consumers unaffected when removed; no DB schema or migration involved

## Journal

- 2026-10-06T19:36:26Z [implementation] — AC3 live GLM measurement, run via 'metrics tokens --host kilo' (source kilo.db, mode=ro): source_available=true, reliable_totals=true, coverage sessions=3 rows_read=568 malformed=0. 569 responses (568 completed, 1 failed), glm_responses=569. tokens: input=62213578 (cached_input=60458560, cache_write=0), output=323597, reasoning_output=164889. providers=[kilo, zai-coding-plan], models=[glm-4.7, ~z-ai/glm-flash-latest], host_versions=[7.8.1, 7.8.3]. task_attribution=unknown in source (AC4: kept, not invented). pricing_applied=false — the gap this task closes. Config declaration note (AC1): the observed model ids are 'glm-4.7' and '~z-ai/glm-flash-latest' (NOT zai-coding-plan/glm-4.7); provider carries the plan name. Prices are declared per model id as observed.
- 2026-10-06T20:09:50Z [implementation] — AC verified: 1. ✓ pricing section classifies every model as priced/free/unknown — tests/test_usage_pricing.py 146 passed incl. parametrized priced/free matrix, unknown-is-named-never-zero, unmeasured-null 2. ✓ negative: unknown models with billable tokens are warned once and never priced 0.00 — test_unknown_is_named_and_never_zero + live kilo report shows glm-4.7 unknown, usd null, warning 132618149 tokens stay unpriced 3. ✓ live measurement logged (task_log AC3: 569 responses, input 62213578 cached 60458560, output 323597, reasoning 164889, hosts 7.8.1/7.8.3) 4. ✓ task_attribution stays unknown — usage_kilo keeps the hard-coded unknown; test_usage_kilo pin line 109 green (16 passed).
- 2026-10-06T20:10:36Z [implementation] — step 1 complete
- 2026-10-06T20:10:36Z [implementation] — step 2 complete
- 2026-10-06T20:10:36Z [implementation] — step 3 complete
- 2026-10-06T20:10:37Z [implementation] — step 4 complete
- 2026-10-06T20:10:37Z [implementation] — step 5 complete
- 2026-10-06T20:10:37Z [implementation] — step 6 complete
- 2026-10-06T20:10:37Z [implementation] — step 7 complete
- 2026-10-06T20:11:02Z [done] — AC-2: ✓ tests/test_usage_pricing.py::TestThePairKeyPricesTheReportPath + test_unknown_is_named_and_never_zero — negative proven: billable unknown is warned once, usd stays null, applied stays false. AC-4: ✓ tests/test_usage_kilo.py (16 passed) pins task_attribution unknown at line 109; usage_kilo never upgrades it. Domain: live kilo report on this machine prints glm-4.7 unknown with a 132618149-token warning, no 0.00 anywhere.
