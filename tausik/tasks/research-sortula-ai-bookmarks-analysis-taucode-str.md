---
slug: research-sortula-ai-bookmarks-analysis-taucode-str
title: "Research: Sortula AI bookmarks analysis + TauCode strategy"
status: done
epic: null
story: null
complexity: null
role: architect
stack: python
tier: substantial
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/research/2026-06-12-sortula-ai-bookmarks-taucode-strategy.md"
scope_paths: []
scope_tools: []
completed_at: "2026-06-11T22:54:01Z"
---

## Goal

Two-part research: (1) analyze AI-related bookmarks of andrey.jumashev@gmail.com in Sortula (staging/prod) and derive TAUSIK improvement ideas; (2) propose evolution path for TAUSIK — TauCode (OpenCode-like CLI) vs VS Code extension. Deliverable: md report in docs/ + summary in chat. AC: report covers both tasks with concrete actionable recommendations.

## Acceptance Criteria

1) AI-related bookmarks of andrey.jumashev@gmail.com pulled from Sortula prod (read-only SQL), categorized and analyzed. 2) Report md file written in docs/ with: bookmark insights mapped to concrete TAUSIK improvements, and TauCode-vs-VSCode-extension strategy with recommendation. 3) Summary delivered in chat. Negative scenario: if prod access fails, fall back to staging; if both fail, document blocker and analyze via local dev DB or API.

## Plan

## Rollback

## Journal

- 2026-06-11T22:45:54Z [implementation] — Prod access via memory #12 (root@172.50.0.19). User id abf1335d. 331 bookmarks total, 129 AI/ML by category; exported 169 AI-related (category OR tags regex) to d:/tmp/sortula_ai_bookmarks.jsonl
- 2026-06-11T22:47:25Z [implementation] — Context gathered: memory #24 (bug classification: MCP 33%, bootstrap 25%, Windows 25%), audit-report-2026-05-18 (top-5 risks, positioning, 24-mo roadmap). Two background agents running: (1) bookmark digest from jsonl, (2) TauCode landscape web research (OpenCode/Agent SDK/VS Code ext/Cline/Spec Kit).
- 2026-06-11T22:50:59Z [implementation] — Landscape research done: (A) OpenCode plugin route 2-4wk MVP (tool.execute.before hard gates, no fork), (B) Agent SDK PreToolUse deny/updatedInput 4-8wk MVP but Anthropic lock-in, (C) VS Code ext worst ROI (Roo Code died 2026-05-15, Copilot policy dependency). Recommended: enforcement-adapters strategy, one policy core + 3 thin adapters. Awaiting bookmark digest agent.
- 2026-06-11T22:53:41Z [implementation] — Report written: docs/research/2026-06-12-sortula-ai-bookmarks-taucode-strategy.md. Part 1: 15 clusters, 6 obsessions, 10 TAUSIK improvements (T1 self-correcting CLI, T2 escalating nudges, T3 tausik tune, T4 dep-graph RAG, T5 memory lint, T6 deny-by-default, T7 judge pipeline, T8 domain challenge, T9 cq, T10 AGENTS.md). Part 2: enforcement-adapters strategy, 4 phases (fix Claude Code hooks → OpenCode plugin TauCode Q3 → Agent SDK headless Q4 → VS Code dashboard panel Q1'27).
- 2026-06-11T22:54:01Z [implementation] — AC verified: 1. ✓ 169 AI bookmarks pulled from prod (root@172.50.0.19, read-only COPY TO STDOUT → d:/tmp/sortula_ai_bookmarks.jsonl), categorized into 15 clusters via subagent digest. 2. ✓ Report at docs/research/2026-06-12-sortula-ai-bookmarks-taucode-strategy.md: 10 concrete TAUSIK improvements (T1-T10) mapped to bookmark sources + TauCode strategy (enforcement-adapters, 4 phases) with web-verified landscape data. 3. ✓ Summary delivered in chat. Negative scenario not triggered — prod access worked first try.
