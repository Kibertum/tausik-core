---
slug: the-19-plan-is-a-dated-record-after-the-tag
title: "The 1.9 plan is a dated record once the tag is out: its test compared it with a map that now belongs to 1.10"
status: done
epic: release-110-deferred-from-19
story: deferred-110-outward-loop-and-test-authorship
complexity: simple
role: tech-writer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - TAUSIK-plan-1.9.md
  - "tests/test_plan_19_names_the_composition_in_force.py"
  - ROADMAP.md
scope_paths:
  - TAUSIK-plan-1.9.md
  - "tests/test_plan_19_names_the_composition_in_force.py"
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-14T14:23:28Z"
resolution: null
resolution_reason: null
---

## Goal

tests/test_plan_19_names_the_composition_in_force.py held TAUSIK-plan-1.9.md to the decision ROADMAP.md is built from; the moment decision #374 declared the 1.10 composition the map moved to 1.10 and the 1.9 plan — a document about a release that shipped as tag v1.9.0 on 2026-09-14 — went red for naming #370. The plan is frozen with its release: its header states that 1.9 shipped, with which tag and which composition decision, and the test compares it with the map only while the map is still the 1.9 map; afterwards it holds the shipped statement.

## Acceptance Criteria

AC-1: with ROADMAP.md belonging to 1.10 the test passes and the plan's header says 1.9 shipped on 2026-09-14 as tag v1.9.0 with composition decision #370. AC-2 (negative): a plan header naming another decision number for the shipped composition still reddens; and if ROADMAP.md were the 1.9 map again, the old comparison with the map's decision applies.

## Plan

## Rollback

git revert; one header note and one test

## Journal

- 2026-09-14T14:23:12Z [implementation] — AC-1 ✓ plan header: «1.9 выпущена 14 сентября 2026 тегом v1.9.0; состав выпуска — решение #370»; test branches on the map's version (1.10 now) and holds the shipped sentence + #370. AC-2 ✓ (negative) ::test_a_stale_number_in_the_plan_is_caught swaps the number to #337 and reddens; the 1.9-map branch keeps the old comparison. 48 passed with tests/test_release_roadmap.py.
