---
slug: d5-merge-security
title: "Merge security references"
status: done
epic: docs-overhaul-v13
story: references-merge
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:41:55Z"
---

## Goal

Merge references/security/owasp+security into docs/en/security.md + docs/ru/security.md

## Acceptance Criteria

1. references/security/security.md (RU) moved to docs/ru/security.md with bilingual header. 2. EN translation created at docs/en/security.md. 3. references/security/owasp.md moved to docs/en/security-checklist.md. NEGATIVE: original references/security/ marked for deletion in d5-cleanup.

## Plan

## Rollback

## Journal

- 2026-04-26T15:41:55Z [implementation] — AC verified: docs/ru/security.md exists with bilingual header ✓ docs/en/security.md created (EN translation, OWASP brief, validation, secrets, TAUSIK guards) ✓ docs/en/security-checklist.md exists (moved from owasp.md) ✓ NEGATIVE: references/security/ marked for d5-cleanup deletion
