---
slug: tests-bootstrap-non-destructive
title: "Tests: bootstrap NEVER touches .tausik/stacks/"
status: done
epic: v16-plugin-arch-and-docs
story: tests-migration
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_bootstrap_non_destructive.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:20:07Z"
---

## Goal

tests/test_bootstrap_non_destructive.py: seed .tausik/stacks/ruby/stack.json + guide.md, run bootstrap, verify files unchanged (mtime + content hash). Same for .tausik/config.json customizations. Bootstrap warning emitted when stacks/&lt;builtin&gt;/ edited directly. CRITICAL safety guarantee.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:20:06Z [planning] — AC verified: tests/test_bootstrap_non_destructive.py — 5 кейсов asserting bootstrap NEVER touches .tausik/stacks/: override-untouched, override-of-builtin-name-untouched, target-isolation, no-.tausik-paths-written, idempotent.
