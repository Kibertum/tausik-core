---
slug: v14b-en-mirror-backport-batch-1
title: v14b-en-mirror-backport-batch-1
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/en/stacks.md, docs/en/upgrade.md, docs/ru/stacks.md, docs/ru/upgrade.md"
scope_exclude: "scripts/*, tests/*, docs/ru/architecture.md, docs/ru/security.md, docs/ru/claude-md-guide.md, docs/ru/brain-db-schema.md, docs/ru/environment.md"
relevant_files:
  - "docs/en/stacks.md"
  - "docs/en/upgrade.md"
  - "docs/ru/stacks.md"
  - "docs/ru/upgrade.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T21:37:01Z"
---

## Goal

Backport DEFAULT_STACKS (25) section to docs/en/stacks.md and Version Policy + See Also sections to docs/en/upgrade.md to clear two carry-over TODOs from session #62 handoff and reduce translation drift count.

## Acceptance Criteria

1. docs/en/stacks.md has new "## DEFAULT_STACKS (25)" section listing all 25 built-in stacks (mirror of removed RU section) before the "## See also" block.
2. docs/en/upgrade.md has new "## Version Policy" section (semver patch/minor/major rules + tausik doctor pointer) AND "## See Also" section (cross-link to customization + architecture) appended after "## Disaster recovery".
3. scripts/audit_translation_drift.py reports stacks.md and upgrade.md as parity (drift count for those two files = 0).
4. pytest tests/test_audit_translation_drift.py passes (script regression suite).
5. ruff + mypy clean (no Python source changes anyway, but gates must pass).

## Plan

## Rollback

## Journal

- 2026-05-06T21:35:49Z [implementation] — Edited docs/en/stacks.md (added DEFAULT_STACKS list before "## See also") and docs/en/upgrade.md (added "## Version Policy" + "## See Also" after Disaster recovery). Markdown-only changes; no code touched. Security AC warning N/A — pure documentation backport, no threat surface.
- 2026-05-06T21:36:44Z [implementation] — Restored DEFAULT_STACKS (1 hd) to docs/ru/stacks.md and Версионная политика + См. также (2 hd) to docs/ru/upgrade.md. Pairs now structurally identical. audit_translation_drift.py --check exit=0, "No structural drift detected on paired mirrors. (OK)".
- 2026-05-06T21:37:01Z [implementation] — AC verified: 1. ✓ docs/en/stacks.md +6 lines: '## DEFAULT_STACKS (25)' section + 25-stack list inserted before '## See also' (lines 92-96) 2. ✓ docs/en/upgrade.md +13 lines: '## Version Policy' (semver patch/minor/major + tausik doctor pointer) + '## See Also' (Customization + Architecture cross-links) appended after Disaster recovery 3. ✓ python scripts/audit_translation_drift.py --check exit=0; report: 'No structural drift detected on paired mirrors. (OK)' (after parallel restore of same sections to docs/ru/stacks.md and docs/ru/upgrade.md to maintain parity) 4. ✓ pytest tests/test_audit_translation_drift.py — 21 passed in 0.23s 5. ✓ No Python source touched; ruff+mypy gates run by service_gates.py via verify pipeline (cache hit, exit=0)
