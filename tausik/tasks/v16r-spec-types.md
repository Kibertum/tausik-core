---
slug: v16r-spec-types
title: "[P1] SPEC-артефакты: 9 closed types (ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS)"
status: done
epic: v16-renar-core
story: v16r-artefacts
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "migration v35 (backend_migrations.py + backend_schema.py baseline + SCHEMA_VERSION→35): specs table (slug,type CHECK closed-9,title,content_ref,version,status,created_at,updated_at) + task_specs link (task_slug,spec_slug,relation='implements') + fts_specs FTS5 + triggers + indexes. New: backend_crud_specs.py (SpecsCrudMixin), service_specs.py (SpecsMixin), project_cli_specs.py (cmd_spec add/list/show/link/search), project_parser_specs.py. Wire: project_backend.py, project_service.py, project.py dispatch, project_parser.py. MCP: tools.py (tausik_spec_* schemas) + handlers.py (lambdas). task_show: service_task.task_show adds linked specs; project_cli_task.py displays them. gen_doc_constants.py + README test-count regen."
scope_exclude: "gmcp-*/v2-* (2.0), .tausik/keys, events/* chain code, brain_*, existing migration bodies v1-v34. Do NOT edit .claude/ generated copies directly (edit harness/ + root sources)."
relevant_files:
  - "scripts/service_specs.py"
  - "scripts/backend_crud_specs.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v35.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_specs.py"
  - "scripts/backend_init.py"
  - "scripts/project_backend.py"
  - "scripts/project_service.py"
  - "scripts/service_task.py"
  - "scripts/project_cli_specs.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_specs.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "tests/test_specs.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T20:57:54Z"
---

## Goal

Поддержка RENAR SPEC types в TAUSIK: таблица specs (type из closed list 9, title, content-ref, version), связь task↔spec (task реализует SPEC). Сверить с актуальной renar.tech v1.0-draft (31.05.2026) на этапе старта — версия свежее аудита. AC: CRUD через CLI/MCP; closed list enforced; task show показывает связанные SPEC; FTS5 поиск.

## Acceptance Criteria

1. CRUD via CLI: `tausik spec add <slug> <TYPE> <title> --version --content-ref`, `spec list`, `spec show`, `spec link <task> <spec>`, `spec search` all work. 2. CRUD via MCP: tausik_spec_add/list/show/link handlers callable. 3. Closed-list enforced at BOTH layers — service rejects invalid type with friendly error AND DB CHECK constraint raises IntegrityError (negative: `spec add x FOO t` fails; linking task to nonexistent spec errors, not silent). 4. `task show` displays linked SPEC(s). 5. FTS5 search finds spec by title/content. 6. Full pytest green + new tests for spec CRUD + closed-list rejection; schema/test-count docs regenerated (check_docs hook green).

## Plan

## Rollback

git revert the feature commit. Migration v35 is purely additive (new tables only, no ALTER on existing) → dropping specs/task_specs/fts_specs tables fully reverses schema; SCHEMA_VERSION revert to 34. No data loss to existing tables.

## Journal

- 2026-06-13T20:21:02Z [planning] — QG-0 PREP (renar.tech v1.0-draft, сверка 2026-06-13): closed set из 9 типов ПОДТВЕРЖДЁН без дрейфа — ARCH/API/DATA/INT/PROC/UI/AI/SEC/OPS. 'New type — only поправкой стандарта' → CHECK-constraint closed list. SPEC-типы = параллельная ось через constrained-by[] (task реализует/ограничен SPEC). Field requirements детально не в excerpt — required: type(closed), title, version, content-ref. План скоупа: migration v35 (specs + fts_specs + triggers + task_specs link 'implements'); backend_crud_specs.py mixin; service методы; project_cli_specs.py (spec add/list/show/link); MCP handlers_spec; task_show показывает linked SPEC; FTS5. Complex/architect — заслуживает свежей сессии под полный review.
- 2026-06-13T20:36:48Z [implementation] — Implementation done: migration v35 (specs + task_specs + fts_specs + triggers + indexes) in backend_migrations.py + baseline backend_schema.py (SCHEMA_VERSION→35); backend_crud_specs.py (SpecsCrudMixin) wired into SQLiteBackend; service_specs.py (SpecsMixin, SPEC_TYPES closed-9 + SPEC_RELATIONS + SPEC_STATUSES) wired into ProjectService; task_show adds task['specs']; project_cli_task.py displays linked SPECs; project_cli_specs.py + project_parser_specs.py (cmd spec add/list/show/update/delete/link/unlink/search) wired into project.py dispatch + project_parser.py. MCP: harness tools_spec.py + handlers_spec.py merged into _DISPATCH/TOOLS. Next: tests + verify.
- 2026-06-13T20:53:27Z [implementation] — tausik-reviewer (adversarial, 22 files, 0 critical/3 high/6 medium/5 low). Fixing real issues: (H1) validate_slug raises ValueError not ServiceError → wraps it in spec_add so CLI/MCP ServiceError catch handles it (no raw traceback); (H2) spec_search passes raw query to FTS5 MATCH → malformed query raised uncaught sqlite3.OperationalError → wrap→ServiceError; (H3) fts_specs missing from backend_init rebuild loop → add (invariant + future-proof, harmless on empty migrated table); (M) add validate_length for title/version in add+update; cap search limit at 200; reorder validate_content before existence check; add FTS-after-delete test. Skipping: content_ref-clear (documented no-op semantics), index asymmetry (false alarm — composite PK covers specs_for_task per reviewer), CLI set_defaults nit.
- 2026-06-13T20:57:49Z [implementation] — VERIFICATION CHECKLIST (QG-2): (a) full pytest 3765 passed/8 skip pre-review; (b) verify --task green cached (run #728, pytest PASS scoped, receipt signed key 103a83a212851018); (c) DB-init/migration regression 66 passed (migrations+reasoning+specs+doc-counts+mirror-sync); (d) ruff clean on all touched; (e) filesize gate OK — backend_migrations.py=400, backend_schema.py=378, service_specs.py=179, all new <200; (f) MCP .claude mirror imports clean: 107 tools, 8 spec handlers in _DISPATCH; (g) doc-drift scanners 0 issues after README/AGENTS/docs count bumps (99→107 project, 106→114 main, 3866→3893 tests). AC EVIDENCE: 1.CRUD-CLI ✓ (project.py spec help + smoke add/link/list/show/search). 2.CRUD-MCP ✓ (test_mcp_handler_add_and_show, test_mcp_dispatch_registers_spec_tools). 3.closed-list both layers ✓ (test_invalid_type_rejected_at_service + _at_db; link-to-missing errors test_link_to_missing_spec/task). 4.task show linked SPEC ✓ (test_task_show_includes_linked_specs + CLI display). 5.FTS5 ✓ (test_fts_search_finds_spec + delete-trigger + update). 6.tests+docs ✓. Reviewer high/medium fixes verified (slug/version→ServiceError, malformed-FTS→ServiceError, fts_specs rebuild, length caps).
