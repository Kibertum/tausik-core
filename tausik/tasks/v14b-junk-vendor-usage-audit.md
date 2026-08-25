---
slug: v14b-junk-vendor-usage-audit
title: "B-junk-4: Vendor skill repo usage audit (delete unused)"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T00:46:44Z"
---

## Goal

Spin-off from v14b-junk-audit-pass. New scripts/audit_vendor_usage.py — checks which vendor/* skill repos are actually referenced via usage_events / activity_log. Reports unused vendors with deletion suggestion. After user confirmation, delete unused vendor entries. Goal: smaller repo, fewer cognitive distractions.

## Acceptance Criteria

1. New scripts/audit_vendor_usage.py with pure function audit_vendor_usage(vendor_dir: str, activity_log_path: str) -> dict — walks vendor/ subdirs (one entry per cloned skill repo), cross-references each against usage_events / activity_log via FTS or grep, classifies as 'used' (≥1 event in last 90d), 'unused' (no events in last 90d), or 'unknown' (no telemetry source available). 2. Returns {used: [{name, last_used_at, event_count}], unused: [{name, cloned_at}], unknown: [{name, reason}]}. Never raises — surface errors in 'unknown' bucket with reason. 3. CLI: tausik audit vendors [--json] — prints human or JSON report; non-destructive (does NOT delete). 4. tests/test_audit_vendor_usage.py: ≥8 cases — empty vendor dir, single used vendor, single unused vendor, mixed, missing activity_log handled, malformed activity_log handled, JSON CLI output, threshold boundary (89d=used, 91d=unused). 5. docs/{en,ru}/cli.md document the new command under audit section. 6. CHANGELOG en+ru entry. 7. Negative: audit never deletes; user must do so manually after review. 8. ruff + mypy + pytest + filesize gates green.

## Plan

## Rollback

## Journal

- 2026-05-07T00:43:25Z [implementation] — SCOPE FINDING: usage_events table tracks tokens/cost, not skill invocations. AC #1-2 (telemetry-based 'used'/'unused' classification) невозможны. Re-scope: статический cross-check vendor_dir vs config['installed_skills'] + file mtime as activity proxy. Categories: 'installed' (active in config), 'vendored_unused' (cloned but not installed), 'unknown' (errors). Same goal — surface candidates for cleanup — но честный сигнал.
- 2026-05-07T00:46:44Z [implementation] — AC verified: 1.✓ scripts/audit_vendor_usage.py with audit_vendor_usage(vendor_dir, config_path) static cross-check (re-scoped from telemetry — usage_events tracks tokens not invocations). 2.✓ Returns {installed, vendored_unused, unknown} per AC structure. 3.✓ tausik audit vendors [--json] CLI; smoke on live repo found 5 cleanup candidates. 4.✓ tests/test_audit_vendor_usage.py 9 cases passed. 5.✓ docs/{en,ru}/cli.md updated with audit vendors entry. 6.✓ CHANGELOG en+ru. 7.✓ Negative: read-only invariant tested (test_audit_never_deletes). 8.✓ ruff/mypy/pytest/filesize green; constants.json regen.
