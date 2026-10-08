---
slug: selected-tests-is-removed-from-cohort-identity-inputs
task: fix-pooled-verify-recovery-ss4-widening-inputs
date: "2026-10-07"
edges: []
---

## Decision

selected_tests is removed from cohort identity inputs; identity placeholders 'declared-at-run'/'selection-evidence-of-run' are dropped from SPEC SS1

## Rationale

selected_tests made identity unstable across identical executions (order-sensitive) and the placeholders bound literal strings instead of content; identity now = members + content_hashes (content-only digest, no mtime) + gate signature + union files hash, all real values. Pinned by TestProvenanceDigest x4 in tests/test_verify_cohort.py
