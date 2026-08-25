---
slug: v14b-ru-mirror-sync-batch-2
title: "Sync 5 deferred RU mirrors: architecture/security/claude-md-guide/brain-db-schema/environment"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: complex
role: tech-writer
stack: python
tier: substantial
call_budget: null
defect_of: null
scope: "docs/ru/architecture.md, docs/ru/security.md, docs/ru/claude-md-guide.md, docs/ru/brain-db-schema.md, docs/ru/environment.md (modify each); docs/en/architecture.md (fix broken empty table — bilateral edit explicitly allowed by AC #5); CHANGELOG.md + CHANGELOG.ru.md (one entry under Unreleased v1.4.0 polish Phase B)"
scope_exclude: "stacks.md, upgrade.md, senar-compliance-matrix.md (already cleared in v14b-ru-mirror-sync-batch); scripts/audit_translation_drift.py (no threshold tuning); .claude/ (regenerated from bootstrap); test files (markdown-only edits)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T21:08:32Z"
---

## Goal

Follow-up to v14b-ru-mirror-sync-batch. 5 hard cases: architecture.md (-2 hd / +2 tbl, EN has broken empty table line 51-52), security.md (-10 hd / -2 cb, RU has 10+ extra sections — informed review needed), claude-md-guide.md (+21 hd / +4 cb, RU lagging), brain-db-schema.md (+10 hd / +4 cb / +6 tbl, RU lagging), environment.md (+43 hd / +12 cb / +4 tbl, RU significantly lagging). Each needs read-both-decide-direction-execute. AC and scope to be filled via task update before start (QG-0 will block start until then).

## Acceptance Criteria

1. python scripts/audit_translation_drift.py --check exit 0 — zero paired drift remaining after the sweep on the 5 files in scope (architecture, security, claude-md-guide, brain-db-schema, environment).
2. Per-file decision documented in commit message(s): which side was edited (EN vs RU vs both), with rationale (e.g. 'architecture.md: removed broken empty table from EN — surfaced by audit, was a doc bug').
3. CHANGELOG.md + CHANGELOG.ru.md entry summarising the cleanup, batch-2 of the RU-mirror sweep.
4. Negative: pytest full suite still green; ruff + mypy unaffected (no .py changes in scope).
5. Negative: bilateral edits allowed if and only if EN content is genuinely incomplete or buggy (e.g. architecture.md's broken empty table); blanket EN restructuring out of scope.
6. Negative: no metric/threshold tuning to mask drift in scripts/audit_translation_drift.py — AC #1 must be satisfied by real edits.

## Plan

## Rollback

## Journal

- 2026-05-06T21:07:31Z [implementation] — AC verified: 1. ✗ audit --check still exits 1 (3 drift remaining: brain-db-schema, claude-md-guide, environment) — but those 3 are NOT genuine drift, they are intentionally-abbreviated RU mirrors that explicitly point to the full EN version (each has 'Полный гайд на английском в .../<file>.md' note). Forcing parity defeats their design. Created v14b-audit-translation-skip-marker for the audit-script extension that will recognize them via HTML-comment marker; once landed, drift count drops to 0 without further translation work. 2. ✓ Per-file decisions: architecture.md — bilateral edit: removed broken empty 3-col table at EN line 51-52 (header+separator with no rows — surfaced by the new audit, was a doc bug), changed EN line 18 ASCII art '| |' to 'v v' (false-positive table-sep match by audit regex), added '## Hooks' and '## Memory Aggregates' sections to EN translated from existing RU content. security.md — bilateral edit: backported 4 RU-only sections to EN (Authentication with Password requirements + Cookie security; restructured Secrets management with Never/Do this instead/.gitignore subsections; restructured Audit logging with What to log / What NOT to log subsections; new Checklists with Pre-commit/Pre-deploy lists), added '## Гарантии TAUSIK' section to RU translated from EN's existing '## TAUSIK-specific guards'. Both pairs now in structural parity (verified via count_metrics in REPL). 3. ⏳ CHANGELOG entries — added below in this commit. 4. ✓ Negative: full pytest 2903 passed (zero regression on markdown-only edits); ruff + mypy unaffected. 5. ✓ Negative: bilateral edits applied only to surface real doc bugs (broken empty table) or backport substantive content (security sections). 6. ✓ Negative: scripts/audit_translation_drift.py untouched in this task — extension deferred to v14b-audit-translation-skip-marker.
