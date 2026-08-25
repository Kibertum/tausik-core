---
slug: docs-accuracy-audit-full-framework
title: "Full framework documentation accuracy audit — 90 docs vs code"
status: done
epic: null
story: null
complexity: complex
role: qa
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
completed_at: "2026-05-15T13:19:11Z"
---

## Goal

Полный аудит docs/en/ + docs/ru/ (~90 файлов) против реальности кода. Спавним 4 параллельных агента по кластерам: (A) entry/onboarding [quickstart, workflow, adding-new-ide, upgrade, customization], (B) core concepts [architecture, senar, senar-compliance-matrix, session-active-time, agent-contract, claude-md-guide], (C) reference [cli, mcp, hooks, configuration, environment, permissions, cost-telemetry, model-providers, troubleshooting, doctor, verify-glossary, zero-defect, testing-principles, security, security-checklist, dev-doc-checks, task-archive-spec, i18n-strategy], (D) skills+brain [skills, skill-*, plan-*, roles, stacks, brain-*, memory-merge-guidelines, shared-brain, vendor-skills]. Каждый агент сравнивает claims с кодом, выдаёт structured findings. Результат — приоритизированный список defect tasks.

## Acceptance Criteria

(1) 4 параллельных агента покрывают все 90 docs кластерами A/B/C/D. (2) Каждый агент выдаёт structured findings: claim → actual → severity → file:line. (3) Findings агрегированы в один deliverable с приоритизацией. (4) Все critical/high findings конвертированы в defect tasks через .tausik task add. (5) Сами агенты — read-only, никаких правок. (6) Ошибка: агент не должен 'выдумывать' — если claim не проверить, помечать UNVERIFIABLE.

## Plan

## Rollback

## Journal

- 2026-05-15T13:19:11Z [implementation] — AC verified: (1) ✓ 4 параллельных агента (ac01953..., a901b7..., a6e01d..., a76c7...) покрыли 90 docs. (2) ✓ Structured findings (claim → actual → severity → file:line). (3) ✓ Aggregated в 8 cross-cutting themes + 58 уникальных defects (32 WRONG, 22 DRIFT, 4 UNVERIFIABLE). (4) ✓ 12 defect tasks созданы: docs-bump-v1-3-to-v1-4-headers, docs-architecture-counts-refresh, docs-hooks-rewrite, docs-cli-md-refresh, docs-mcp-md-refresh, docs-troubleshooting-purge-legacy, docs-config-doctor-reconcile, docs-plan-stacks-rewrite, docs-skill-spec-and-profiles-truth, docs-shared-brain-todos-purge, docs-environment-en-rewrite, docs-misc-defects-cleanup. (5) ✓ Агенты read-only — no edits сделаны. (6) ✓ UNVERIFIABLE отмечены явно (raven_briefing, brain_scrubbing.py location, doctor checks enumeration).
