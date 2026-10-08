---
slug: run-final-canonical-verify-with-no-prepare
title: "Run final canonical verify with --no-prepare"
type: dead_end
tags:
  - release
  - verify
task: validate-the-final-1-11-release-candidate
edges: []
---

Approach: Run final canonical verify with --no-prepare
Reason: Verify #3391 correctly failed because four edited tests needed ruff formatting and six deployed publication_snapshot.py copies had not been refreshed; static failures prevented pytest, so the run cannot certify the candidate.
