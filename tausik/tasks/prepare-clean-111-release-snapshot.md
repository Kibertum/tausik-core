---
slug: prepare-clean-111-release-snapshot
title: "Prepare the clean 1.11 release materials and public snapshot"
status: done
epic: null
story: null
complexity: complex
role: release-engineer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "Changelog subsystem removal; EN/RU changelog and whats-new pages; version/generated constants; publication snapshot filtering/sanitization and their focused tests/docs."
scope_exclude: "No external issue or milestone mutation, commit, push, tag, GitHub Release or site deployment in this task."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - AGENTS.md
  - CLAUDE.md
  - pyproject.toml
  - "scripts/tausik_version.py"
  - "scripts/publication_snapshot.py"
  - "scripts/project.py"
  - "scripts/project_parser_ops.py"
  - "scripts/gate_changelog.py"
  - "docs/en/cli-admin.md"
  - "docs/ru/cli-admin.md"
  - "docs/en/publishing.md"
  - "docs/ru/publishing.md"
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
  - "docs/_generated/constants.json"
  - "docs/_generated/doc-map.md"
  - "tests/test_publication_snapshot.py"
  - "scripts/changelog_fragments.py"
  - "scripts/project_cli_changelog.py"
  - "scripts/project_parser_changelog.py"
  - "tests/test_changelog_fragments.py"
  - "changelog.d/.gitkeep"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-10-02T12:45:21Z"
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

Produce a clean, user-facing 1.11.0 release candidate: direct bilingual changelogs and release notes, no changelog.d subsystem, no internal/live state in the GitHub snapshot, and a verified versioned tree ready for GitLab history and a filtered GitHub cut.

## Acceptance Criteria

AC-1 changelog.d and its parser/CLI/tests/docs/gate bypass are absent; task closure again requires direct EN and RU changelog evidence. Negative: no dangling import, command or documentation reference remains. AC-2 CHANGELOG.md and CHANGELOG.ru.md contain a complete 1.11.0 section covering every shipped user-visible economy feature without unsupported weekly-quota claims. AC-3 docs/en/whats-new-1.11.md and docs/ru/whats-new-1.11.md exist, are linked by the release body, and state the measured limits honestly. AC-4 version sources and generated constants consistently report 1.11.0. AC-5 a dry-run public snapshot contains neither changelog.d, the internal release plan, live DYNAMIC state nor private host/dev paths while retaining static AGENTS guidance. AC-6 focused tests, documentation checks, default release lane and dedupe audit pass with denominators.

## Plan

[{"step": "Remove the changelog fragment subsystem and restore direct bilingual changelog enforcement", "done": true}, {"step": "Consolidate the 1.11 changelog and create bilingual release notes plus release body", "done": true}, {"step": "Bump the release version and regenerate derived documentation", "done": true}, {"step": "Sanitize and verify the public snapshot boundary", "done": true}, {"step": "Run focused, documentation and release quality checks", "done": true}]

## Rollback

Revert the release-preparation changes; restore the changelog fragment modules/tests/docs and regenerate constants from 1.10.1.

## Journal

- 2026-10-02T12:33:48Z [implementation] — Step 1: removed changelog.d, its CLI/parser/module/test and gate bypass; direct EN/RU changelog enforcement remains.
- 2026-10-02T12:33:48Z [implementation] — Step 2: consolidated a bounded 1.11 section in both changelogs; added EN/RU whats-new pages and a release body that passes the bilateral-link contract.
- 2026-10-02T12:33:49Z [implementation] — Step 3: bumped pyproject, runtime version, badges and generated constants to 1.11.0; regenerated the documentation map.
- 2026-10-02T12:33:49Z [implementation] — Step 4: public snapshot excludes the internal 1.11 plan and strips AGENTS/CLAUDE dynamic blocks while keeping static guidance. Candidate dry-run: 1625 public, 3506 excluded, all three leak classes zero; changelog.d absent.
- 2026-10-02T12:36:35Z [implementation] — Release snapshot prepared: changelog.d subsystem removed; bilingual 1.11 changelogs and release notes added; version set to 1.11.0; public snapshot strips live host state and excludes the internal economy plan. Focused validation: 276 passed; release-body links, doc map, and dedupe audit passed.
- 2026-10-02T12:44:25Z [implementation] — Verification evidence: run #3379 PASS, complete declared scope; standard affected-test lane selected 92/656 test files and passed 2,438 with 18 skipped. Release note validation: 276 focused tests passed; publish notes, doc-map check, ruff/format, bootstrap drift, documentation coverage, and dedupe audit passed. Public snapshot dry-run: 1,625 public, 3,506 excluded, zero internal-host/dev-path/transcript leaks.
- 2026-10-02T12:44:33Z [implementation] — Release checks complete: verify #3379 passed 2,438 tests over 92/656 selected files; focused documentation/publication checks passed 276 tests; release notes, doc map, dedupe and public snapshot boundaries passed.
- 2026-10-02T12:44:51Z [implementation] — AC verified: 1. changelog.d subsystem, command, tests, docs and gate bypass removed; no live dangling references. 2. EN/RU 1.11.0 changelogs cover shipped economy work and explicitly reject an unmeasured weekly-quota claim. 3. EN/RU whats-new pages exist and publish-notes validation passed. 4. pyproject, runtime version, badges and generated constants report 1.11.0. 5. snapshot dry-run: 1,625 public, 3,506 excluded, zero internal host/dev/transcript leaks; dynamic state stripped. 6. verify #3379: 2,438 passed, 18 skipped across 92/656 affected test files; focused docs/publication 276 passed; doc map and dedupe checks passed.
- 2026-10-02T12:45:20Z [implementation] — AC-5 (public cut is sanitized): ✓ tests/test_publication_snapshot.py::TestTheExclusionListIsOneDeclaration::test_dynamic_state_is_removed_but_static_agent_guidance_remains. AC-6: green verification_run #3379 (2,438 passed, 18 skipped; 92/656 test files selected).
