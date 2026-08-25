---
slug: version-coherence-1-8
title: "Reconcile version metadata across TODO/CHANGELOG/matrix/constants"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: light
call_budget: 25
defect_of: null
scope: "TODO.md, docs/en/senar-compliance-matrix.md, docs/ru/senar-compliance-matrix.md, scripts/README.md (assess). Coherent version = 1.7.0 released / 1.8 in flight."
scope_exclude: "docs/research/* retros, docs/*/vendor-skills.md example git refs, skill-bundles-migration.md, and any doc snapshotting a PAST release — these are historical records, not current-state metadata. The final 1.7→1.8 version bump/tag is a SEPARATE release task (do not bump pyproject/constants here)."
relevant_files:
  - TODO.md
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - "scripts/README.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T13:32:54Z"
---

## Goal

Restore trust in the discipline framework's own metadata (converged regulation+UX finding): TODO.md says 'Released v1.5.0', constants/pyproject say 1.7.0, branch is release/1.8, senar-compliance-matrix.md header says 'v1.5.1 / 100%'. Produce one coherent statement of current-version + released-vs-in-flight, and refresh the stale matrix header. Part of the 1.8 release cut (coordinate with the pending bump/tag).

## Acceptance Criteria

1. TODO.md line 7 "Released: **v1.5.0**" reconciled to the current coherent statement: latest released = v1.7.0 (matching pyproject/constants), with v1.8 in flight on branch release/1.8. 2. docs/en/senar-compliance-matrix.md:5 framework-version label "TAUSIK v1.5.1" → v1.7.0 (single source = pyproject/tausik_version.__version__). The audit DATE (2026-06-13) is PRESERVED, not bumped: refreshing it would fabricate a compliance audit that did not occur — honesty over a cosmetic freshness stamp. 3. docs/ru/senar-compliance-matrix.md:5 mirrored identically. 4. scripts/README.md:34 "tausik_version.py | Version: 1.1.0" — since tausik_version.py IS the single-source framework version (currently 1.7.0), the stale hardcoded "1.1.0" is DE-HARDCODED to a version-free description so it never drifts on a bump again. 5. No NEW doc drift introduced; doc-drift / version tests stay green; full suite green. NEGATIVE/BOUNDARY: 6. Historical/example version references (docs/research/* retros, vendor-skills example git refs "v1.5.0", migration docs, and the SENAR-SPEC version in the matrix H1 which is a different axis) are LEFT unchanged — "reconcile" targets current-state TAUSIK-framework metadata only, never a rewrite of history nor an unrelated version axis.

## Plan

## Rollback

## Journal

- 2026-07-26T13:32:52Z [implementation] — AC verified: 1. ✓ TODO.md:7 'Released v1.5.0' → 'v1.7.0 released, v1.8 in flight on release/1.8' 2. ✓ docs/en/senar-compliance-matrix.md:5 'TAUSIK v1.5.1'→'v1.7.0'; audit date 2026-06-13 preserved (bumping = fabricated audit) 3. ✓ docs/ru/senar-compliance-matrix.md:5 mirrored 'v1.5.1'→'v1.7.0', date preserved 4. ✓ scripts/README.md:34 'Version: 1.1.0' de-hardcoded → 'Single-source framework version (__version__)'; tausik_version.__version__ confirmed = 1.7.0 5. ✓ docs-only change; verify recorded no_tests_declared (auditable, run #1383, signed receipt). Suite was green with the OLD stale versions → no test asserts matrix-vs-pyproject coherence, so no test affected 6. ✓ Left unchanged: docs/research/* retros, vendor-skills example refs, SENAR-spec version in matrix H1 (different axis) — scope_exclude honored; no pyproject/constants bump (separate release step)
