---
slug: d2-en-cli-refresh
title: "docs/en/cli.md refresh"
status: done
epic: docs-overhaul-v13
story: docs-en-refresh
complexity: null
role: tech-writer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/cli.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:13:09Z"
---

## Goal

docs/en/cli.md refreshed with all v1.3 commands

## Acceptance Criteria

1. docs/en/cli.md reflects v1.3 command surface (epic/story/task/session/gates/skill/brain/stack/role/memory/doctor/hud/metrics/roadmap/events/search/decide/dead-end/explore/audit/run/doc/verify/suggest-model/team/update-claudemd/fts/init); 2. Every command shows correct flags (e.g. task done --ac-verified); 3. Removed/renamed CLI noted; 4. Examples use .tausik/tausik wrapper; 5. Negative: removed commands not present, no stale `--force` for task done

## Plan

## Rollback

## Journal

- 2026-04-26T16:13:05Z [implementation] — Rewrote docs/en/cli.md for v1.3. Added: stack/role/doctor/verify/audit/brain/run/doc top-level commands, session recompute, task logs, task done --evidence, task start --force, task add --call-budget/--tier, expanded stacks list to 25, removed stale `task done --force` mention, documented hybrid role storage, scoped pytest gate + verify cache, gap-based session active-time. AC: 1.✓ all v1.3 commands shown; 2.✓ flags accurate; 3.✓ removed --force on task done documented as removed; 4.✓ examples use .tausik/tausik wrapper; 5.✓ negative — no stale --force.
- 2026-04-26T16:13:09Z [implementation] — AC verified: 1.✓ v1.3 surface complete (epic/story/task/session/gates/skill/brain/stack/role/memory/doctor/hud/metrics/roadmap/events/search/decide/dead-end/explore/audit/run/doc/verify/suggest-model/team/update-claudemd/fts/init); 2.✓ flags match `--help` output for task add/done/start/update/list/logs and session/stack/role; 3.✓ removed `task done --force` documented as gone; 4.✓ wrapper convention `.tausik/tausik` shown; 5.✓ negative — no retired commands or stale --force.
