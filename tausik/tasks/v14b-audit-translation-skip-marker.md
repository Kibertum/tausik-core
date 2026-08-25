---
slug: v14b-audit-translation-skip-marker
title: "Audit skip-marker for intentionally abbreviated RU mirrors"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: "scripts/audit_translation_drift.py (modify); tests/test_audit_translation_drift.py (extend); docs/ru/claude-md-guide.md, docs/ru/brain-db-schema.md, docs/ru/environment.md (insert marker only); CHANGELOG.md + CHANGELOG.ru.md (entry)"
scope_exclude: "docs/en/* (no EN edits in this task); docs/ru/{stacks,upgrade,senar-compliance-matrix,architecture,security}.md (already cleared in batches 1-2); .claude/ (regenerated)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T21:15:23Z"
---

## Goal

v14b-ru-mirror-sync-batch-2 surfaced 3 RU mirrors that are intentionally-abbreviated overviews of the full English doc: claude-md-guide.md, brain-db-schema.md, environment.md. All three explicitly say 'Полный гайд на английском в .../<file>.md' and point readers to the EN version. Bringing them to structural parity with EN defeats their purpose. Plus: regex matches inside fenced code blocks produce false-positive heading drift (EN claude-md-guide.md has many markdown\n# BAD\n## Auth\n examples with #-prefixed lines INSIDE code fences that the audit counts as headings). Two improvements needed: (a) audit script honors a <!-- audit-translation-drift: skip --> HTML-comment marker — pairs with marker shown in a separate 'intentionally abbreviated' section, not counted as drift; (b) regex for headings tracks fenced-code-block context — lines inside  not counted as headings. After these two improvements, run audit again on these 3 pairs — expect drift count drops to 0.

## Acceptance Criteria

1. scripts/audit_translation_drift.py extended with two improvements: (a) honors HTML-comment marker '<!-- audit-translation-drift: skip -->' (or similar) anywhere in either EN or RU file of a pair — pairs with the marker NOT counted as drift, listed in a separate 'Intentionally abbreviated' section in the report; (b) heading regex tracks fenced code-block context — lines inside triple-backtick fences (```...```) NOT counted as headings.
2. tests/test_audit_translation_drift.py extended with at least 4 new cases: (a) skip-marker in RU file → pair NOT in drift list, IS in abbreviated list; (b) skip-marker in EN file → same; (c) heading inside fenced code block → not counted; (d) heading after closing fence → still counted.
3. Markers added to the 3 abbreviated RU mirrors that explicitly say 'Полный гайд на английском в .../<file>.md': docs/ru/claude-md-guide.md, docs/ru/brain-db-schema.md, docs/ru/environment.md. Place marker right after the title block.
4. python scripts/audit_translation_drift.py --check exit 0 after the changes — zero paired drift. The 3 abbreviated mirrors appear in the new 'Intentionally abbreviated' section instead.
5. CHANGELOG.md + CHANGELOG.ru.md entry under Unreleased v1.4.0 polish Phase B describing the two improvements + final audit state.
6. Negative: pytest full suite green (the existing 14 tests + new ones); ruff + mypy clean on scripts/audit_translation_drift.py + tests; no test relaxed to mask the extension.
7. Negative: marker placement does NOT alter the rendered RU output noticeably — HTML comment is invisible in markdown render. No content changes to the 3 abbreviated docs (only marker insertion).

## Plan

## Rollback

## Journal

- 2026-05-06T21:15:18Z [implementation] — AC verified: 1. ✓ scripts/audit_translation_drift.py extended: (a) _SKIP_MARKER_RE regex + has_skip_marker() helper detect HTML-comment marker '<!-- audit-translation-drift: skip -->' anywhere in EN or RU file; (b) _FENCED_BLOCK_RE + _strip_fenced_blocks() helper strips fenced code blocks before count_metrics() counts headings (code_blocks and tables still on raw text). audit_pairs() returns 4-tuple (drifts, en_only, ru_only, abbreviated); render_markdown/render_json accept new optional abbreviated arg. 2. ✓ tests/test_audit_translation_drift.py: +7 cases — has_skip_marker shape (with/without spaces / negatives), count_metrics_ignores_headings_inside_code_fence, skip_marker_in_ru_excludes_pair, skip_marker_in_en_excludes_pair, main_check_exits_zero_with_only_abbreviated_pairs, render_markdown_lists_abbreviated_section, heading_after_closing_fence_still_counted. 21/21 PASS. 3. ✓ Markers inserted in docs/ru/claude-md-guide.md, docs/ru/brain-db-schema.md, docs/ru/environment.md right after the title-block link line, before the # heading. HTML comment is invisible in rendered markdown. 4. ✓ python scripts/audit_translation_drift.py --check exit 0 — output shows 'No structural drift detected on paired mirrors. (OK)' + 'Intentionally abbreviated' section listing all 3 pairs. 5. ✓ CHANGELOG.md + CHANGELOG.ru.md entries added under Unreleased v1.4.0 polish Phase B describing both improvements + final audit state. 6. ✓ Negative: full pytest 2903→2910 passed (+7 new, zero regression); ruff + mypy clean on scripts + tests; no test relaxed to mask the extension (drift on non-marked pairs still detected, verified by retained 14 original tests). 7. ✓ Negative: marker is HTML comment — invisible in rendered markdown (verified by visual inspection of file structure); zero content changes to the 3 abbreviated docs (only marker insertion). Final audit state: 0 paired drift, 3 abbreviated, 4 EN-only + 1 RU-only — full v14b sweep closed.
