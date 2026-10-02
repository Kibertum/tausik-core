---
slug: make-clean-bootstrap-skill-installation-opt-in
title: "Make clean bootstrap skill installation opt-in"
status: done
epic: null
story: null
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Bootstrap skill discovery and activation defaults only"
scope_exclude: "No official-store content changes, no external downloads in tests, no commit or publication"
relevant_files:
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_config.py"
  - "tests/test_bootstrap_extension_skills.py"
  - "scripts/pytest_test_count.py"
  - "scripts/gen_doc_constants.py"
  - "tests/test_gen_doc_constants.py"
  - "docs/en/vendor-skills.md"
  - "docs/ru/vendor-skills.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
scope_paths:
  - "bootstrap/bootstrap.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap_copy.py"
  - "tests/test_bootstrap_extension_skills.py"
  - "tests/test_bootstrap_check.py"
  - "tests/test_vendor.py"
  - "docs/en/vendor-skills.md"
  - "docs/ru/vendor-skills.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "scripts/pytest_test_count.py"
  - "scripts/gen_doc_constants.py"
  - "tests/test_gen_doc_constants.py"
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T14:57:08Z"
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

A clean TAUSIK bootstrap installs only bundled core skills, performs no external skill downloads unless the user created an active skills.json or explicitly opted in, and never detects an unavailable extension skill.

## Acceptance Criteria

AC-1 A clean public-style checkout with only skills.example.json performs zero external skill sync/download and does not create an active skills.json. AC-2 Auto-detected extension skills are restricted to sources deployable under the current flags/config, so docs produces no missing-skill warning when its store is absent or official skills are not enabled. AC-3 Existing explicit skills.json and --include-official behavior remain supported. Negative: no network dependency is required by the tests and no external catalog is silently enabled.

## Plan

[{"step": "Pin clean-bootstrap behavior with focused tests", "done": true}, {"step": "Stop activating the example manifest by default", "done": true}, {"step": "Filter detected extensions to resolvable sources", "done": true}, {"step": "Update docs and verify clean plus explicit paths", "done": true}]

## Rollback

Revert bootstrap default activation changes; skills.example.json remains available as documentation

## Journal

- 2026-10-02T14:41:11Z [implementation] — Auto-detection now intersects recommendations with skills deployable under current flags/config; absent or disabled docs store no longer becomes a missing skill.
- 2026-10-02T14:41:11Z [implementation] — Pinned clean-vs-explicit manifest behavior in one parametrized bootstrap test plus deployable-extension filtering tests; 41 focused tests pass and dedupe audit reports 0 copies.
- 2026-10-02T14:41:11Z [implementation] — Removed automatic copy of skills.example.json to skills.json; bootstrap now calls sync_deps only when an explicit active manifest exists.
- 2026-10-02T14:48:19Z [implementation] — Final public run exposed badge drift: development collection 12827 includes 26 tests/test_ci_lane_dev.py nodes excluded from GitHub; public collection is 12801. Extending scope so the generated count derives its ignored test paths from EXCLUDED_FROM_PUBLIC_SNAPSHOT.
- 2026-10-02T14:54:50Z [implementation] — AC-1: ✓ tests/test_bootstrap_extension_skills.py::test_example_manifest_is_inert_until_explicitly_activated plus clean public bootstrap output: zero external downloads and skills.json absent. AC-2: ✓ tests/test_bootstrap_extension_skills.py::TestDetectExtensionSkills::test_detection_only_returns_deployable_skills and clean bootstrap emitted no docs warning. AC-3: ✓ the active-manifest parameter invokes sync once and official-disabled/enabled test preserves flag behavior. Negative: tests monkeypatch sync_deps and require no network. Domain: a physical 1622-file public tree bootstrapped Claude, Cursor, Qwen, Kilo, OpenCode and Codex successfully without silently activating any external catalog.
- 2026-10-02T14:54:50Z [implementation] — Clean extracted public tree 4670479fa6a32b781ead00655833aec0ca3c5d45 bootstrapped all six hosts with no skills.json creation, no external sync section and no missing-skill warning. Final public lanes: default 12559 passed/100 skipped/143 deselected; slow 129 passed/14 skipped/12659 deselected. Public collection and README badge are 12802; development-only 26-test reader is derived from the snapshot exclusion list.
- 2026-10-02T14:57:04Z [implementation] — Canonical verify #3394 PASS: 939 passed, 16 skipped, 51 deselected over 49 mapped test files; ruff and bootstrap drift green. Full public default and slow lanes were also green on the extracted release tree.
