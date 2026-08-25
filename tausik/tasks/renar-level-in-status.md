---
slug: renar-level-in-status
title: "Surface honest RENAR conformance level in `tausik status`"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/renar_conformance.py (current_level + format_status_line), scripts/project_cli.py (best-effort status line), tests/ (format_status_line tests)"
scope_exclude: "scripts/tausik_utils.py format_status_compact_json (compact path untouched), renar signing/manifest logic"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T14:18:22Z"
---

## Goal

Close the architecture-audit MEDIUM finding: the RENAR adoption level is computed by renar_conformance but never surfaced in the daily dashboard, so the headline initiative's honest state is invisible (anti-drift/dogfooding gap). Add a best-effort one-line RENAR level to the RICH `tausik status` only (NOT the compact JSON hot path, to avoid per-call DB-query cost). Reuses infer_level — surfaces current honest level, does NOT change/climb it.

## Acceptance Criteria

AC-1: renar_conformance gains a lightweight current_level(conn)->verdict helper (gather→eval→infer, no manifest/date needed) and a format_status_line(verdict)->str. AC-2: rich `tausik status` prints a RENAR line, e.g. 'RENAR: RENAR-1 (blocked at RENAR-2: tz_immutable, delta_tz_artifact)' or 'RENAR: pre-adoption (N mandatory clause(s) unmet)'. AC-3: the line is BEST-EFFORT (wrapped so any failure prints nothing, never breaks status) and is NOT added to the compact JSON / status_compact path. AC-4: tests cover format_status_line for level / blocked / pre-adoption verdict shapes. Negative: compact status JSON output is byte-unchanged (no new key); current honest level is read-only (no signing/mutation). AC-5: tests + ruff + filesize (<400) green via .tausik/tausik.

## Plan

## Rollback

git checkout -- scripts/renar_conformance.py scripts/project_cli.py tests/; additive best-effort read-only display, no migration/mutation.

## Journal

- 2026-06-14T14:18:21Z [implementation] — AC verified: 1. ✓ renar_conformance.current_level(conn) + format_status_line(verdict) added (gather→eval→infer, no manifest/date). 2. ✓ rich status prints 'RENAR: RENAR-1 (blocked at RENAR-2: tz_immutable, delta_tz_artifact)' — verified live via .tausik/tausik status. 3. ✓ best-effort try/except in project_cli.py (display-only, never breaks status); NOT in compact path. 4. ✓ 6 tests: pre-adoption(mandatory/signal), achieved+blocked, top-level, live empty-store, live RENAR-1. Negative: compact JSON has no RENAR key (verified: RENAR key present=False); read-only (no mutation/signing). 5. ✓ 15 passed (test_renar_conformance), ruff clean, renar_conformance.py 383<400, project_cli.py 277<400. Domain: the headline RENAR initiative's honest level is now visible in the daily dashboard — closes the architecture-audit anti-drift gap.
