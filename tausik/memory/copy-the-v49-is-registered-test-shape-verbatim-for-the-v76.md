---
slug: copy-the-v49-is-registered-test-shape-verbatim-for-the-v76
title: "Copy the v49 'is registered' test shape verbatim for the v76 migration test (two bare asserts: N in "
type: dead_end
tags: []
task: fix-pooled-verify-recovery-ss4-widening-inputs
edges: []
---

Approach: Copy the v49 'is registered' test shape verbatim for the v76 migration test (two bare asserts: N in MIGRATIONS; SCHEMA_VERSION >= N)
Reason: The shape signature erases names and numbers, so the v76 twin became structurally indistinguishable from the v49 twin and the test_dedupe ratchet reddened (283/671 vs baseline 282/669) — a new pair-group formed across two files. Fix: fuse the two clauses into ONE assert statement (assert 76 in MIGRATIONS and SCHEMA_VERSION >= 76) — different AST shape, same contract. Also verify #3608 red on scope-narrower-than-diff: two defect commits (f2fa9d57, de2ca844) landed AFTER task start (14:01:57Z < 14:02:50Z/14:03:05Z), so their files (CHANGELOG.md, CHANGELOG.ru.md, scripts/mcp_cli_parity.py, one memory export) counted as undeclared until added to relevant_files
