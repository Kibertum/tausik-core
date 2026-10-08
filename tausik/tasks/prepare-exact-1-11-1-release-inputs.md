---
slug: prepare-exact-1-11-1-release-inputs
title: "Prepare exact 1.11.1 release inputs"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "`CHANGELOG.md`, `CHANGELOG.ru.md`, `pyproject.toml`, `scripts/tausik_version.py`, `README.md`, `README.ru.md`, `docs/_generated/constants.json`, `docs/en/whats-new-1.11.md`, `docs/ru/whats-new-1.11.md`, `release-body-1.11.1.md`, and directly aligned tests/generated documentation."
scope_exclude: "No implementation feature work; no economy acceptance closure; no commit, push, tag, GitHub/GitLab release, tracker mutation, or site deployment."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - pyproject.toml
  - "scripts/tausik_version.py"
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
  - release-body-1.11.1.md
scope_paths: []
scope_tools: []
assurance_profiles:
  - declarative
assurance_impact: "{\"blast_radius\":\"bounded\",\"data_change\":\"none\",\"governance_boundary\":false,\"level\":\"medium\",\"owner_escalation\":false,\"privileged\":false,\"reversibility\":\"reversible\",\"security_boundary\":false}"
depends_on: []
completed_at: "2026-10-04T11:29:43Z"
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

Leave a coherent, reviewable 1.11.1 release-input set without committing, tagging, publishing, or claiming the blocked economy acceptance.

## Acceptance Criteria

AC-1 EN and RU changelogs retain an empty [Unreleased] heading and move the current entries under [1.11.1] dated 2026-10-04 with mirrored meaning. AC-2 runtime, package metadata, README badges, and generated constants report exactly 1.11.1. AC-3 both whats-new pages link the immutable v1.11.1 paths. AC-4 a saved English GitHub release body names 1.11.1, links both EN/RU whats-new pages at v1.11.1, and passes `tausik publish notes --version 1.11.1`. AC-5 focused release/version/docs tests, pytest dedupe audit, and task-scoped tausik_verify pass with denominators. Negative: no commit, push, tag, release, synthetic benchmark, savings claim, or closure of r111-economy-hardening-acceptance.

## Plan

## Rollback

Revert only this task's version, changelog-heading, links, generated constants, release-body, and aligned-test changes while preserving all other dirty worktree content.

## Journal

- 2026-10-04T11:21:50Z [implementation] — Implementation: folded the current bilingual [Unreleased] entries under [1.11.1] — 2026-10-04 while retaining empty [Unreleased]; set pyproject/runtime/generated constants/README badges to 1.11.1; pinned both whats-new pages to immutable v1.11.1 EN/RU links; saved release-body-1.11.1.md with the same links and an explicit no-savings-claim boundary. Focused tests: 111 passed in 10.92s across test_release_notes.py, test_gen_doc_constants.py, test_publication_lines.py, test_update_check.py. Dedupe audit: 0 copy, 282 parallel groups; no duplicate-test defect. Idempotence/postconditions: second gen_doc_constants.py --write changed no selected hashes; --check passed; source CLI prints TAUSIK 1.11.1; publish notes accepts the saved body.
- 2026-10-04T11:22:05Z [implementation] — AC verified: AC-1: ✓ CHANGELOG.md and CHANGELOG.ru.md each have empty [Unreleased] followed by [1.11.1] — 2026-10-04; the six release bullets remain bilingual mirrors. AC-2: ✓ `scripts/project.py --version` prints `TAUSIK 1.11.1`; pyproject.toml, scripts/tausik_version.py, README badges and generated constants all carry 1.11.1; constants --check passes. AC-3: ✓ both whats-new pages contain immutable v1.11.1 links for EN and RU pages; no v1.11.0 remains on the inspected release surfaces. AC-4: ✓ release-body-1.11.1.md names 1.11.1, states that no savings claim is made, contains both immutable links, and publish-notes validation returns OK. AC-5: ✓ focused lane 111 passed; audit_pytest_dedupe reports 0 copy groups; task-scoped tausik_verify remains to be recorded. Behavior: the release validator accepts the actual saved body. Idempotence: a second generator --write preserved hashes. Postconditions: exact-version and stale-link searches pass. Rollback: only the named release inputs need reversal. Negative: no commit, push, tag, release, benchmark, savings claim, or economy-acceptance state change occurred.
- 2026-10-04T11:23:22Z [implementation] — Dead end: bootstrap without --ide all refreshed only Claude and left five deployed profiles stale; bootstrap --ide all is required for a release version bump. MCP self-check then correctly detected tausik_version.py drift, so all remaining governance calls use CLI fallback until IDE restart.
- 2026-10-04T11:24:06Z [implementation] — AC verified final: AC-1 ✓ bilingual [Unreleased] is empty and [1.11.1] is dated 2026-10-04. AC-2 ✓ exact 1.11.1 across runtime/package/badges/constants; source CLI prints TAUSIK 1.11.1. AC-3 ✓ both whats-new pages pin EN/RU links to v1.11.1 with no stale v1.11.0 on release surfaces. AC-4 ✓ saved release-body-1.11.1.md names 1.11.1, links both pages, states no savings claim, and publish-notes accepts it. AC-5 ✓ focused 111 passed; dedupe 0 copy; verify #3459 passed 444, skipped 16 over 10/659 mapped test files, 8 gates passed, hadolint skipped as non-applicable evidence. Behavior/idempotence/postconditions/rollback and negative boundaries were checked; no commit, push, tag, release, synthetic benchmark, savings claim or economy-acceptance closure occurred.
- 2026-10-04T11:28:46Z [implementation] — Review iteration 1: bounded fresh-context review found 0 critical, 0 high, 2 medium. Fixed both: README EN/RU now lead with 1.11, and release body distinguishes the exact 1.11.1 changelog from the bilingual 1.11-series overview. Revalidation: 111 passed; constants check and publish-notes passed; review gate passed over 10/659 mapped files.
- 2026-10-04T11:29:39Z [implementation] — AC verified final after review fixes: AC-1 ✓ empty bilingual [Unreleased] plus [1.11.1] dated 2026-10-04. AC-2 ✓ exact 1.11.1 across source/package/badges/constants. AC-3 ✓ immutable v1.11.1 EN/RU whats-new links. AC-4 ✓ saved body distinguishes exact 1.11.1 changelog from 1.11 overview, retains both language links, rejects a savings claim, and passes publish-notes. AC-5 ✓ focused 111 passed; dedupe 0 copy; L2 review #57 recorded with both medium findings fixed; verify #3461 passed 444, skipped 16 over 10/659 mapped files, 8 gates passed, hadolint skipped and not claimed. Negative boundaries unchanged.
