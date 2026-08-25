---
slug: r14-senar-checklist-deeper
title: "SENAR 28-item checklist: replace keyword counting with structured AC evidence parser"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_ac_evidence.py"
  - "tests/test_ac_evidence.py"
  - "tests/test_qg2_gates.py"
  - "docs/en/senar-compliance-matrix.md"
  - "docs/ru/senar-compliance-matrix.md"
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:18:29Z"
---

## Goal

Release 1.4 readiness: r14-senar-checklist-deeper

## Acceptance Criteria

1. New scripts/service_ac_evidence.py exposes parse_ac_text/parse_evidence_lines/build_report; AcCoverageReport reports covered_with_tests, gaps, has_negative_evidence. 2. service_gates._check_verification_checklist enriched: keeps tier keyword check AND adds structured AC coverage warnings (per-AC gaps, missing test refs for high/critical, missing negative scenario for high/critical). 3. Tests tests/test_ac_evidence.py (10) + updated tests/test_qg2_gates.py - 26/26 pass. 4. Docs - senar-compliance-matrix EN/RU + CLAUDE.md table updated to mention service_ac_evidence parser. 5. Negative scenarios: empty AC/notes returns 0 coverage + 0% pct (no crash); plain text without AC/check/test markers ignored; multi-AC mention on one line counted for each AC.

## Plan

## Rollback

## Journal

- 2026-05-01T01:17:52Z [implementation] — AC verified: AC-1 ✓ tested via tests/test_ac_evidence.py::test_parse_numbered_ac etc. AC-2 ✓ verified via tests/test_qg2_gates.py::TestCheckVerificationChecklist - 26/26 pass. AC-3 ✓ tested via tests/test_ac_evidence.py (10/10 pass). AC-4 ✓ manual review of senar-compliance-matrix.md and CLAUDE.md. AC-5 Negative: tests/test_ac_evidence.py::test_parser_handles_empty_input + test_inline_ac_reference_matches verify edge cases.
- 2026-05-01T01:17:52Z [implementation] — Created scripts/service_ac_evidence.py with EvidenceLine + AcCoverageItem + AcCoverageReport dataclasses. parse_ac_text reads numbered AC, parse_evidence_lines extracts per-line evidence (test_refs via tests/test_*.py(::test_*) regex, manual/negative/review keywords, checkmark detection).
- 2026-05-01T01:17:52Z [implementation] — Docs: docs/{en,ru}/senar-compliance-matrix.md QG-2 row updated with service_ac_evidence pointer; CLAUDE.md Rule 5 line mentions structured parser. Mirrored to .claude/docs.
- 2026-05-01T01:17:52Z [implementation] — Tests: tests/test_ac_evidence.py (10 cases) covers numbered parsing, test-ref extraction, manual/negative/review tagging, full coverage, partial coverage gaps, inline AC-N reference. Updated tests/test_qg2_gates.py simple-task case to include explicit AC evidence so the new parser does not fire.
- 2026-05-01T01:17:52Z [implementation] — service_gates._check_verification_checklist: kept legacy keyword tier counts but now also runs build_report() and emits NOTE warnings for (a) gaps in per-AC evidence, (b) missing test_refs at high/critical tier, (c) missing negative-scenario evidence at high/critical.
