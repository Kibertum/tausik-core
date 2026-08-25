---
slug: v14-strategic-review-10-1-4
title: "v14 strategic review — ревью реализации 10 эпиков и плана 1.4"
status: done
epic: null
story: null
complexity: null
role: architect
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: "read-only audit: docs/, scripts/, tests/, .tausik/config.json, MEMORY.md; git log/diff анализ; делегирование Explore-агентам по эпикам"
scope_exclude: "все code edits откладываются до отдельных задач после согласования с пользователем"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T18:24:12Z"
---

## Goal

Провести комплексный ревью качества реализации десяти v14-* эпиков (brain snippets, model prompts, verify integrity, cost telemetry, project hygiene, test philosophy, doc automation, dead-code, skill store, framework lean) + бага зависания task_done; зафиксировать gaps, дать структурированное видение по каждому пункту с рекомендациями для следующей итерации.

## Acceptance Criteria

1) Для каждого из 10 v14-* эпиков (brain-snippets, model-prompts, verify-integrity, cost-telemetry, project-hygiene, test-philosophy, doc-automation, dead-code-audit, skill-store, framework-lean) зафиксированы: что реально сделано (коммиты + файлы), что осталось, риски/gaps, ссылки на тесты. 2) Для бага task_done-hang исследован research в docs/, описано фактическое поведение, риски регрессии. 3) Для auto_verify-bypass: feedback сохранён в auto-memory, проверены коммиты на наличие следов bypass в config.json, описан правильный путь решения. 4) Структурированный документ-мнение по 10 задачам с рекомендацией + tradeoff, пользователь может приоритезировать. 5) Никаких code edits в этой ревью-таске — это анализ-only; следующие задачи будут отдельными. NEGATIVE: если для эпика нет коммитов/тестов или эпик помечен done без evidence — явно отметить gap «epic done без подтверждения», а не маскировать; если task_done research в docs отсутствует — явно сказать «research не найден», не выдумывать; если попадается auto_verify=false в config.json — флагнуть как defect-кандидат.

## Plan

## Rollback

## Journal

- 2026-05-02T16:09:04Z [implementation] — Review evidence collected via 3 Explore agents. Epic 1 brain-snippets: 5/5 tasks done; code [brain_artifact_taxonomy.py:64 LOC, brain_publish_flow.py:202, brain_mcp_write.py:394]; 7+25 tests; docs EN+RU OK. Gap: no CLI propose_artifact subcommand (MCP-only), taxonomy not a Notion column. Epic 2 model-prompts: 4/4 done; code [skill_profile.py:71, model_routing.py:60]; only 5 tests. Gap: model_routing.py never called from task_next; v14-task-next-model-hint marked done but no integration; no tests for TAUSIK_MODEL_PROFILE bootstrap flow. Epic 3 verify-integrity: 3/3 done; doctor warning + verify-glossary + conftest shim. Gap: doctor auto_verify warning not surfaced in real doctor output (integration test missing); security-sensitive paths claimed but not enumerated in code. Epic 4 cost-telemetry: 5/5 done; usage_events table real (migration v23), pricing hardcoded in session_metrics.py (Claude 4.x rates), --cost command real. Gap: pricing config field exists but hooks use hardcoded; no epic/story rollup; no TTL on usage_events. Epic 5 project-hygiene: 4/4 (+1 retro bonus); spec + dry-run CLI hygiene; 9 tests. Gap: memory_compact is summary not merge; no TTL for memory types; --confirm reserved (read-only v1 only). Epic 6 test-philosophy: 3/3 done; testing-principles.md + AGENTS section (9 lines) + audit_pytest_dedupe.py (164 groups, 480 dup tests flagged). Gap: AGENTS section too brief; dedupe not in CI/hooks; KNOWN_FALSE_POSITIVES empty; 480 duplicates not consolidated. Epic 7 doc-automation: 3/3 done; gen_doc_constants.py + CI drift check wired in tests.yml:40-41; 3 tests. No major gaps. Epic 8 dead-code-audit: 3/3 done; audit_unused_python+stale_docs+orphan_files; 53 tests; real cleanups in commits db54249 + b48d230. Gap: 480 dup tests not yet consolidated. Epic 9 skill-store: 3/3 done; skill-ecosystem.md (one-pager) + vendor-skills.md (deep dive) + security callout in bootstrap. No critical gaps. Epic 10 framework-lean: 3/3 done; context_tier (minimal/standard/full) live in bootstrap_templates.py:269-323; status --compact verified. Gap: no auto-regen of bootstrap when config tier changes. Bug task_done hang: solved by Verify-First Contract — verify --task <slug> records into verification_runs table (TTL 600s), task done reads cache; 9+61 tests. Hang only possible in intentional cases (no prior verify, auto_verify=true CI legacy, security-sensitive cache miss). auto_verify bypass: current .tausik/config.json clean (gates pytest+mypy enabled, no auto_verify field). git log on config.json: no history (file is local-only / user-edited). auto_verify is a documented legacy CI escape in service_gates.py:425-620, not fraud per se. The "fraud" term applies only if framework dev silently turns it on to skip gates during local work — no such commit found in current branch.
- 2026-05-02T16:17:21Z [implementation] — AC verified: 1. ✓ Для всех 10 v14-* эпиков зафиксировано (см. docs/ru/research/tausik-1.5-strategic-review-2026-05-02.md): сводный verdict + видение + gaps + ссылки на коды/тесты. Источник фактов — 3 параллельных Explore-агента, отчёты в task_log. 2. ✓ Bug task_done hang исследован: решён через Verify-First Contract (verification_runs TTL 600s), регрессия покрыта 9+61 тестами, single gap — нет timeout-теста на симулированный виснущий pytest. 3. ✓ auto_verify-bypass: feedback сохранён как convention #71 в TAUSIK memory (cross-project запись через memory_pretool_block hook перенаправлена в проектную). HEAD .tausik/config.json чистый — gates pytest+mypy enabled, никаких auto_verify=false. История по файлу пустая (local-only). 4. ✓ Структурированный документ опубликован — docs/ru/research/tausik-1.5-strategic-review-2026-05-02.md, содержит сводный verdict, видение по 10 темам и приоритезированный backlog v1.5 (12 задач P0..P3). 5. ✓ Никаких code edits — только research-документ + memory entry + task_log записи. Все code edits отложены до отдельных v15-* задач после согласования с пользователем. NEGATIVE сценарии: - Эпики 2 (model-prompts) и 5 (project-hygiene) явно отмечены как «бумажные» с конкретными gaps, не маскируем «done». - task_done hang research найден (verify-first контракт), описан фактический механизм + остающийся gap (timeout-тест). - auto_verify=false в HEAD config не найден, но пользователю явно сказано: следов в коммите нет, поведение в прошлых сессиях возможно — convention сохранён.
