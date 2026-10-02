---
slug: close-the-read-only-audit-immediately-after-a-no-tests
title: "Close the read-only audit immediately after a no-tests-expected verify"
type: dead_end
tags: []
task: audit-and-trim-111-public-release-snapshot
edges: []
---

Approach: Close the read-only audit immediately after a no-tests-expected verify
Reason: task done re-exported state and invalidated the fresh run twice (#3374/#3376); the audit remains active rather than bypassing QG-2.
