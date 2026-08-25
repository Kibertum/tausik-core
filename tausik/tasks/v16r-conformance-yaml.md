---
slug: v16r-conformance-yaml
title: "[P2] RENAR-CONFORMANCE.yaml self-assessment генератор"
status: done
epic: v16-renar-core
story: v16r-artefacts
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/renar_conformance.py (gather_signals/eval_mandatory/infer_level/build_manifest/render_yaml), scripts/project_cli_renar.py (cmd_renar → conformance subcmd) + project.py/project_parser.py reg, tests/test_renar_conformance.py, docs/ru+en/cli.md. Синк .claude/scripts через bootstrap."
scope_exclude: "Без новых MCP tools. Без записи в БД (read-only генератор; опц. --write только RENAR-CONFORMANCE.yaml в корень). Не трогать schema/migrations/service mixins. Не реализовывать остальные drift-классы. gmcp-*/v2-*, .tausik/keys."
relevant_files:
  - "scripts/renar_conformance.py"
  - "scripts/project_cli_renar.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T22:10:45Z"
---

## Goal

Команда `tausik renar conformance`: генерирует RENAR-CONFORMANCE.yaml self-assessment по уровням RENAR-1..5 на основе фактического состояния БД (есть ли reasoning traces, SPEC coverage, drift detectors). Dogfooding: kai/RENAR-CONFORMANCE.yaml застрял на RENAR-0 (аудит §0.2.3). AC: yaml генерируется и валиден против схемы renar.tech; уровень вычисляется честно из данных, не декларативно.

## Acceptance Criteria

1) `tausik renar conformance` генерирует RENAR-CONFORMANCE.yaml со ВСЕМИ mandatory-полями §14.4.2 (renar-version, manifest-version, manifest-id, level, assessment-mode/date, assessor, mandatory-clauses-confirmed, quality-gates qg0-4, substrate-capabilities v1-6, spec-types-supported 9). 2) Уровень вычисляется ЧЕСТНО из live-БД (specs/adapts/reasoning_steps/task_specs/memory_edges/verification_runs/drift-detectors), НЕ декларативно: нарушение mandatory clause → pre_adoption=true + level=null (§14.4.3, паттерн kai). 3) yaml валиден: yaml.safe_load round-trips; mandatory-поля присутствуют и нужных типов. 4) Negative-сценарий: пустая БД → pre_adoption (adapt-per-tz unmet); синтетика с adapts+specs+reasoning → клаузы поднимаются/уровень растёт. 5) Evidence-секция показывает какие сигналы met/unmet (агенту видно что нужно до RENAR-1). 6) docs cli.md RU+EN. 7) tausik-reviewer clean.

## Plan

[{"step": "renar_conformance.py: gather_signals (live-DB) + eval_mandatory_clauses + infer_level + build_manifest(\u00a714.4.2) + render_yaml", "done": true}, {"step": "project_cli_renar.py: cmd_renar conformance [--assessor --write] + reg project.py/project_parser.py", "done": true}, {"step": "tests/test_renar_conformance.py: empty\u2192pre_adoption, synthetic\u2192clauses up, mandatory-fields present, yaml round-trip", "done": true}, {"step": "docs ru+en cli.md: tausik renar conformance", "done": true}, {"step": "sync bootstrap; verify CLI; tausik-reviewer; commit", "done": true}]

## Rollback

git revert; фича изолирована в renar_conformance.py + project_cli_renar.py + 1 parser/dispatch ветка — удаление откатывает. Генератор read-only (кроме явного --write файла в корень) → нет риска для БД.

## Journal

- 2026-06-13T22:02:25Z [implementation] — Реализовано: renar_conformance.py (gather_signals из live-БД, eval_mandatory_clauses 7×§14.3 machinery/data split, infer_level §14.4.3 cumulative §12.9, build_manifest §14.4.2 все mandatory-поля, render_yaml PyYAML). CLI tausik renar conformance [--assessor --write] (project_cli_renar + parser subcmd + dispatch). На собственной базе честно: pre_adoption=true, level=null, blocked-at mandatory-clauses (adapt-per-tz unmet, 0 ADAPT). evidence-секция: raw-counts + 20 per-signal met/unmet. tests/test_renar_conformance.py 6 passed (empty→pre-adoption, 1 adapt→RENAR-1, +spec+delta→RENAR-2 blocked RENAR-3, all mandatory-fields, yaml round-trip). ruff clean, 322 lines. docs cli.md RU+EN §14.4. Bootstrap synced.
- 2026-06-13T22:10:15Z [implementation] — tausik-reviewer triaged: 2 critical + 6 high + 3 medium FIXED. tc-pos-neg-pairing category-error → vacuous-truth (§14.3.5 conditional, не gate_negative_scenario). --write: читает existing manifest-version → инкремент + atomic os.replace (§14.4.1 immutability, не reset-to-1). tz_immutable → adapts_signed (draft≠immutable §12.5.1). next-assessment-due = date+90d. manifest-id date-granular (V1 non-reuse). lifecycle_statuses_used → specs status!=draft (не tautology). RENAR-4 += continuous_reconciliation signal. knowledge_graph_primary → honest False. delta_tz non-superseded. SPEC_TYPES из service_specs (single source). _scalar warn stderr. level-target → next level. Отклонено: qg-1 required (фиксировано §14.4.3), verifs-in-raw (уже было). Тесты 9 passed (draft→RENAR-1, signed+spec+delta→RENAR-2, next-due, level-target, determinism×2). Регрессия 92 passed.
- 2026-06-13T22:10:43Z [implementation] — AC verified: 1.✓ все mandatory-поля §14.4.2 (test_all_mandatory_fields_present). 2.✓ уровень из live-БД, не декларативно: empty→pre_adoption blocked-at mandatory-clauses (test_empty_db_is_pre_adoption); adapt→RENAR-1; signed+spec+delta→RENAR-2. 3.✓ yaml валиден round-trip (test_yaml_round_trips safe_load==manifest). 4.✓ negative: empty→pre_adoption, синтетика поднимает клаузы/уровень. 5.✓ evidence-секция met/unmet+blocked-at+raw-counts. 6.✓ docs cli.md RU+EN §14.4. 7.✓ tausik-reviewer 2crit+6high FIXED, ruff clean. verify run #738 pytest PASS exit=0 signed.
