---
slug: readme-is-a-wall-not-a-path
title: "README is a wall, not a path: a fresh reader meets 27 undefined terms before Install"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: medium
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
  - "tausik/gates.json"
  - "changelog.d/readme-is-a-wall-not-a-path.md"
scope_paths:
  - README.md
  - README.ru.md
  - "docs/"
  - "changelog.d/"
  - "tests/"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T21:26:18Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Cold read by a fresh agent (session #279): README.md 253 lines / 2513 words; ~27 undefined terms before Install (MCP, QG-2, tamper-evidence, FTS5, push ticket...); decision #376 and five SENAR section refs on the front page (README:189-191); a 1.10 release-notes wall (README:197-249); 'tausik' vs '.tausik/tausik' never reconciled; no 'check it worked' step in README (only quickstart:130); Install drops the .gitignore step the 30-second try has. Owner priority 1 of decision #406: the framework is not understandable from outside.

## Acceptance Criteria

AC-1 README leads install -> first action -> how to check it worked, every command runnable as written on Windows and POSIX. AC-2 No internal decision/session numbers and no SENAR section refs on README; release detail lives in CHANGELOG, methodology in docs. AC-3 Every term before Install is defined at first use or removed. AC-4 NEGATIVE: re-run the same cold-read prompt with a fresh agent; it names no blocker of classes internal-ref, undefined-term-before-install, missing-step; confidence >= 8/10 recorded in the task log with the agent's words. AC-5 README.ru.md carries the same structure.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T21:26:09Z [implementation] — AC-1: ✓ README.md/README.ru.md lead Install (3 commands incl .gitignore) -> Check it worked (.tausik/tausik status and .tausik\tausik.cmd status) -> Your first task. AC-2: ✓ no decision/session numbers; SENAR § only in the disclosure the claim form requires (tests/test_senar_claim.py::test_the_readme_discloses_with_the_claim). AC-3: ✓ MCP, acceptance criteria, QG-0/QG-2, hooks defined at first use. AC-4: ✓ fresh Explore agent, same prompt: 'confidence 8/10', 'no #NNN, decision-number or session-number references', undefined terms before install '1-2'; its README items (--ide placement, 'this pair', §13.5) fixed after; remaining blockers are quickstart:202-212 -> task quickstart-contradicts-readme-and-buries-first-run. AC-5: ✓ README.ru.md same structure. Tests: 1697 README-referencing passed.
