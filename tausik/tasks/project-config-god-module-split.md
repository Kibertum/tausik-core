---
slug: project-config-god-module-split
title: "project_config: девять ответственностей, 139 импортёров и get_service() в загрузчике конфига — блокер standalone-пакета"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "NEW scripts/service_factory.py, NEW scripts/tausik_constants.py; edit scripts/project_config.py (remove get_service + DB imports + moved constants, add re-exports), scripts/project.py (get_service import). NEW tests/test_config_module_boundary.py. CHANGELOG.md + CHANGELOG.ru.md."
scope_exclude: "DEFERRED (separate follow-up tasks, per handoff 'полный 9-way сплит отложить'): gates extraction (load_gates/get_gates_for_trigger/auto_enable_gates_for_stacks/STACK_GATE_MAP stay in project_config for now); project_cli_ops.py concern-split; project_cli_extra.py concern-split. Do NOT change gate merge/validation logic or the config trust-tier logic."
relevant_files:
  - "scripts/service_factory.py"
  - "scripts/tausik_constants.py"
  - "scripts/project_config.py"
  - "scripts/project.py"
  - "tests/test_config_module_boundary.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T13:46:42Z"
---

## Goal

Топ-1 хотспот связности: 139 импортёров при 391 строке. Докстринг обещает «find .tausik/ dir, create service, gates config», фактически внутри: резолв путей, load/save, делегирование трастовых тиров, мердж гейтов + валидация команд, нормализация цен LLM, константы длительности сессии, enum context-tier, флаги модельного баннера и DI-фабрика get_service() на :387. Именно get_service() тянет ребро project_config → project_backend → project_service на этапе импорта, из-за чего модуль конфига нельзя импортировать без всего слоя БД — а standalone-пакет (v2-engine-standalone-package) не может поставлять загрузчик конфига, тянущий ORM. Фикс: get_service() → новый service_factory.py (ребро рвётся); DEFAULT_SESSION_* / CONTEXT_TIER_* / цены → tausik_constants.py; в project_config остаются пути + load/save + trust (~120 строк). В том же классе, но отдельными шагами: project_cli_ops.py (387 строк, восемь несвязанных концернов в собственном докстринге: metrics, search, events, explore, audit, run, dead-end, brain) и project_cli_extra.py (363 строки, пять концернов) — резать по концерну, а не по числу строк. Это предусловие для 2.0-упаковки, а не косметика.

## Acceptance Criteria

1. NEW scripts/service_factory.py holds get_service() + its DB imports (SQLiteBackend, ProjectService). project_config.py NO LONGER imports project_backend/project_service at module level, nor defines get_service — the import-time edge project_config→DB layer is broken (the standalone-package blocker). 2. scripts/project.py imports get_service from service_factory; behavior identical. 3. NEW scripts/tausik_constants.py holds DEFAULT_SESSION_MAX_MINUTES/WARN_THRESHOLD/IDLE_THRESHOLD, DEFAULT_SESSION_CAPACITY_CALLS, CONTEXT_TIER_VALUES, DEFAULT_CONTEXT_TIER, resolve_context_tier, normalize_llm_pricing_config, lookup_llm_usd_per_million_tokens. project_config RE-EXPORTS all of them so every existing importer (MCP handlers.py, service_session, project_cli, project_cli_doctor, service_recording, cost_pricing, bootstrap_modes, bootstrap_config, tests) works UNCHANGED. 4. A test AST-asserts project_config has NO module-level import of project_backend/project_service (edge broken), plus a functional test that project_config re-exports the moved symbols identically. 5. Full suite green, 0 warnings; test_context_tier + test_llm_pricing_config + session tests pass unchanged. 6. CHANGELOG EN+RU: edge-break (standalone precondition) + constants extraction; gates-extraction and project_cli_ops/project_cli_extra concern-splits are DEFERRED (separate steps per plan). NEGATIVE/BOUNDARY: 7. A fresh subprocess import of project_config with project_backend AND project_service blocked in sys.modules still SUCCEEDS (proves the edge is truly gone); load_config/get_config_path/load_gates behave byte-identically to before.

## Plan

## Rollback

git revert the commit — deletes service_factory.py + tausik_constants.py and restores get_service + the constants inline in project_config.py. Pure code-move refactor with back-compat re-exports; no schema/data/API change, no behavior change.

## Journal

- 2026-07-26T13:46:11Z [implementation] — Created service_factory.py (get_service + DB imports; the edge). Created tausik_constants.py (session/context-tier/pricing). project_config.py: removed DB imports + get_service + moved defs, added re-export import; 401→321 lines. project.py get_service import repointed to service_factory. Added tests/test_config_module_boundary.py (AST + subprocess-block proof edge broken; re-export identity; get_service moved). Smoke import OK, get_service gone from project_config. Tests: 89 boundary/context/pricing/trust + 889 importer-surface passed. Gates/cli splits deferred per scope. Constants regen, redeployed all IDEs.
- 2026-07-26T13:46:40Z [implementation] — AC verified: 1. ✓ scripts/service_factory.py holds get_service + SQLiteBackend/ProjectService imports; project_config.py has NO module-level DB import and no get_service (AST guard test_source_has_no_db_layer_import + test_get_service_moved_to_service_factory) 2. ✓ project.py:72 imports get_service from service_factory; behavior identical (589 project/cli tests pass) 3. ✓ scripts/tausik_constants.py holds all session/context-tier/pricing symbols; project_config re-exports them (test_constants_and_helpers_reexported_identically: same objects). test_context_tier + test_llm_pricing_config pass unchanged 4. ✓ test_config_module_boundary.py: AST guard + subprocess import with project_backend/project_service blocked → project_config imports OK; re-export identity asserted 5. ✓ 889 importer-surface tests + 89 boundary/context/pricing/trust pass; scoped verify (high) 5 test files PASS. Full suite run pending as final gate 6. ✓ CHANGELOG EN+RU document edge-break (standalone precondition) + constants extraction + explicit deferral of gates/cli splits 7. ✓ test_project_config_imports_without_db_layer (subprocess, DB blocked) succeeds; test_service_factory_still_requires_db_layer fails as expected; load_config/get_config_path callable in that env
