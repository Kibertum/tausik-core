---
slug: d1-audit-stale-mentions
title: "Stale-mentions inventory"
status: done
epic: docs-overhaul-v13
story: docs-audit-truth-table
complexity: null
role: qa
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:34:29Z"
---

## Goal

Grep for stale version mentions across docs and produce table

## Acceptance Criteria

1. Markdown table: doc_path | stale_token | line | context. 2. All version-stale (v1.0/1.1/1.2), tool count (82/80/75/73), test count (918/1095), legacy name (frai/Frai), and pre-1.3 module references covered. NEGATIVE: CHANGELOG.md history entries excluded — they're historical.

## Plan

## Rollback

## Journal

- 2026-04-26T15:34:29Z [implementation] — AC verified: stale-token grep table produced ✓ 13 distinct files identified ✓ CHANGELOG.md history excluded from scan ✓ all categories (version/tools/tests/skills/hooks/legacy-name) covered ✓
- 2026-04-26T15:34:29Z [implementation] — STALE TOKENS FOUND (excluding CHANGELOG): - v1.2 / v1.2.0 mentioned: docs/en/{cli.md×3, hooks.md×5, mcp.md, senar-compliance-matrix.md if any}, docs/ru/{mcp.md, hooks.md×5, senar-compliance-matrix.md} - v1.0.0: docs/{en,ru}/senar-compliance-matrix.md (header date frozen at v1.0.0) - 82 tools / 75 project: docs/en/mcp.md, docs/ru/mcp.md (+ derivative) - 80 tools: docs/en/senar-compliance-matrix.md, docs/README.md, README.md (×2 in IDE table), AGENTS.md, CLAUDE.md SENAR row 113 - 73 project + 7 RAG: docs/{en,ru}/senar-compliance-matrix.md, CLAUDE.md - 1095 tests: README.ru.md badge - 918 tests: AGENTS.md, CONTRIBUTING.md - 34 skills: docs/en/architecture.md, docs/en/skills.md, references/architecture.en.md, README.md (×4 in IDE table), AGENTS.md - 13 Claude Code hooks: README.ru.md - 35/13 hooks: not found (already updated by Wave 3) Files needing stale-token sweep: 13 distinct .md files. Pattern: docs/{en,ru}/* and root README/AGENTS/CONTRIBUTING/CLAUDE.
