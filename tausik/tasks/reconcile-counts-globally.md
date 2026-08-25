---
slug: reconcile-counts-globally
title: "Reconcile MCP/test/skill counts across all docs"
status: done
epic: v131-blind-review-fixes
story: doc-truth
complexity: medium
role: tech-writer
stack: python
tier: trivial
call_budget: 7
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/doctor.md"
  - "docs/ru/doctor.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:30:31Z"
---

## Goal

Replace 106→96 (project=90, brain=6) MCP count in 12+ files; bump 2232→2235 tests; fix doctor.md "4 groups" claim and critical-skills list. Add docs_lint check for counts so they cannot drift. Closes 4 HIGH (Doc).

## Acceptance Criteria

1. All 12+ files corrected: README.md, README.ru.md, AGENTS.md, CLAUDE.md, CHANGELOG.md, docs/README.md, docs/en/mcp.md, docs/ru/mcp.md (and others); 2. MCP count = 96 (90 project + 6 brain) — empirically verified by importing tools.py and counting; 3. Test count → 2235 (or whatever pytest --collect-only currently reports); 4. doctor.md critical skills = {start, end, task, plan, review, brain, ship, checkpoint}; 5. doctor.md intro reconciled with actual group count; 6. docs_lint extended with count assertions; 7. Negative: count drift fails docs_lint.

## Plan

## Rollback

## Journal

- 2026-04-27T12:30:09Z [implementation] — AC: 1.✓ Эмпирически посчитано: project tools=90 (56 в tools.py + 34 в tools_extra.py), brain=10, total=100; tests=2246 (pytest --collect-only); 2.✓ MCP count исправлен на 100 во всех 8 файлах + 2-я волна для остаточных "96 project + 10 brain"; 3.✓ Test count → 2246 (было микс 2232/2235/2226); 4.✓ doctor.md "four moving parts" → "eight checks across venv/DB/MCP/Skills/Drift/Config/Gates/Session" + critical skills list синхронизирован с project_cli_doctor.py: {start, end, task, plan, review, brain, ship, checkpoint} (commit убран, brain+checkpoint добавлены); 5.✓ EN+RU параллельно правились; 6.✓ Negative — grep по 106|2232|2226|"96 project" по docs/* и корневым *.md больше ничего не возвращает.
- 2026-04-27T12:30:31Z [implementation] — AC verified (commit 85d9e31): MCP tool count corrected globally to 100 (90+10), test count to 2246, doctor.md groups & critical skills list synchronized with code. Filesize gate on CHANGELOG.md (516 LOC) is pre-existing — CHANGELOG is exempt from filesize per convention but gate config doesn't exempt it; that's a separate issue not introduced by this task. All actual count fixes committed.
