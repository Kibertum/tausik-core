---
slug: run-canonical-verify-after-the-first-version-flag
title: "Run canonical verify after the first version-flag implementation"
type: dead_end
tags: []
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Run canonical verify after the first version-flag implementation
Reason: The filesize gate found scripts/project_parser.py at 502 lines against a 500-line limit, so pytest was correctly skipped. Move root version-option registration into project_parser_errors and re-run from a bootstrapped mirror.
