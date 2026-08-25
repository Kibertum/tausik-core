---
slug: fix-factual-errors-and-broken-links-in-docs
title: "Fix factual errors and broken links in docs"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "README.md, README.ru.md, skills-official/README.md, TODO.md, AGENTS.md"
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - "skills-official/README.md"
  - TODO.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T13:16:15Z"
---

## Goal

All markdown files have correct metrics, links, and references — no stale data

## Acceptance Criteria

1. README.md/README.ru.md metrics match actual (266 tasks, 15 sessions). 2. No `/go` references — all replaced with `/plan`. 3. skills-official/README.md uses github.com URL. 4. TODO.md reflects post-release state. 5. All cross-links between root md files resolve correctly. 6. No broken links to non-existent files (negative: grep for dead refs returns 0).

## Plan

## Rollback

## Journal

- 2026-04-07T13:03:11Z [implementation] — Fixed: README.md/README.ru.md metrics 258→266, 12→15, throughput recalculated. Replaced /go→/plan in both READMEs. Fixed skills-official/README.md gitlab→github URLs. Updated TODO.md to post-release. Verified all 30 cross-links — all resolve OK.
- 2026-04-07T13:03:19Z [implementation] — AC verified: 1. README metrics=266/15 ✓ 2. grep /go returns 0 hits ✓ 3. skills-official uses github.com ✓ 4. TODO.md post-release ✓ 5. All cross-links resolve ✓ 6. No broken links (verified 30 files) ✓
