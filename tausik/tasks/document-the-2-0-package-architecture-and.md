---
slug: document-the-2-0-package-architecture-and
title: "Document the 2.0 package architecture and migration baseline"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Measured current and target architecture documentation only"
scope_exclude: "No runtime moves, migration deletion, compatibility break, commit, push or release"
relevant_files:
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/package-layout-2.0.md"
  - "docs/ru/package-layout-2.0.md"
  - "docs/README.md"
  - "docs/_generated/doc-map.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/package-layout-2.0.md"
  - "docs/ru/package-layout-2.0.md"
  - "docs/README.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-10-02T13:51:56Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Replace the misleading flat-scripts architecture description with a measured current-state map and a safe 2.0 target that packages runtime domains without breaking the 1.11 line.

## Acceptance Criteria

AC-1 EN/RU architecture docs state the measured current layout: 563 script files, 502 at root, 34 version migration modules, schema v67. AC-2 A bilingual 2.0 package-layout document defines module boundaries, compatibility shims, rollout order and rollback. AC-3 Migration consolidation explicitly preserves upgrades from every supported 1.11 schema and names the decision needed before old steps can be removed. Negative: no runtime file is moved in the 1.11 release preparation.

## Plan

[{"step": "Measure current module and migration topology", "done": true}, {"step": "Write the bilingual current-state and 2.0 target map", "done": true}, {"step": "Link the map from architecture indexes and changelogs", "done": true}, {"step": "Verify links, bilingual parity and negative no-runtime-change", "done": true}]

## Rollback

Revert the new architecture pages and restored bilingual architecture sections; runtime is untouched

## Journal

- 2026-10-02T13:50:12Z [implementation] — Added bilingual 2.0 package map with one-way dependencies, 1.11 compatibility boundary, baseline plus supported-bridge migration strategy, staged shims and rollback.
- 2026-10-02T13:50:12Z [implementation] — Measured scripts topology: 563 files total, 502 root-level, 501 root Python modules, 71 backend modules, 34 versioned migration modules / 2541 lines, current schema v67; flat sys.path injection is used by bootstrap and MCP.
- 2026-10-02T13:50:13Z [implementation] — Linked the 2.0 map from bilingual architecture and docs index; corrected stale schema, migration, core-skill and MCP counts; recorded the boundary in both 1.11 changelogs.
- 2026-10-02T13:51:05Z [implementation] — Doc-map gate rejected the undefined reader 'contributor'; changed both pages to the closed reader 'maintainer' and regenerated the map.
- 2026-10-02T13:51:52Z [implementation] — AC verified: AC-1 measured topology is stated in both architecture pages. AC-2 bilingual package map is registered and fresh: ✓ tests/test_doc_map.py::test_the_generated_map_is_fresh. AC-3 the migration page keeps the 1.11 chain and requires an explicit minimum-source-schema decision before removal. Negative: scope contains documentation and changelogs only; no runtime file was moved. Domain: the plan follows the observed bootstrap/MCP flat sys.path imports and separates the 1.11 compatibility line from the 2.0 import contract.
- 2026-10-02T13:51:52Z [implementation] — Targeted documentation suite passed 253 tests: relative links, generated doc map, and gate-list parity. Verify #3389 passed every applicable documentation gate; ruff/pytest/hadolint were correctly non-applicable to a docs-only declared scope. No runtime module was moved.
