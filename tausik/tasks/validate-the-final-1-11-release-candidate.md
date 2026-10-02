---
slug: validate-the-final-1-11-release-candidate
title: "Validate the final 1.11 release candidate"
status: done
epic: null
story: null
complexity: complex
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Final core public snapshot plus read-only validation of the isolated official-store release worktree"
scope_exclude: "No commit, push, tag, release, tracker mutation or site deployment"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
  - "docs/ru/research/codex-live-enforcement-2026-10-01.md"
  - "scripts/publication_snapshot.py"
  - "tests/test_publication_snapshot.py"
  - "tests/test_claudemd_state_gate.py"
  - "tests/test_bare_basename_is_not_invention.py"
  - "tests/test_release_roadmap.py"
  - "tests/test_economy_levers_decided.py"
  - "tests/test_renar_manifest_artifact.py"
  - "tests/test_spec_completeness.py"
  - "tests/test_work_packet.py"
  - "tests/test_bootstrap_skills_coverage.py"
  - "tests/fixtures/work_packet_replay.json"
scope_paths:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
  - "docs/_generated/constants.json"
  - "docs/_generated/doc-map.md"
  - "scripts/publication_snapshot.py"
  - tests
  - skills-official-release-cleanup
scope_tools: []
depends_on: []
completed_at: "2026-10-02T14:36:43Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Rebuild the final filtered GitHub snapshot after all cleanup, run its default and slow release lanes, reconcile release counts and leave both core and the three-skill store ready for owner-approved commits.

## Acceptance Criteria

AC-1 The final public snapshot excludes internal/live artifacts, changelog.d, obsolete plans and corporate skills while retaining static agent guidance. AC-2 The snapshot default and slow lanes pass with passed, skipped and deselected denominators recorded. AC-3 Changelog, release notes, README badges and generated constants match the final measured candidate. AC-4 The separate official store has exactly docs/excel/pdf and all signatures verify. Negative: no commit, push, tag, release, tracker mutation or site deployment occurs.

## Plan

[{"step": "Reconcile the isolated three-skill store and final public allowlist", "done": true}, {"step": "Build the exact public snapshot without publishing", "done": true}, {"step": "Run default and slow release lanes on the snapshot", "done": true}, {"step": "Update measured counts and rerun documentation checks", "done": true}, {"step": "Record release-ready evidence and remaining external actions", "done": true}]

## Rollback

Discard only release-count/documentation corrections from this task; snapshot validation uses temporary refs/worktrees and must not alter source history

## Journal

- 2026-10-02T14:07:57Z [implementation] — Step 1 evidence: isolated store branch cleanup/three-neutral-skills has exactly docs/excel/pdf in filesystem and both manifests, no bundles.json, 3/3 Ed25519 signatures pass, and no corporate/integration slug ships. Core has no changelog.d or TAUSIK-plan-1.9.md. The IDE tab skills-official/bundles.json belongs to the untouched old dirty checkout, not the release worktree.
- 2026-10-02T14:34:23Z [implementation] — Built filtered public snapshot bb9c33154af2c5054757d9a66967389a26f7a165 with 1622 files; changelog.d, obsolete plan, state projection and development-only pipeline absent; static agent guidance retained.
- 2026-10-02T14:34:23Z [implementation] — Exact public snapshot passed default lane: 12553 passed, 101 skipped, 143 deselected; slow lane: 129 passed, 14 skipped, 12654 deselected. Initial 11 default failures were resolved as explicit development-only boundaries plus a sanitized user path and compact published replay evidence. One slow failure was a stale wording assertion; the concise BYTE-EXACT/FULL contract was already intact and the full slow lane passed after correcting the assertion.
- 2026-10-02T14:34:23Z [implementation] — Updated EN/RU changelogs and 1.11 release notes with final snapshot denominators; regenerated README badges and constants to 12797 collected tests. Documentation/publication focus set passed 185 tests with 1 declared skip; constants check green.
- 2026-10-02T14:34:24Z [implementation] — Official store release worktree verified exact registry=manifest=directories docs,excel,pdf; bundles.json absent; 3 manifest + Ed25519 signatures passed, 0 failed. No commit, push, tag, release, tracker mutation or deployment performed.
- 2026-10-02T14:34:58Z [implementation] — Verify #3391 failed before pytest: ruff_format found 4 files and bootstrap_drift found 6 deployed copies after --no-prepare. The no-preparation attempt cannot certify the candidate; rerun with canonical preparation.
- 2026-10-02T14:36:24Z [implementation] — Release candidate is ready for owner-approved commits: canonical verify #3392 passed 579 tests with 16 skipped and 8 deselected over 19 mapped files; full public default and slow lanes are green; store signatures are green. Remaining actions are external only: review diff, commit/push GitLab, publish filtered GitHub snapshot, reconcile issues and create release/tag/site if approved. r111-verification-cycle-replay remains active and unmet.
- 2026-10-02T14:36:39Z [implementation] — AC verified: 1. Public snapshot tree bb9c33154af2c5054757d9a66967389a26f7a165 contains 1622 files; state projection, .gitlab-ci.yml, changelog.d and TAUSIK-plan-1.9.md are absent; sanitized AGENTS.md and CLAUDE.md retain static guidance. 2. Snapshot default lane: 12553 passed, 101 skipped, 143 deselected, 0 failed; slow lane: 129 passed, 14 skipped, 12654 deselected, 0 failed. 3. CHANGELOG EN/RU and whats-new EN/RU carry those denominators; gen_doc_constants --check passes and README/constants report 12797 collected tests. 4. Isolated official store has exact registry=manifest=directories docs,excel,pdf, no bundles.json; ci/verify_signatures.py reports 3 manifest+Ed25519 checked, 0 failed. Negative: no commit, push, tag, release, tracker mutation or site deployment performed. Canonical verify #3392 PASS.
- 2026-10-02T14:37:00Z [done] — AC-1: ✓ tests/test_publication_snapshot.py::TestTheLiveTree::test_no_leak_class_survives_on_the_snapshot and physical snapshot boundary inspection. AC-2: ✓ manual public-snapshot runs python -m pytest tests/ -q --tb=short = 12553 passed/101 skipped/143 deselected and python -m pytest tests/ -m slow -q --tb=short = 129 passed/14 skipped/12654 deselected. AC-3: ✓ python scripts/gen_doc_constants.py --check plus tests/test_gen_doc_constants.py; README/constants = 12797. AC-4: ✓ isolated-store python ci/verify_signatures.py with TAUSIK_CORE_SCRIPTS = 3 manifest+Ed25519 checked/0 failed and exact manifest/directory comparison. Domain: the extracted 1622-file public tree bootstraps all six hosts and the separate installable store contains only the three owner-approved neutral skills.
