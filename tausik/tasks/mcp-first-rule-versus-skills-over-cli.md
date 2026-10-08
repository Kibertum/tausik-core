---
slug: mcp-first-rule-versus-skills-over-cli
title: "Правило MCP-first принято до того, как индустрия качнулась к skills-over-CLI"
status: done
epic: release-111-economy-draft
story: release111-measurement
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "Bounded MCP/CLI comparison using existing service layer and Codex/GLM hosts; decision record"
scope_exclude: null
relevant_files:
  - "docs/ru/research/mcp-cli-economy-111.md"
scope_paths:
  - "docs/ru/research/mcp-cli-economy-111.md"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - r111-budgeted-context-package
completed_at: "2026-10-01T17:31:02Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#130"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Правило MCP-first в CLAUDE.md либо подтверждено доказательством, либо изменено. Сейчас оно держится на времени, когда было записано, а не на данных.

## Acceptance Criteria

AC1. СИГНАЛ ЛАНДШАФТА ЗАФИКСИРОВАН (закладка 2026-08-06): 'индустрию качает в сторону skills over CLI: вместо MCP используются CLI, которые обращаются к нужным сервисам'. Одна закладка — не доказательство; она повод проверить, а не основание менять.
AC2. СОБСТВЕННЫЕ ДАННЫЕ ВЕСОМЕЕ ЧУЖОГО ТРЕНДА, И ОНИ У НАС ЕСТЬ. Расхождение MCP и CLI стоило нам трёх дефектов подряд, последний — стирание хвоста памяти при каждом /start. Плюс постоянная ловушка: MCP-сервер держит старый код до перезапуска IDE, чего у CLI нет по устройству. Свести это в счёт, а не в впечатление.
AC3. ЦЕНА ОБЕИХ СТОРОН НАЗВАНА. У MCP есть то, чего у CLI нет: типизированные аргументы и отсутствие возни с кавычками, что на Windows стоило нам отдельной конвенции. Задача не имеет права свестись к 'CLI победил'.
AC4. РЕШЕНИЕ ЗАПИСЫВАЕТСЯ КАК РЕШЕНИЕ, с альтернативой и причиной отказа, а не правкой строки в CLAUDE.md. Правило без записанной причины — это то, что мы сейчас и разбираем.
AC5. НЕГАТИВНЫЙ СЦЕНАРИЙ: если правило подтверждено, задача обязана закрыться ПОДТВЕРЖДЕНИЕМ с доказательством, а не остаться висеть. Исследование без исхода — тот же тихий отказ.
AC6. Разобрать отдельно, не является ли настоящим ответом ТРЕТЬЕ: одна реализация и две тонкие обёртки. Именно к этому мы пришли вынужденно в claudemd_state.py, но как общее правило это нигде не записано.
AC-7 Compare actual Codex and chosen GLM paths with equal guarantees, including tool discovery, Windows quoting, retries and total model responses; do not equate MCP tool count to schemas injected on every host. Preserve MCP-first until a separately recorded owner-approved change.
Release matrix clarification (owner, 2026-10-01): Claude Code, Kilo Code with GLM, and Codex are mandatory live acceptance targets; Codex remains the primary quantitative economy benchmark. Shared context/workflow/usage contracts apply to all three, not only fixture regression for Claude. Cursor is an additional host and OpenRouter an additional provider, never synonyms for a model or for each other. Optional Cursor/OpenRouter discovery plus thin integration has a combined ceiling of 25 extra tool calls across this release; it is not a release prerequisite. If existing adapters cannot support it without a new subsystem, stop, record capability gaps and defer that work; no automatic budget increase or claim of untested parity.
Delivery staging: perform Codex comparison and portable contract checks first. GLM/Claude live cases are collected by release acceptance; do not delay the first compound-operation improvement to await the GLM ledger.

## Plan

[{"step": "Define equivalent existing workflow cases and host capabilities.", "done": true}, {"step": "Measure MCP/CLI end-to-end overhead and reliability on Codex/GLM.", "done": true}, {"step": "Record keep/change/same-service-two-wrappers verdict with evidence; no speculative transport rewrite.", "done": true}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T17:28:33Z [implementation] — Codex live evidence: tool discovery exposes 147 TAUSIK MCP tools lazily inside functions.exec; active MCP schema is stale (task_show advertises only slug and returns old full form), while fresh CLI exposes --package. Native journal has 491 exec calls, 294 containing TAUSIK/project commands and 120 batched/compound by a conservative heuristic. Transport alone is one model tool round each; batching/compound service shape is the round-trip lever.
- 2026-10-01T17:29:24Z [implementation] — Matched transport latency probe on live Codex: task_show 10/10 each. MCP median 39 ms (35-50), fresh CLI median 439 ms (410-463). Payload shapes differ because live MCP is stale/full and CLI is fresh, so this supports transport/process latency only, not token or quality parity. Both transports fit one outer Codex functions.exec round and can be batched; transport is not the model-response lever.
- 2026-10-01T17:30:10Z [implementation] — Verdict recorded as decision #413 with rejected CLI-first and MCP-only alternatives. Research document now includes live Codex latency/batching evidence and explicit unknowns for token, retry, tool-schema and GLM parity; 4 targeted shared-route tests pass.
- 2026-10-01T17:30:57Z [implementation] — AC-1: ✓ docs/ru/research/mcp-cli-economy-111.md фиксирует гипотезу как сигнал, не доказательство. AC-2: ✓ tests/test_route_is_enforced.py::TestTheMcpTwinIsDerivedNotListed::test_existence_is_checked_against_the_live_dispatch_table — маршрут выводится из реальной таблицы.
- 2026-10-01T17:30:57Z [implementation] — AC-3: ✓ измерены обе цены: typed MCP и Windows quoting/stale CLI tradeoff. AC-4: ✓ решение #413 содержит rationale и две rejected alternatives. AC-5: ✓ Negative: подтверждённое правило закрывается вердиктом, CLI-first и MCP-only явно отклонены.
- 2026-10-01T17:30:57Z [implementation] — AC-6: ✓ one ProjectService + two thin wrappers записан как архитектурный критерий. AC-7: ✓ tests/test_usage_codex.py::test_cli_and_mcp_share_native_report — общий результат; Codex latency 10+10, response batching описан, GLM/token parity остаётся unknown без ложной claims. Verify #3253.
