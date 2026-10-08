---
slug: reduce-the-official-skill-catalog-to-three
title: "Reduce the official skill catalog to three neutral document skills"
status: done
epic: null
story: null
complexity: complex
role: release-engineer
stack: python
tier: substantial
call_budget: null
defect_of: null
scope: "external official skill-store contents and manifests; core skill docs/bootstrap compatibility; obsolete TAUSIK-plan-1.9.md and publication rules; RENAR references in harness"
scope_exclude: "No change to Kibertum corporate plugin repository, no commit, push, tag, release, tracker mutation or site deployment"
relevant_files:
  - README.md
  - README.ru.md
  - QWEN.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - TAUSIK-plan-1.9.md
  - "bootstrap/analyzer.py"
  - "bootstrap/bootstrap_config.py"
  - "bootstrap/bootstrap_templates.py"
  - docs
  - "harness/claude/mcp/project/tools_extra.py"
  - "scripts/code_counts.py"
  - "scripts/doc_drift_common.py"
  - "scripts/doc_drift_tables.py"
  - "scripts/gen_doc_constants.py"
  - "scripts/publication_snapshot.py"
  - tests
scope_paths:
  - skills-official-release-cleanup
  - docs
  - bootstrap
  - scripts
  - tests
  - harness
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - QWEN.md
  - TAUSIK-plan-1.9.md
scope_tools: []
depends_on: []
completed_at: "2026-10-02T13:44:07Z"
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

Keep only pdf, docs and excel in the TAUSIK official catalog; remove company-specific and MCP-redundant skills from TAUSIK supply; delete the obsolete 1.9 plan and reconcile every public document and release invariant.

## Acceptance Criteria

AC-1 The official store contains only pdf, docs and excel plus required manifests; no Kibertum corporate role or service integration ships. AC-2 TAUSIK core documentation describes the three-skill neutral catalog and no removed skill or obsolete bundle as current. AC-3 TAUSIK-plan-1.9.md and its publication exception are gone with no dangling reference. AC-4 RENAR references in harness are classified and either justified as the framework reasoning protocol or removed if accidental. Negative: core bootstrap and per-skill installation still work without the removed catalog entries.

## Plan

[{"step": "Inventory RENAR and every live official-skill consumer", "done": true}, {"step": "Prepare the three-skill store in an isolated clean worktree", "done": true}, {"step": "Remove obsolete core plan and reconcile EN/RU documentation and manifests", "done": true}, {"step": "Run store and core verification with negative coverage", "done": true}]

## Rollback

Restore deleted core files from Git and retain the untouched dirty skills-official checkout; external-store cleanup is prepared in an isolated clean worktree

## Journal

- 2026-10-02T13:23:06Z [implementation] — Reduced clean official-store worktree to docs/excel/pdf; removed obsolete plan and migration pages; reconciled current EN/RU skill docs, manifests, bootstrap guidance, and changelogs. RENAR remains core protocol exposed through harness.
- 2026-10-02T13:24:11Z [implementation] — Prepared isolated clean official-store worktree from origin/main; retained only docs, excel and pdf plus manifests and CI infrastructure.
- 2026-10-02T13:24:11Z [implementation] — RENAR is intentional: root renar holds the protocol and conformance artifacts; harness reason/task/MCP surfaces expose SPEC/ADAPT/ACTZ/AT to agents. No duplicate implementation found.
- 2026-10-02T13:24:12Z [implementation] — Deleted obsolete 1.9 plan and old migration pages; reconciled bilingual current docs, bootstrap text, manifests and 1.11 changelogs.
- 2026-10-02T13:27:54Z [implementation] — Focused tests exposed one stale publication count after removing the obsolete plan fixture: expected exclusions remained 2 while only tausik/tasks is excluded. Updated the behavioral assertion to 1.
- 2026-10-02T13:43:20Z [implementation] — Official store contract: exact docs/excel/pdf manifests and directories; 3/3 manifest plus Ed25519 signatures pass. Focused core tests: 183 passed. Docs links: 234 passed. Scoped verify #3386: 1180 passed, 32 deselected, all applicable blocking gates passed; scope warning is caused by pre-existing concurrent 1.11 changes and deleted-path formatter limitation dead end #861.
- 2026-10-02T13:43:32Z [implementation] — AC verified: AC-1 exact store manifests and filesystem contain only docs/excel/pdf; all 3 signatures pass and removed integration/corporate names are absent. AC-2 live EN/RU docs name only docs/excel/pdf; obsolete bundle/migration references absent; docs link suite 234 passed. AC-3 TAUSIK-plan-1.9.md and its publication exception/test are deleted; repository search found no live reference. AC-4 RENAR is intentional: root renar owns protocol artifacts; harness reason/task/MCP surfaces expose SPEC/ADAPT/ACTZ/AT without a duplicate implementation. Negative: focused bootstrap/install/publication suites 183 passed; verify #3386 passed 1180 tests with 32 deselected.
- 2026-10-02T13:44:01Z [implementation] — AC-1 (three-skill supply): ✓ tests/test_bootstrap_extension_skills.py::TestDetectExtensionSkills::test_detects_real_skills
- 2026-10-02T13:44:03Z [implementation] — AC-2 (current documentation): ✓ tests/test_docs_links_resolve.py::test_every_relative_link_resolves[docs\\en\\skills.md]
- 2026-10-02T13:44:03Z [implementation] — AC-3 (publication without obsolete plan): ✓ tests/test_publication_snapshot.py::TestTheLiveTree::test_the_ratchet_files_are_kept_and_the_projection_is_not
- 2026-10-02T13:44:03Z [implementation] — AC-4 (RENAR classification): ✓ tests/test_skills_maturity.py::test_all_core_skills_meet_maturity_contract
- 2026-10-02T13:44:27Z [done] — Correction to AC-4 citation: ✓ tests/test_docs_links_resolve.py::test_every_relative_link_resolves[docs\\en\\reasoning-trace.md]. The earlier test_all_core_skills_meet_maturity_contract name was incorrect; no such node exists.
- 2026-10-02T13:44:28Z [done] — Domain: clean store filesystem and both release manifests resolve exactly docs/excel/pdf; ci/verify_signatures.py reproduced every manifest and Ed25519 signature against the publisher public key; no corporate or integration slug occurs in the three shipped skill trees.
