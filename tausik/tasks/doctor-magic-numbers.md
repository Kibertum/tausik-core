---
slug: doctor-magic-numbers
title: "De-magic project_cli_doctor.py session thresholds (280-282)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_config.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_config_knobs.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T11:15:33Z"
---

## Goal

Kill the concentrated magic-number drift trap where the 'doctor' would misreport config: add DEFAULT_SESSION_WARN_THRESHOLD_MINUTES=150 to project_config.py (no named constant exists), and replace the three inlined defaults at project_cli_doctor.py:280-282 (150 warn, 10 idle, 600 cache TTL) with the existing/new constants — the same function already imports DEFAULT_SESSION_MAX_MINUTES, proving the pattern.

## Acceptance Criteria

1. A named constant DEFAULT_SESSION_WARN_THRESHOLD_MINUTES=150 is defined next to the sibling session constants in project_config.py WITHOUT pushing the file over the 400-line cap (reclaim a line if needed — the file is exactly at 400). 2. project_cli_doctor.py:280-282 use named constants: warn→DEFAULT_SESSION_WARN_THRESHOLD_MINUTES, idle→DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES (already exists), ttl→DEFAULT_CACHE_TTL_S (verify_constants, already imported pattern). 3. No inline 150/10/600 magic literals remain in that doctor Config-knobs block. 4. NEGATIVE/EDGE: doctor output for a default config is byte-identical (same 150/10/600 values surface); filesize gate stays green (project_config.py ≤400). 5. Existing doctor tests still pass.

## Plan

## Rollback

## Journal

- 2026-07-26T11:15:25Z [implementation] — AC verified: 1. ✓ DEFAULT_SESSION_WARN_THRESHOLD_MINUTES=150 added to project_config.py net-zero (tightened adjacent comments) — file still 400 lines (at cap, not over). 2. ✓ project_cli_doctor.py:280-282 now use DEFAULT_SESSION_WARN_THRESHOLD_MINUTES / DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES / DEFAULT_CACHE_TTL_S (imported from project_config + verify_constants). 3. ✓ No inline 150/10/600 literals remain in the Config-knobs block. 4. ✓ NEGATIVE: values resolve to exactly (150,10,600) — doctor output byte-identical; filesize gate green (both files=400≤400); test_config_knobs 9/9 + 69 doctor tests pass. Verify #1352. Domain: bumping a session default now updates the doctor's reported value too — no more silent drift where the 'doctor' misreports config.
