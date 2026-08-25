---
slug: doc-drift-split-and-regex
title: "Split doc_drift_scanners.py (524L filesize breach) + harden count regexes"
status: done
epic: null
story: null
complexity: complex
role: developer
stack: null
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/doc_drift_scanners.py (trim to scan-fns + re-exports); scripts/doc_drift_common.py (NEW: shared constants+helpers); scripts/doc_drift_fixes.py (NEW: auto-fix fns); tests/test_doc_write_fixes.py + a new scanner regex test; README.md (hooks 21→22); docs/ru/architecture.md (test example 4101→6022)."
scope_exclude: "scripts/gen_doc_constants.py (consumer — imports must stay working UNCHANGED via re-export); all other scanners/gates; .claude/ deployed copies."
relevant_files:
  - "scripts/doc_drift_scanners.py"
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_fixes.py"
  - "tests/test_doc_drift_scanners.py"
  - "tests/test_doc_write_fixes.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T11:11:32Z"
---

## Goal

Fix the sole real filesize-rule violation: split scripts/doc_drift_scanners.py (524 lines) at the existing '# Auto-fix:' seam (~line 415) into a doc_drift_fixes.py sibling with re-export for import stability (same pattern gate_filesize.py used). Simultaneously harden the count regexes so they catch the drift they currently miss — '21 real-time hooks' (word between number and 'hooks'), bare '(4101)' test counts, 'хук' singular — then reconcile README hooks count (21→22) and architecture.md test count (4101→6022). Converged finding from architecture + UX audits.

## Acceptance Criteria

1. scripts/doc_drift_scanners.py ≤400 lines (filesize gate passes). Auto-fix machinery → new scripts/doc_drift_fixes.py; shared regex/pattern constants + shared helpers → new scripts/doc_drift_common.py, so all three modules stay under cap with NO duplication and NO circular import (dependency is one-directional: scanners→common, scanners→fixes, fixes→common; fixes never imports scanners). 2. Existing imports keep working: `from doc_drift_scanners import scan_version_refs/scan_py_version_constants/scan_mcp_tool_counts/scan_test_counts/scan_code_counts/write_cross_file_fixes` AND `CROSS_FILE_SCAN_TARGETS` still resolve (re-export), so gen_doc_constants + tests/test_doc_write_fixes.py are unchanged. 3. Hooks regex hardened to catch the genuine NON-FENCED miss the UX audit found — '21 real-time hooks' (adjective between number and 'hooks', README:138) — plus 'хук' singular/other RU cases; narrow enough not to false-positive. 4. Reconcile stale literals: README hooks 21→22, architecture.md test example 4101→6022 (the latter is INSIDE a ```bash fence and is fixed as a literal only — the scanner deliberately does NOT scan fences, and that illustrative-number guard is preserved, NOT weakened). 5. Full existing doc-drift suite passes + new test pins the hardened hooks pattern. NEGATIVE/EDGE: auto-fixer still must NOT rewrite numbers inside fenced blocks or CLAUDE.md DYNAMIC section; hardened hooks regex must not match illustrative prose.

## Plan

## Rollback

git checkout -- scripts/doc_drift_scanners.py tests/test_doc_write_fixes.py README.md docs/ru/architecture.md && rm -f scripts/doc_drift_common.py scripts/doc_drift_fixes.py (new files); imports revert automatically since scanners re-exports restore.

## Journal

- 2026-07-26T10:59:33Z [planning] — DECISION (scope refinement): the UX audit flagged architecture.md '4101' as scanner-missed drift, but it sits INSIDE a ```bash fence (verified: 9 fences precede line 296 = odd = inside). The scanner strips fences on purpose — the illustrative-number guard that stops it flagging 'add 5 tests where one parametrized covers'. Teaching it to scan fences to catch this one number would reintroduce that whole false-positive class. So: fix 4101→6022 as a plain literal (hygiene), do NOT add fence-scanning. The real scanner gap is '21 real-time hooks' (non-fenced bullet, README:138) — 'real-time' between number and 'hooks' evades \b(\d+)\s+hooks\b. That regex IS hardened. Dropped the '(N tests) paren pattern' from the original AC for the same fence reason.
- 2026-07-26T11:10:05Z [implementation] — AC verified: 1. ✓ doc_drift_scanners.py=239L (was 524), doc_drift_common.py=242L, doc_drift_fixes.py=135L — all ≤400; filesize gate passes. No duplication; no circular import (verified both import orders load clean). 2. ✓ Re-exports intact: `from doc_drift_scanners import scan_version_refs/scan_py_version_constants/scan_mcp_tool_counts/scan_test_counts/scan_code_counts/write_cross_file_fixes/CROSS_FILE_SCAN_TARGETS` all resolve; gen_doc_constants imports OK, __all__ intact. 3. ✓ Hooks regex hardened: catches '21 real-time hooks' + RU '21 real-time-хук' + '5 хуков'; rejects 'stack-scoped gates'/'add 5 tests' (validated 6/6). 4. ✓ README hooks 21→22 (EN+RU), architecture test example reconciled to live 6096; fenced 4101 fixed as literal, scanner still skips fences by design. 5. ✓ 71 related tests pass incl. previously-failing test_check_docs_hook::test_exit_0_when_in_sync; new tests/test_doc_drift_scanners.py (7 tests) pins hardened pattern + fenced-skip + idempotent fix; gen_doc_constants --check clean. Constants regenerated (test_count→6096). Domain: the gate that guards doc accuracy is itself now cap-compliant and actually catches the drift it advertises.
