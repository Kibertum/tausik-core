---
slug: remove-four-trailing-spaces-from-generated
title: "Remove four trailing spaces from generated instruction blocks"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "`AGENTS.md`, `CLAUDE.md`: dynamic blocks only; remove the four observed trailing ASCII spaces."
scope_exclude: "No other generated text, no release input edits, no code, no commit/push/tag/release."
relevant_files:
  - AGENTS.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T11:17:29Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Remove exactly the four trailing-space defects in the generated dynamic memory-tail lines of AGENTS.md and CLAUDE.md without changing their text or other worktree content.

## Acceptance Criteria

AC-1 AGENTS.md lines for decisions #420 and #418 have no trailing whitespace. AC-2 CLAUDE.md mirrors those two cleaned lines. AC-3 git diff --check reports no trailing-whitespace errors for AGENTS.md or CLAUDE.md. Negative: decision text, dynamic-block structure, and unrelated dirty files remain unchanged.

## Plan

## Rollback

## Journal

- 2026-10-04T11:15:49Z [implementation] — Implementation: removed exactly four trailing ASCII spaces: decisions #420 and #418 in AGENTS.md, mirrored in CLAUDE.md. Validation: `git diff --check -- AGENTS.md CLAUDE.md` reports no whitespace errors; explicit scan found 0 trailing-space lines; mirrored decision-line comparison found 2+2 equal lines. No other text or dirty files was modified by this task.
- 2026-10-04T11:16:22Z [implementation] — Verification note: tausik_verify #3455 passed 6 non-test gates and skipped ruff/pytest because the MCP task_update surface cannot declare relevant_files (the server explicitly refused that field). This whitespace-only generated-doc cleanup has no behavioral test mapping; domain evidence is the byte-level trailing-whitespace scan and git diff --check recorded above. The skipped tests are not represented as proof.
- 2026-10-04T11:16:42Z [implementation] — AC-1: VERIFIED — AGENTS.md decisions #420 and #418 no longer end in ASCII whitespace; explicit scan found zero trailing-space lines. AC-2: VERIFIED — CLAUDE.md contains the same two cleaned decision lines; Compare-Object over the two selected lines returned no differences and each file had exactly two matches. AC-3: VERIFIED — `git diff --check -- AGENTS.md CLAUDE.md` emitted no whitespace defect. Domain: live worktree files were read after the edit. Negative: patch removed one terminal space from exactly four lines and changed no decision text or dynamic-block structure; all unrelated dirty files were preserved. Verification #3455: 6 non-test gates passed, ruff/pytest skipped; those skips are explicitly not claimed as evidence because this is a whitespace-only generated-doc cleanup with no behavioral test mapping.
- 2026-10-04T11:16:56Z [implementation] — AC verified: AC-1: ✓ AGENTS.md decisions #420 and #418 have no trailing whitespace; explicit scan found 0 lines. AC-2: ✓ CLAUDE.md mirrors the two cleaned lines; Compare-Object returned no difference and counts are 2+2. AC-3: ✓ `git diff --check -- AGENTS.md CLAUDE.md` emitted no whitespace defect. Domain: checked the live worktree bytes after the edit. Negative: exactly four terminal ASCII spaces were removed; decision text, dynamic-block structure, and unrelated dirty files remain unchanged. Verify #3455 passed 6 non-test gates; ruff and pytest were skipped and are not claimed as evidence.
