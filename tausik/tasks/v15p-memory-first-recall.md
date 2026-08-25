---
slug: v15p-memory-first-recall
title: "[P1] Memory strictness: surface context-memory at session start + memory-first-before-asking constraint"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_knowledge_aggregates.py (build_compact_memory_tail + build_memory_block), bootstrap/bootstrap_templates.py (constraint line in MEMORY + MINIMAL_MEMORY or constraints block), tests, docs note"
scope_exclude: "no new MCP tool; no AskUserQuestion hook (prose-asks bypass it — constraint is the lever); memory write hooks unchanged"
relevant_files:
  - "scripts/service_knowledge_aggregates.py"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_memory_context_surfacing.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T18:57:54Z"
---

## Goal

Close the strictness gap exposed by a real incident (agent forgot an established test machine that WAS in project memory and asked the user instead of recalling). Two root causes: (1) build_compact_memory_tail / build_memory_block inject only decision/convention/dead_end — the `context` type (environment facts: hosts, machines, access, paths) is never surfaced at session start, so the agent literally never sees it; (2) no hard constraint telling the agent to memory_search BEFORE asking the user for / guessing an established project fact. Fix both in the framework source so v1.5 actually enforces 'knowledge over experience'.

## Acceptance Criteria

AC1: build_compact_memory_tail surfaces a bounded (<=5) "Context" subsection of `context`-type memories (one line each) so environment facts appear in CLAUDE.md every session. AC2: build_memory_block likewise includes a Context section. AC3: CLAUDE.md template gains a HARD constraint: before asking the user for — or guessing — an established project fact (hosts/machines/env/credentials-location/paths), the agent MUST `tausik_memory_search` first; asking for something already in memory is a process violation. Same line in the minimal-memory variant. AC4: tests cover the context-surfacing (present when context memories exist, absent when none, capped) and the template constraint text; ruff+mypy clean; filesize<400. Negative: empty/zero context memories → no Context subsection emitted, no crash.

## Plan

## Rollback

git revert; additive (extra subsection + a constraint line) — no schema/behavior removal.

## Journal

- 2026-06-14T18:57:39Z [implementation] — Root cause (YPN incident): build_compact_memory_tail + build_memory_block injected only decision/convention/dead_end — `context` type (env facts: hosts/machines/access) never surfaced at session start → agent forgot + asked user. Fix: both functions now emit a bounded Context section (<=5). Plus hard constraint in bootstrap_templates MEMORY + MINIMAL_MEMORY: memory_search/decisions_list BEFORE asking-or-guessing an established project fact; asking for recorded info = process violation; record env facts as `context`. 7 tests (context surfaced/absent/capped, block includes context, both templates carry the rule). ruff+mypy clean, files <400, bootstrap regenerated.
- 2026-06-14T18:57:54Z [implementation] — AC1: ✓ build_compact_memory_tail emits bounded(<=5) Context subsection of context-type memories — test_context_surfaced_when_present + test_context_capped_at_five. AC2: ✓ build_memory_block includes Context section — test_memory_block_includes_context. AC3: ✓ MEMORY + MINIMAL_MEMORY templates carry hard memory-first rule (memory_search before asking/guessing project facts; process violation; record env as context) — test_full/minimal_memory_template_has_memory_first_rule. AC4: ✓ 7 tests; ruff+mypy clean; service_knowledge_aggregates.py 176, bootstrap_templates.py 332 (<400); bootstrap regenerated. Domain: a project that records 'test machine 212 is Linux, ssh user@212' as context now sees it in CLAUDE.md every session — the exact YPN miss is closed. Negative: zero context memories → no Context subsection, empty DB → [] (test_no_context_section_when_none + test_empty_db_returns_empty).
