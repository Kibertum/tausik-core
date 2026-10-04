---
slug: run-the-focused-lane-from-a-filtered-git-archive-without
title: "Run the focused lane from a filtered git archive without repository metadata."
type: dead_end
tags:
  - git-metadata
  - public-snapshot
  - test-fixture
task: public-snapshot-tests-read-excluded-files
edges: []
---

Approach: Run the focused lane from a filtered git archive without repository metadata.
Reason: Four tests intentionally ask Git for the tracked set or HEAD tree. A tar archive contains the right files but is not a checkout, so those tests failed on `not a git repository` rather than on product behavior. Re-run after initializing a temporary index-only repository; omit the HEAD-object test because the production dry-run already verified the filtered tree object.
