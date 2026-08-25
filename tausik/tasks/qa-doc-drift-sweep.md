---
slug: qa-doc-drift-sweep
title: "Doc-drift sweep: CHANGELOG RENAR entry + mcp.md spec/adapt family + architecture.md stale counts"
status: done
epic: v15-polish
story: v15p-debt
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: "CHANGELOG.md, CHANGELOG.ru.md, docs/ru/mcp.md, docs/ru/architecture.md, docs/ru/agent-contract.md (docs only)"
scope_exclude: "scripts/*, tests/*, docs/_generated/* (no source/generated edits)"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/ru/mcp.md"
  - "docs/ru/architecture.md"
  - "docs/ru/agent-contract.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T12:24:52Z"
---

## Goal

Close documentation drift the Rule 9.5 audit found: (1) RENAR Phase 0-1 (commit ced03a3) shipped but absent from CHANGELOG.md/CHANGELOG.ru.md; (2) tausik_spec_*/tausik_adapt_* (17 MCP tools) missing from docs/ru/mcp.md; (3) architecture.md says 'до v27' (actual v37), has 3 conflicting test-counts, an incorrect '0 CLI-only gaps' claim, and skills 12 vs live 13.

## Acceptance Criteria

AC-1: CHANGELOG.md + CHANGELOG.ru.md [Unreleased] both gain a RENAR Phase 0-1 entry (renar export + first SPEC-ARCH/ADAPT, RENAR-1). AC-2: docs/ru/mcp.md line ~11 project-tool count 99→116 AND a new SPEC/ADAPT (RENAR substrate) section documents all 17 tausik_spec_*/tausik_adapt_* tools. AC-3: docs/ru/architecture.md 'до v27'→'до v37' (verified: migrations reach v37), '12 core'→'13 core' (constants=13), test count '(3844)'→'(4083)'. AC-4: docs/ru/agent-contract.md:119 '0 CLI-only gaps' reworded to reflect intentional CLI-only maintenance verbs. Negative: '27 таблиц + 8 FTS5' left UNCHANGED (verified accurate: 27 base + 8 fts_* = 35 total); no false numbers introduced — every count cross-checked against constants.json / live DB / migrations. AC-5: check_docs cross-file gate stays green after edits.

## Plan

## Rollback

git checkout -- CHANGELOG.md CHANGELOG.ru.md docs/ru/mcp.md docs/ru/architecture.md docs/ru/agent-contract.md (pure doc edits, no migrations/flags; trivially revertible)

## Journal

- 2026-06-14T12:24:39Z [implementation] — All 5 doc files edited. architecture.md: до v27→v37 (migrations verified reaching v37), 12→13 core skills (constants_core=13), 3844→4083 tests. agent-contract.md:119: '0 CLI-only gaps' reworded (intentional maintenance verbs). mcp.md: project count 99→116, new 'RENAR substrate — SPEC+ADAPT (17)' section with accurate per-tool descriptions+required params pulled from harness tools_spec.py/tools_adapt.py. CHANGELOG.md+ru: [Unreleased] RENAR Phase 0-1 entry. VERIFIED NOT changed: '27 таблиц + 8 FTS5' (live DB: 27 base + 8 fts_* = 35 — accurate; audit had conflated with schema v37). check_docs+gen_doc_constants: 42 passed.
- 2026-06-14T12:24:51Z [implementation] — AC verified: 1. ✓ CHANGELOG.md + CHANGELOG.ru.md [Unreleased] both gained RENAR Phase 0-1 entry (renar export + SPEC/ADAPT substrate + RENAR-1) — git diff shows +6/+6 2. ✓ docs/ru/mcp.md: project count 99→116; new 'RENAR substrate — SPEC+ADAPT (17)' section, descriptions+required params sourced verbatim from harness/claude/mcp/project/tools_{spec,adapt}.py (8 spec + 9 adapt) 3. ✓ architecture.md: 'до v27'→'до v37' (verified migrations reach v37), '12 core'→'13 core' (constants skills_core_count=13), '(3844)'→'(4083)' (live test_count) 4. ✓ agent-contract.md:119 '0 CLI-only gaps' reworded to 'agent-loop verbs полностью покрыты, CLI-only — только намеренные maintenance/operator verbs (см. mcp.md)' 5. ✓ Negative: '27 таблиц + 8 FTS5' left UNCHANGED — live DB confirms 27 base + 8 fts_* tables (audit's 'should be 37' was a schema-version/table-count conflation). check_docs+gen_doc_constants 42 passed; no false numbers introduced
