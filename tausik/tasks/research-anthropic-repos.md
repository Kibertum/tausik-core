---
slug: research-anthropic-repos
title: "Research github.com/anthropics репозиториев → идеи для TAUSIK"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "references/anthropic-oss-applicability.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:58:20Z"
---

## Goal

Изучить публичные репозитории Anthropic (github.com/anthropics), выявить паттерны/инструменты/идеи, применимые к TAUSIK: prompt caching, tool use, Claude Agent SDK, hooks, MCP примеры, skills ecosystem. Сформировать список конкретных improvement-задач с приоритетами.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T10:50:13Z [planning] — Research done via claude-code-guide subagent (web search + WebFetch). Surveyed 7 most-relevant Anthropic OSS repos (knowledge-work-plugins, anthropic-cli, agent-sdk-workshop, original_performance_takehome, skills, claude-code-action, financial-services-plugins). Identified 9 applicable patterns ranked by complexity (5 simple, 3 medium, 1 complex). Top 3 conversion candidates с proposed slugs: tausik-skill-manifest (skill.yaml registry + CLI filter), tausik-metrics-tiers (bronze/silver/gold/platinum tiers from cycle-counting eval pattern), tausik-brain-swappable-backend (decouple brain MCP from Notion для swappable connectors). Полный отчёт saved в references/anthropic-oss-applicability.md (~1300 words с цитатами URL'ов). Не applicable: closed-domain repos (compiler/buffa/connect-rust), non-agent orchestration.
