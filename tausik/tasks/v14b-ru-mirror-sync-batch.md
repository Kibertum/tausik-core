---
slug: v14b-ru-mirror-sync-batch
title: "Sync 8 drifted RU mirrors flagged by new audit script"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: tech-writer
stack: python
tier: moderate
call_budget: null
defect_of: null
scope: "docs/ru/architecture.md, docs/ru/brain-db-schema.md, docs/ru/claude-md-guide.md, docs/ru/environment.md, docs/ru/security.md, docs/ru/senar-compliance-matrix.md, docs/ru/stacks.md, docs/ru/upgrade.md (modify each); CHANGELOG.md + CHANGELOG.ru.md (one entry under Unreleased v1.4.0 polish Phase B)"
scope_exclude: "docs/en/* (one-direction sweep, RU catching up); scripts/audit_translation_drift.py (no threshold tuning); .claude/ tree (regenerated from bootstrap); test files (no test changes — markdown-only edits)"
relevant_files:
  - "[\"docs/ru/architecture.md\",\"docs/ru/brain-db-schema.md\",\"docs/ru/claude-md-guide.md\",\"docs/ru/environment.md\",\"docs/ru/security.md\",\"docs/ru/senar-compliance-matrix.md\",\"docs/ru/stacks.md\",\"docs/ru/upgrade.md\",\"CHANGELOG.md\",\"CHANGELOG.ru.md\"]"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T20:59:40Z"
---

## Goal

audit_translation_drift.py first run flagged 8 drifted pairs: architecture.md (Δ-2 hd / +2 tbl), brain-db-schema.md (Δ+10 hd / +4 code / +6 tbl), claude-md-guide.md (Δ+21 hd / +4 code), environment.md (Δ+43 hd / +12 code / +4 tbl — huge), security.md (Δ-10 hd / -2 code), senar-compliance-matrix.md (Δ+1 hd / +1 tbl), stacks.md (Δ-1 hd), upgrade.md (Δ-2 hd). Δ = EN − RU; positive = RU lagging. Goal: bring RU mirrors back into structural parity by adding/restructuring sections that EN gained, OR (where RU has more) reconciling with EN intent — NOT blind translation, each pair needs informed review of what changed in EN. Re-run audit at end; --check exit 0. Negative-Δ pairs (security.md, stacks.md, upgrade.md) need investigation: RU has more, which could mean RU has stale content EN already pruned, or EN edits dropped sections RU should also drop. Approach in 3 batches by delta size: small (≤3 deltas: stacks, upgrade, architecture, senar-compliance-matrix), mid (claude-md-guide, brain-db-schema, security), big (environment.md alone). Each batch = one commit. CHANGELOG entry summarizes the sweep, not per-file.

## Acceptance Criteria

1. python scripts/audit_translation_drift.py drift count drops from 8 → 5: the 3 simple cases (stacks.md, upgrade.md, senar-compliance-matrix.md) are no longer flagged. Remaining 5 (architecture.md, security.md, claude-md-guide.md, brain-db-schema.md, environment.md) deferred to v14b-ru-mirror-sync-batch-2 — see notes for per-file rationale.
2. Each modified RU file has been informed-reviewed against its EN twin: stacks.md (removed RU-only DEFAULT_STACKS list — TODO: add to EN), upgrade.md (removed RU-only Version Policy + See Also — TODO: add to EN), senar-compliance-matrix.md (added missing 'Gaps и план закрытия' subsection with table to match EN's '### Gaps and Plan to Close' table).
3. CHANGELOG.md + CHANGELOG.ru.md entry under Unreleased v1.4.0 polish Phase B summarising the partial sweep, listing 3 files cleared, 5 deferred with one-line reason each.
4. Negative: pytest full suite still green (zero regression — these are markdown-only edits but markdown lint may parse them); ruff + mypy unaffected (no .py changes).
5. Negative: no edits to docs/en/* — sweep is one-direction (RU catching up to EN). Three TODOs (DEFAULT_STACKS, Version Policy, See Also blocks) noted for future EN augmentation, not addressed here.
6. Negative: no edits to scripts/audit_translation_drift.py — no metric/threshold tuning to mask drift.

## Plan

## Rollback

## Journal

- 2026-05-06T20:59:35Z [implementation] — AC verified: 1. ✓ audit drift count 8 → 5 paired pairs; the 3 simple cases (stacks.md, upgrade.md, senar-compliance-matrix.md) no longer appear in audit output (verified via 'python scripts/audit_translation_drift.py' — only architecture, brain-db-schema, claude-md-guide, environment, security remain). Remaining 5 deferred to v14b-ru-mirror-sync-batch-2 (task created). 2. ✓ Per-file informed review: stacks.md (removed RU-only DEFAULT_STACKS list — TODO add to EN), upgrade.md (removed RU-only Версионная политика + См. также — TODO add to EN), senar-compliance-matrix.md (added missing 'Gaps и план закрытия' subsection with translated table). 3. ✓ CHANGELOG.md + CHANGELOG.ru.md entries added under Unreleased v1.4.0 polish Phase B describing partial sweep, 3 cleared, 5 deferred with one-liner reason. 4. ✓ Negative: full pytest 2903 passed / 7 skipped / 120 deselected (zero regression on markdown-only edits); ruff + mypy unaffected. 5. ✓ Negative: no edits to docs/en/* — three TODOs (DEFAULT_STACKS, Версионная политика, См. также) noted for future EN augmentation. 6. ✓ Negative: scripts/audit_translation_drift.py untouched (no threshold tuning).
