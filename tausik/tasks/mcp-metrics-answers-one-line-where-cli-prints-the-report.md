---
slug: mcp-metrics-answers-one-line-where-cli-prints-the-report
title: "tausik_metrics отдаёт ОДНУ строку там, где CLI печатает весь отчёт SENAR: агент судит о проекте по сводке"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
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

MCP-обработчик метрик возвращает «Tasks: N/M (x%), Sessions: ...» — одну строку. CLI печатает throughput, lead time, FPSR, DER, cycle time, knowledge capture rate, dead end rate, стоимость по сложности и риск-секцию. CLAUDE.md велит агенту предпочитать MCP, то есть основной читатель метрик видит наименьшую их часть. Схлопнуть в один рендерер: cmd_metrics печатает построчно через project_cli_metrics.render_extended_metrics и risk_metrics.format_risk_section, поэтому нужна конверсия печати в список строк, а не перенос текста. Заведено из one-implementation-per-command-mcp-over-cli: там снят инвентарь (17 вторых реализаций, 13 схлопнуто), эта осталась как объявленный остаток, а не как незамеченная.

## Acceptance Criteria

## Plan

## Rollback

## Journal
