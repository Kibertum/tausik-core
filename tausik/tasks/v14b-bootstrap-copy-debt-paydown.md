---
slug: v14b-bootstrap-copy-debt-paydown
title: "v1.4 polish Phase B: split bootstrap/bootstrap_copy.py 420→sub-400 (extract skill helpers)"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "bootstrap/bootstrap_copy.py (extract), bootstrap/bootstrap_skill_helpers.py (new), CHANGELOG.md, CHANGELOG.ru.md, plus any test/import that needs updating."
scope_exclude: "scripts/service_gates.py, scripts/brain_init.py, harness/* runtime — those are separate filesize-debt tasks. Do NOT touch verify_cache, gates, or QG-2 internals."
relevant_files:
  - "bootstrap/bootstrap_copy.py"
  - "bootstrap/bootstrap_skill_helpers.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T19:34:49Z"
---

## Goal

Reduce bootstrap/bootstrap_copy.py from 420 lines to under 400-line filesize gate by extracting skill-specific helpers (frontmatter parser/validator, _resolve_skill, _generate_stub, _load_registry) into a new bootstrap_skill_helpers.py module. Behaviour byte-for-byte identical — bootstrap output (file copies, stub contents, validation warnings) must not change.

## Acceptance Criteria

1. bootstrap/bootstrap_copy.py < 400 lines after split. 2. New module bootstrap/bootstrap_skill_helpers.py contains parse_skill_frontmatter, validate_skill_frontmatter, _resolve_skill, _generate_stub, _load_registry, VALID_CONTEXT, VALID_EFFORT (and re-exports them so external imports keep working). 3. All existing pytest tests for bootstrap module pass with no behaviour change. 4. Bootstrap actually runs (`python .tausik-lib/bootstrap/bootstrap.py --init` or equivalent) on this repo and produces byte-identical .claude/ output vs pre-split (no regressions in skill copy, stub generation, registry loading). 5. Filesize gate passes (filesize_gate.py reports ≤400 for both files). 6. CHANGELOG entry added under Unreleased v1.4.0 polish Phase B. NEGATIVE: 7. parse_skill_frontmatter on a file with no `---` block still returns None (not raises). 8. validate_skill_frontmatter on invalid context/effort still returns warning strings (not raises). 9. _resolve_skill for a missing skill still returns (None, "missing"). 10. If bootstrap_skill_helpers.py is missing or import fails, bootstrap_copy.py raises a clear ImportError at module load time (no silent fallback).

## Plan

## Rollback

## Journal

- 2026-05-06T19:33:08Z [implementation] — Split done: bootstrap_copy.py 420→311 (-109), bootstrap_skill_helpers.py 139 NEW. Re-export pattern preserves all external imports (skill_profile.py, test_bootstrap_frontmatter.py, test_vendor.py, test_v13_hardening.py, test_copy_symlinks_disabled.py). 76 bootstrap-related tests pass. Filesize gate PASS for both files.
- 2026-05-06T19:34:49Z [implementation] — AC verified: 1. ✓ wc -l bootstrap/bootstrap_copy.py = 311 (was 420, -109 lines) 2. ✓ bootstrap/bootstrap_skill_helpers.py 139 lines NEW; contains parse_skill_frontmatter+validate_skill_frontmatter+_resolve_skill+_generate_stub+_load_registry+VALID_CONTEXT+VALID_EFFORT; bootstrap_copy.py re-exports them via `from bootstrap_skill_helpers import (...) # noqa: F401`. hasattr smoke test confirmed all 16 names accessible via bootstrap_copy module. 3. ✓ pytest tests/test_bootstrap_frontmatter.py tests/test_vendor.py tests/test_v13_hardening.py tests/test_copy_symlinks_disabled.py: 71/71 passed in 1.10s. Bigger sweep including non_destructive: 76/76 passed in 1.34s. 4. ✓ python bootstrap/bootstrap.py --ide claude --smart re-run after split — git status shows ZERO .claude/ diffs. Skills: 13 copied; Scripts: 111; MCP: 3; Refs: 6; Roles: 5; Stacks: 1 — same as pre-split. 5. ✓ run_filesize_gate({max_lines: 400}, [bootstrap_copy.py, bootstrap_skill_helpers.py]) → PASS ("All files within line limit."). 311 ≤ 400 and 139 ≤ 400. 6. ✓ CHANGELOG.md and CHANGELOG.ru.md: new "Filesize debt paydown: bootstrap/bootstrap_copy.py 420 → 311" entry inserted at top of "Changed" section under [Unreleased] — v1.4.0 polish (Phase B). Both files in sync. 7. ✓ Negative parse: tests/test_bootstrap_frontmatter.py::TestParseFrontmatter::test_no_frontmatter (file with no `---` block returns None) and ::test_missing_file (nonexistent path returns None) — both green post-split. 8. ✓ Negative validate: same test file covers invalid context/effort cases via TestValidateFrontmatter — returns warning list, never raises. All passed post-split. 9. ✓ Negative resolve: _resolve_skill in bootstrap_skill_helpers.py preserves the (None, "missing") return when skill not found in builtin/adjacent/vendor — code is byte-identical to the pre-split version (verified via diff). 10. ✓ If bootstrap_skill_helpers.py is missing or fails to import, the top-level `from bootstrap_skill_helpers import (...)` in bootstrap_copy.py raises ImportError at module load — Python default behaviour, no try/except wrapper added. Confirmed by reading bootstrap_copy.py:11-21.
