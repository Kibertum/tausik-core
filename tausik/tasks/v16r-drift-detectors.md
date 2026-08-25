---
slug: v16r-drift-detectors
title: "[P1] Drift detectors: drift-1 (schema) + drift-7 (TC↔req provenance)"
status: done
epic: v16-renar-core
story: v16r-artefacts
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/renar_drift.py (детекторы, pure, conn-based), scripts/project_cli_drift.py + регистрация в project.py/project_parser.py, scripts/default_gates.py (2 warn-gate), scripts/gate_runner.py (dispatch), tests/test_renar_drift.py, docs/ru+en/cli.md. Синк scripts→.claude/scripts через bootstrap."
scope_exclude: "Без новых MCP tools (нет doc-count bump). Не трогать остальные 6 drift-классов. Не трогать service mixins/schema/migrations (детекторы read-only). gmcp-*/v2-*, .tausik/keys."
relevant_files:
  - "scripts/renar_drift.py"
  - "scripts/gate_runner.py"
  - "scripts/project_cli_drift.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T21:54:29Z"
---

## Goal

Реализовать 2 из 8 RENAR drift detectors (рекомендация R4 аудита): drift-1 schema-валидация артефактов, drift-7 провенанс TC↔requirement (тест без привязки к требованию = drift). AC: оба детектора как gates (warning-режим на старте); ложноположительные < разумного порога на собственной базе; docs.

## Acceptance Criteria

1) drift-1 (schema): валидирует specs+adapts по closed-lists + cross-field инвариантам (delta_n↔parent_adapt, signed↔dual-signature), которые DB CHECK не ловит. 2) drift-7 (TC↔req provenance): по task_specs ловит stale (spec.updated_at > link.created_at, task done) + deprecated-target (link на deprecated spec, task не done). 3) Оба как warn-gates на task-done + on-demand `tausik drift`. 4) FP=0 на собственной базе (артефактные таблицы пусты → детекторы молчат). 5) Negative-сценарий: тесты с синтетикой — грязные данные триггерят находки нужного kind, чистые данные → 0 находок (по каждому детектору). 6) docs: cli.md RU+EN + маппинг на RENAR §3.11 (какие 2 из 8, warning-режим). 7) tausik-reviewer на диффе clean.

## Plan

[{"step": "renar_drift.py: detect_schema_drift + detect_provenance_drift + run_all (conn-based, Finding dicts)", "done": true}, {"step": "default_gates.py: 2 warn-gates renar_drift_schema/provenance (command=None, trigger task-done)", "done": true}, {"step": "gate_runner.py: dispatch-\u0432\u0435\u0442\u043a\u0438 + run_renar_drift_gate (lazy open DB by get_db_path)", "done": true}, {"step": "project_cli_drift.py + register in project.py dispatch + project_parser.py subparser", "done": true}, {"step": "tests/test_renar_drift.py: positive(dirty triggers kind)+negative(clean\u21920) per detector", "done": true}, {"step": "docs ru+en cli.md: tausik drift + RENAR \u00a73.11 mapping", "done": true}, {"step": "sync scripts\u2192.claude/scripts (bootstrap); verify via CLI; tausik-reviewer on diff", "done": true}]

## Rollback

git revert коммита; детекторы изолированы в renar_drift.py + 2 gate-записи + CLI — удаление файла, 2 gate-записей и dispatch-веток откатывает фичу. Gates warn-only → не блокируют даже при баге. Re-bootstrap для синка .claude/scripts.

## Journal

- 2026-06-13T21:47:09Z [implementation] — Реализовано: renar_drift.py (detect_schema_drift drift-1 + detect_provenance_drift drift-7, conn-based pure, closed-lists из service_specs/adapts). 2 warn-gate в default_gates (renar_drift_schema/provenance, trigger task-done) + dispatch run_renar_drift_gate в gate_runner (lazy DB read-only, warn-only degrade). CLI tausik drift [--detector schema|provenance|all] (project_cli_drift + parser + dispatch). tests/test_renar_drift.py 14 passed (positive cross-field+enum+provenance, negative clean→0, missing-tables→[]). Bootstrap synced .claude/scripts. Smoke: CLI ok, gates ON warn, gate_runner task-done PASS обоих. Docs cli.md RU+EN §3.11 mapping. FP=0 на собственной базе (артефакты пусты).
- 2026-06-13T21:53:12Z [implementation] — AC verified: 1.✓ drift-1 валидирует specs+adapts по closed-lists+cross-field (delta↔parent, signed↔dual-sig) — tests pass. 2.✓ drift-7 stale(active spec edited after link, done) + deprecated-target — tests pass. 3.✓ оба warn-gate task-done (gate_runner PASS) + on-demand tausik drift (smoke ok). 4.✓ FP=0 на собственной базе (артефакты пусты → No drift detected). 5.✓ negative-сценарий: clean→0, empty→0, missing-tables→[], equal-ts→no-stale, deprecated-after-done→no-stale; dirty→нужный kind. 16 tests pass. 6.✓ docs cli.md RU+EN §3.11 mapping. 7.✓ tausik-reviewer: 0 critical, HIGH-1/HIGH-2 fixed, ruff clean. Verify run #735 pytest PASS exit=0 signed.
