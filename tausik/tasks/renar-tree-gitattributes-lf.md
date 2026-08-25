---
slug: renar-tree-gitattributes-lf
title: "Make renar export --check stable: LF pin (.gitattributes) + drop volatile operational counts from conformance view"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: renar-file-export
scope: ".gitattributes (new), scripts/renar_export.py (_conformance_doc: drop raw-counts), tests/test_renar_export.py (determinism-vs-operational-activity test). Bootstrap after script edit."
scope_exclude: "Do NOT change write_tree newline handling (LF is correct). Do NOT add a global * eol=lf that could reformat unrelated tracked files — scope the rule to renar/ (and *.md if safe)."
relevant_files:
  - ".gitattributes"
  - "scripts/renar_export.py"
  - "tests/test_renar_export.py"
  - "renar/conformance.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T11:19:53Z"
---

## Goal

Two entangled determinism defects break `tausik renar export --check` as a CI gate: (1) no .gitattributes + autocrlf=true → renar/*.md checks out CRLF vs LF generator → false drift on fresh clones; (2) the exported conformance.md embeds raw-counts including operational counters (verification_runs_count, memory_edges_count, reasoning_tasks_count) that change on every `verify`/`memory add`, UNRELATED to RENAR artifacts → the tree churns on any activity and --check fails mid-session (observed: conformance.md drifted after a verify run). Fix both so --check only reacts to actual RENAR-artifact changes.

## Acceptance Criteria

AC-1: `.gitattributes` pins `renar/**` to text eol=lf (`git check-attr eol` → lf). AC-2 (cross-platform): with autocrlf=true a fresh checkout keeps LF (no CRLF) so --check sees no false drift. AC-3: the exported conformance view drops the volatile raw-counts block (verification_runs/memory_edges/reasoning_tasks counters); it keeps level, pre-adoption, blocked-at, mandatory-clauses-confirmed, level-signals (all RENAR-artifact-stable). AC-4 (determinism/negative): running `tausik verify` or adding a memory between two exports does NOT change conformance.md (a regression test seeds artifacts, snapshots conformance.md, runs a verification_run insert, re-builds, asserts identical) — tested via tests/test_renar_export.py. AC-5: local `tausik renar export --check` exits 0 after regen; ruff+mypy clean, files <400.

## Plan

## Rollback

git revert / remove the .gitattributes lines. No code change.

## Journal

- 2026-06-14T11:19:34Z [implementation] — Root cause (edge-case): the renar export --check gate had two cross-environment determinism holes not visible in static-DB tests — (1) no .gitattributes + core.autocrlf=true made git check out renar/*.md as CRLF vs the LF generator; (2) the conformance view embedded gather_signals raw-counts (verification_runs/memory_edges/reasoning_tasks), operational counters that move on every verify/memory op unrelated to RENAR artifacts, churning the tree mid-session. Prevention: scoped .gitattributes (renar/** eol=lf) pins newlines on every platform; _conformance_doc now exports only RENAR-artifact-derived state (level/signals/clauses), never raw operational counters; a regression test inserts a verification_run between two builds and asserts conformance.md is byte-identical. Real proof: a live `tausik verify` (which inserts a verification_run) left --check exit 0.
- 2026-06-14T11:19:53Z [implementation] — AC verified: 1. ✓ .gitattributes pins renar/** eol=lf — `git check-attr eol -- renar/conformance.md` → 'eol: lf' (was unspecified) 2. ✓ Cross-platform: with core.autocrlf=true the renar tree is forced LF on checkout via the text eol=lf rule — no CRLF conversion, so --check sees no false drift 3. ✓ _conformance_doc drops raw-counts; keeps level/pre-adoption/blocked-at/mandatory-clauses-confirmed/level-signals — tests/test_renar_export.py::test_conformance_excludes_volatile_counts 4. ✓ Negative/determinism: inserting a verification_run between two builds leaves conformance.md byte-identical — tests/test_renar_export.py::test_operational_activity_does_not_change_conformance; REAL proof: a live `tausik verify` (inserts a verification_run) left `renar export --check` exit 0 5. ✓ local --check exit 0 after regen; ruff+mypy clean; 21 export tests green; files <400
