---
slug: filter-verify-preparation-only-in-source-before-the-next
title: "Filter verify preparation only in source before the next scoped verify"
type: dead_end
tags: []
task: r111-release-lane-five-regressions
edges: []
---

Approach: Filter verify preparation only in source before the next scoped verify
Reason: The running CLI had already imported the old deployed verify_prepare module, so that same process still passed gates.json to ruff before bootstrap redeployed the fix. Restore JSON, redeploy, then rerun in a fresh process.
