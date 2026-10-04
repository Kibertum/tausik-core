---
slug: treat-the-public-snapshot-defect-as-confined-to-tests-test
title: "Treat the public-snapshot defect as confined to tests/test_publication_lines.py and run the full ori"
type: dead_end
tags:
  - mypy
  - public-snapshot
  - release-1111
task: public-snapshot-tests-read-excluded-files
edges: []
---

Approach: Treat the public-snapshot defect as confined to tests/test_publication_lines.py and run the full original four-test regression slice unchanged.
Reason: The boundary fix passed, but the required repo-wide mypy checks exposed 18 real type errors in five already-dirty 1.11.1 implementation files. A green snapshot cannot be claimed until those existing release changes type-check; skipping the two tests would hide a release blocker.
