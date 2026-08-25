---
slug: senar-skills-rewrite
title: "Rewrite core skills for SENAR enforcement"
status: done
epic: senar-skills
story: senar-skills-core
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-23T12:33:21Z"
---

## Goal

Update all 8+1 core skills to enforce SENAR workflow: QG-0/QG-2 without --force, dead-end documentation, explorations, metrics display, session duration checks

## Acceptance Criteria

1. /plan sets goal+AC so task start works without --force. 2. /task start does NOT use --force. 3. /task done walks AC checklist and uses --ac-verified. 4. /task instructs dead-end on failure. 5. /start shows SENAR metrics and session duration warning. 6. /end shows SENAR metrics dashboard. 7. /checkpoint checks session duration. 8. /plan offers explore for unknown domains. 9. /review checks dead-end documentation. 10. New /explore skill exists.

## Plan

## Rollback

## Journal
