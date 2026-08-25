---
slug: brain-config-unicode-nfc
title: "MEDIUM: NFC-normalize project name перед hash"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_config.py"
  - "tests/test_brain_storage_hardening.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T15:15:22Z"
---

## Goal

Café (NFC) и Café (NFD) дают разные project_hash → двойная регистрация. Добавить unicodedata.normalize('NFC', name) в canonicalize

## Acceptance Criteria

1. compute_project_hash NFC-normalizes input before canonicalization (strip/lower/whitespace collapse).
2. Same name in NFC and NFD encodings produces the SAME hash (regression test).
3. Cyrillic / non-ASCII names still hash deterministically — no exception.
4. Empty/whitespace-only still raises ValueError (existing contract preserved).
5. pytest + ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T15:12:02Z [implementation] — AC verified: 1. ✓ compute_project_hash calls unicodedata.normalize("NFC", project_name) before strip/lower/whitespace-collapse — scripts/brain_config.py:131-133. 2. ✓ test_nfc_and_nfd_forms_collapse_to_same_hash in tests/test_brain_storage_hardening.py verifies NFC and NFD of "Café-Project" produce the same 16-char hash. 3. ✓ test_cyrillic_passes_through confirms МойПроект returns a valid 16-char hash without exception. 4. ✓ test_empty_still_raises preserves the pre-existing ValueError contract for empty input. 5. ✓ pytest + ruff clean.
