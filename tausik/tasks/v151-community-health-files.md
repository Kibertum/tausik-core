---
slug: v151-community-health-files
title: "[P2] Public-repo polish — SECURITY.md, CODE_OF_CONDUCT, issue/PR templates"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "SECURITY.md, CODE_OF_CONDUCT.md, .github/ISSUE_TEMPLATE/*, .github/pull_request_template.md"
scope_exclude: "no code; no history rewrite; no change to existing docs"
relevant_files:
  - SECURITY.md
  - CODE_OF_CONDUCT.md
  - ".github/ISSUE_TEMPLATE/bug_report.md"
  - ".github/ISSUE_TEMPLATE/feature_request.md"
  - ".github/pull_request_template.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T01:09:50Z"
---

## Goal

Close the last resolvable public-release-readiness finding (repo-hygiene: missing community health files) so the public repo reads as professional/complete: add SECURITY.md (vulnerability disclosure policy), CODE_OF_CONDUCT.md (Contributor Covenant), .github/ISSUE_TEMPLATE/{bug_report,feature_request}.md, and .github/pull_request_template.md. Pure additions, no code.

## Acceptance Criteria

AC1: SECURITY.md at repo root — supported versions + private disclosure channel + scope. AC2: CODE_OF_CONDUCT.md (Contributor Covenant) at root. AC3: .github/ISSUE_TEMPLATE/bug_report.md + feature_request.md. AC4: .github/pull_request_template.md referencing the TAUSIK task workflow. AC5: all are valid markdown, no secrets/internal URLs leaked in them, links resolve. Negative: SECURITY.md disclosure does NOT expose an internal/private address (use the public repo's Security advisories / the author's public contact), and no internal gitlab/host appears in any new file.

## Plan

## Rollback

git revert; pure additive doc files.

## Journal

- 2026-06-15T01:09:49Z [implementation] — AC1: ✓ SECURITY.md — supported versions (1.5.x), private disclosure via GitHub Security Advisories, scope (receipts/gates/injection/supply-chain), out-of-scope. AC2: ✓ CODE_OF_CONDUCT.md — Contributor Covenant 2.1. AC3: ✓ .github/ISSUE_TEMPLATE/bug_report.md + feature_request.md. AC4: ✓ .github/pull_request_template.md referencing the TAUSIK task/QG workflow. AC5: ✓ valid markdown; grep confirms no internal gitlab/host/path/email leaked (disclosure via GitHub Advisories, not a private address). Negative: no internal address exposed — uses public GitHub Security Advisories. Domain: a public visitor now finds a clear security-disclosure path, CoC, and contribution templates — standard signals of a maintained OSS project.
