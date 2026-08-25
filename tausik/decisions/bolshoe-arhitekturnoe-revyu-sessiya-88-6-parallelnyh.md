---
slug: bolshoe-arhitekturnoe-revyu-sessiya-88-6-parallelnyh
task: null
date: "2026-06-13"
edges: []
---

## Decision

Большое архитектурное ревью (сессия #88, 6 параллельных агентов): ядро TAUSIK здорово и conformant, но есть конкретный quality-debt — 3 нарушения filesize (backend_queries 461, project_parser 409, project_service 401), дублирование констант (TTL 600 ×3, SPEC_TYPES/ADAPT_STATUSES ×3, task-status литералы), hardcoded identity 'architect-andrey-y', и масштабный doc-count drift (MCP tools: docs говорят 93/98/100/105, факт 123; schema v27 vs v37; CLI-команды spec/adapt/key/receipt не задокументированы).

## Rationale

Verify-First, QG-0/QG-2, Rule 9.2/9.5 реально enforced в коде (подтверждено code-path аудитом). Filesize-gate пропустил 3 нарушения т.к. сканирует только changed files задачи, а не весь репозиторий — латентные нарушения невидимы. Doc-drift gate (CROSS_FILE_SCAN_TARGETS, 8 sites) не покрывает stale-цифры в agent-contract/architecture/compliance-matrix — это agent-facing ложь (агент читает доки как authoritative). tausik_systemwide_analysis.md — внешний Kilo-артефакт, не наш, не удаляю (не я создавал). Продуктовый дрейф (snippets/ADAPT off-axis) и три-зеркальный MCP-tax уже адресованы эпиками gmcp-*/v2-*. Приоритет фиксов: rule-violations (filesize) + agent-facing errors (doc drift, hardcode identity) → single-source-of-truth дедуп → test-hardening (v34/postseed hash-chain backfill не покрыт).
