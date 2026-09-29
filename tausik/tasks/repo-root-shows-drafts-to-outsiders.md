---
slug: repo-root-shows-drafts-to-outsiders
title: "Repository root shows drafts and survey PDFs to an outsider"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "./"
  - "docs/"
  - "changelog.d/"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:11:58Z"
resolution: obsolete
resolution_reason: "Premise was a local-disk artefact: the drafts and PDFs are untracked and never reach GitHub; the one tracked internal file (TAUSIK-plan-1.9.md) is already excluded from the public snapshot (scripts/publication_snapshot.py:57, tests/test_publication_snapshot.py). Verdict per root file is in this task's log."
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Cold read (session #279): the first screen of the repository lists TAUSIK-plan-1.9.md, RENAR-readme-draft.md, prompt.md and survey PDFs next to README. An outsider cannot tell product from working notes.

## Acceptance Criteria

AC-1 Every root file is listed with a verdict: product, moved (path), or deleted (commit). AC-2 NEGATIVE: nothing referenced by docs, gates or bootstrap is moved without its references following (grep evidence in log). AC-3 The published snapshot excludes what stays as internal notes.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T22:11:51Z [implementation] — AC-1: ✓ verdict per root file. TRACKED+PUBLISHED, product: AGENTS.md CLAUDE.md QWEN.md (host rules), README.md README.ru.md CHANGELOG.md CHANGELOG.ru.md ROADMAP.md LICENSE CODE_OF_CONDUCT.md CONTRIBUTING.md SECURITY.md RENAR-CONFORMANCE.yaml pyproject.toml requirements.txt ci-constraints.txt skills.example.json .gitattributes .gitignore. TRACKED, NOT PUBLISHED (scripts/publication_snapshot.py:57 EXCLUDED_FROM_PUBLIC_SNAPSHOT): TAUSIK-plan-1.9.md, .gitlab-ci.yml. UNTRACKED local working files, never reach GitHub: KIBERTUM-org-profile.md, RENAR-readme-draft.md, TAUSIK-pending-readme-renar.md, TAUSIK-report-*.pdf/.md, TAUSIK-roadmap.pdf, *-social-preview.png, prompt.md, opencode.json, skills.json. The cold-read agent saw them because it read the local disk, not the published tree. AC-2 Negative: ✓ nothing moved, so no reference can break. AC-3: ✓ already true, tests/test_publication_snapshot.py holds the exclusion. Premise was a local-disk artefact.
