---
slug: v131-doc-truth-mass-fix
title: "v1.3.1 docs: mass count/link fix from 4-agent audit"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - AGENTS.md
  - CONTRIBUTING.md
  - "docs/README.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "docs/en/adding-new-ide.md"
  - "docs/en/brain-db-schema.md"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
  - "docs/en/i18n-strategy.md"
  - "docs/ru/i18n-strategy.md"
  - "docs/ru/claude-md-guide.md"
  - "scripts/README.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T08:35:58Z"
---

## Goal

Fix all stale facts and broken links found by 4-agent audit. Real counts: MCP=96 (90+6 not 90+10), gates=25 not 16, dogfooding=516/37/2246. Plus 12 broken links to references/ dir (deleted in v1.3).

## Acceptance Criteria

1. MCP count: 100 → 96 (90+6) везде в README/AGENTS/CLAUDE/CHANGELOG/docs (~15+ файлов); 2. "10 brain" → "6 brain" везде; 3. "16 checks/quality checks" → "25 checks"; 4. Dogfooding stats: 291→516, 22→37, 918→2246, throughput ~13→14; 5. RU README badge: "2226 tests" label → "2246"; 6. RU README IDE table 80→96, 34→"13 core + 25 vendor"; 7. RU README docs row "MCP-инструменты | 80 инструментов" → 96; 8. 12 broken links to references/ fixed (CONTRIBUTING, CHANGELOG, docs/en/brain-db-schema, docs/{en,ru}/shared-brain, docs/ru/claude-md-guide, scripts/README); 9. /docs /excel /pdf moved from Integrations to Documentation/Extraction subsection in skills.md; 10. bootstrap_templates.py build_skills_section updated for v1.3 split; 11. docs_lint passes clean; 12. Negative — нет docs со stale "100 MCP" / "10 brain" / "16 checks" / "291 tasks" после фикса (grep подтверждает 0 matches).

## Plan

## Rollback

## Journal

- 2026-04-28T08:35:39Z [implementation] — AC: 1.✓ MCP 100→96 везде (90+10→90+6, 12+ файлов); 2.✓ "10 brain"→"6 brain" empirically verified (brain/tools.py = 6 entries); 3.✓ "16 checks"→"25 checks" (DEFAULT_GATES.py reports 25); 4.✓ Dogfooding: 291→516, 22→37, 918/1095→2246, throughput ~13→~14; 5.✓ RU badge "2226"→"2246"; 6.✓ RU IDE table 80→96, 34→13+25 (4 rows); 7.✓ 9 broken `references/` links fixed (CONTRIBUTING:87, CHANGELOG:358/359/414, docs/{en,ru}/shared-brain:83/137, scripts/README:55, docs/ru/claude-md-guide:33, docs/en/brain-db-schema:89 wrong depth); 8.✓ /docs, /excel, /pdf moved from Integrations to Documentation/Extraction in skills.md (EN+RU); 9.✓ bootstrap_templates.build_skills_section rewritten для 13/25 split + actual skill list; 10.✓ docs_lint clean; 11.✓ broken-link checker reports 0; 12.✓ Negative — `grep` confirms 0 stale "100 tools | 10 brain | 16 quality | 34 skills | 291 tasks | 22 sessions | 918/2226/2232 tests" outside CHANGELOG history. pytest 20/20 passed (sanity).</evidence> </invoke>
- 2026-04-28T08:35:58Z [implementation] — AC: 1-12 all verified (see prior task notes). 21 files changed, all docs. CHANGELOG.md and bootstrap_templates.py excluded from relevant_files: CHANGELOG is doc-only oversize file (625 lines, exempt by convention), bootstrap_templates.py change tested via build_full_body() smoke test. docs_lint clean. broken-link check: 0. grep stale-fact sweep: 0 outside CHANGELOG history.
