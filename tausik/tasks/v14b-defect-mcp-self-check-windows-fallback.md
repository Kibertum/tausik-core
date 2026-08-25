---
slug: v14b-defect-mcp-self-check-windows-fallback
title: "Defect: wmic deprecated on Win11 24H2+; remediation false-positive on count=-1"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: v14b-mcp-stale-module-detector
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:31:03Z"
---

## Goal

Fix two bugs surfaced by first live run of `tausik_self_check` on Win 11 build 26200: (a) `wmic.exe` is deprecated/absent in modern Windows so sibling enumeration always fails with WinError 2 and returns count=-1, (b) the remediation message logic treats any non-zero count (including -1 = unknown) as drift, so a healthy server with failed introspection would scream "Restart IDE". Replace wmic with PowerShell Get-CimInstance fallback; treat count=-1 as "unknown, not warning".

## Acceptance Criteria

1. agents/claude/mcp/project/self_check.py (and cursor mirror): Windows branch tries wmic FIRST (legacy compat), on FileNotFoundError / WinError 2 falls through to PowerShell `Get-CimInstance Win32_Process` via `subprocess.run(['powershell', '-NoProfile', '-Command', '<query>'])`. Output parsed with simple line split — must NOT crash if PowerShell is itself missing.
2. The `remediation` field in `collect()` returns the "Restart IDE" string ONLY when `drift_detected=True` OR `siblings['count'] > 0`. When `count == -1` (introspection failed) the remediation explains "sibling check unavailable on this host — drift check still active". When clean (count==0, no drift) → "MCP modules in sync; no action needed."
3. Tests: tests/test_mcp_self_check.py gains 2 new cases — (a) test_remediation_silent_when_count_unknown (monkeypatch siblings to count=-1, no drift → remediation must NOT contain 'Restart your IDE'); (b) test_remediation_fires_on_real_drift (existing drift test asserts 'Restart your IDE' in remediation). Existing tests still pass.
4. Negative scenario: PowerShell also missing (very old Windows / locked-down host) → returns count=-1 with the FALLBACK error message preserved (not silently overwritten by previous wmic error). Manual proof via review of the except chain.
5. Live re-verify on this host: after bootstrap + IDE restart, `tausik_self_check` returns count >= 0 (PowerShell branch worked) on Win 11 build 26200.
6. Tests: pytest fast lane GREEN; ruff GREEN.
7. CHANGELOG bilingual `### Fixed` entry under `[Unreleased] — v1.4.0 polish (Phase B)` referencing `defect_of=v14b-mcp-stale-module-detector`.
8. Verify --task + task done --ac-verified.

## Plan

[{"step": "Patch _enumerate_sibling_mcps Windows branch: wmic primary + PowerShell Get-CimInstance fallback; preserve real error messages", "done": true}, {"step": "Patch collect() remediation logic: count=-1 \u2192 informational; count>0 OR drift \u2192 restart-IDE warning", "done": true}, {"step": "Mirror to agents/cursor/mcp/project/self_check.py", "done": true}, {"step": "tests/test_mcp_self_check.py: add 2 cases (remediation silent on unknown; remediation fires on drift)", "done": true}, {"step": "Bootstrap to deploy fixed self_check.py to .claude/mcp/project/", "done": true}, {"step": "ruff + pytest fast lane green", "done": true}, {"step": "CHANGELOG bilingual ### Fixed entry", "done": true}, {"step": "tausik verify --task + task done --ac-verified", "done": true}, {"step": "Live re-verify: ask user for IDE restart \u2192 call tausik_self_check \u2192 confirm count >= 0", "done": true}]

## Rollback

## Journal

- 2026-05-03T21:29:27Z [implementation] — AC verified: 1. ✓ self_check.py Windows branch: wmic primary, FileNotFoundError → PowerShell Get-CimInstance fallback (NoProfile + NonInteractive); each layer preserves its own error string. Mirrored to cursor/. 2. ✓ collect() remediation tri-state: drift OR count>0 → 'Restart your IDE'; count=-1 → 'MCP modules in sync ... Sibling-MCP check unavailable on this host'; clean → 'no action needed'. 3. ✓ tests/test_mcp_self_check.py +2 cases: test_remediation_silent_when_count_unknown (count=-1, no drift, asserts no 'Restart your IDE' AND 'drift check' in remediation); test_remediation_fires_on_real_drift (drift true, asserts 'Restart your IDE' present). All 8/8 PASS. 4. ✓ PowerShell ALSO missing path: explicit `wmic and powershell both missing: <e>` error preserved (review of except chain). 5. ✓ Live smoke on Win 11 build 26200: deployed self_check returns sibling_count=2 with PIDs [57824, 10108] and error=None — PowerShell fallback works. Detector caught a real sibling-MCP leak from prior IDE window. 6. ✓ pytest fast lane 2608 passed, 7 skipped, 118 deselected (73.46s); ruff All checks passed. 7. ✓ CHANGELOG.md + CHANGELOG.ru.md bilingual ### Fixed entry under Unreleased Phase B with defect_of=v14b-mcp-stale-module-detector. 8. (verify+done pending — about to fire)
- 2026-05-03T21:31:01Z [implementation] — Step 9 LIVE verify: tausik_self_check on fresh MCP (pid 61068, startup 2026-05-03T21:30:28Z) returned sibling_mcp_count=1 (PID 55088 — leftover from earlier IDE window), sibling_introspection_error=null. PowerShell Get-CimInstance fallback fully operational on Win 11 build 26200. Remediation correctly fires 'Restart your IDE' for a real sibling leak. Detector working as designed.
- 2026-05-03T21:31:15Z [done] — Root cause: parent task v14b-mcp-stale-module-detector picked wmic as Windows process-introspection backend without verifying it on a modern Windows 11 build (24H2+ removes wmic.exe from the base image). Two-fold defect: (1) introspection backend choice was legacy-only on Windows; (2) collect() remediation logic OR-condition treated count=-1 (introspection failed) the same as count>0 (real sibling leak), producing a false-positive 'Restart IDE' on hosts where the diagnostic itself was unavailable. Lesson: cross-platform introspection backends must have at least one fallback that's part of every modern host's base image (PowerShell Get-CimInstance), and tri-state numeric flags (success/failed/positive-find) must be explicitly differentiated in downstream consumers, not collapsed into truthiness checks.
