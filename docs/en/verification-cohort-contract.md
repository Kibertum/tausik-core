# Verification Cohort Contract (1.11.3 pooled verification, Track A)

<!-- doc-map: reader=agent; zone=quality -->

SPEC `verification-cohort-contract` · status draft · task
`r1112-verification-cohort-contract` → superseded by the implementation tasks
`r1112-cohort-receipts-and-incremental-rerun`,
`r1112-hierarchy-verify-and-atomic-close`,
`r1112-pooled-verification-proof-and-rollout`.

## Why (measured, not felt)

`scripts/verify_baseline.py` on this repository (2026-10-06, 3562 recorded
runs over 1409 tasks): **2153 invocations (60.4%) are re-runs of a task that
already had a run**; 1076 tasks were verified twice or more; 248 tasks went
red at least once. Cohorts of ≥5 tasks (a release story closing in a 2h
window) paid **2049 invocations / ~12.5 hours**; the dominant fallback reason
there is `under-declared` (1175 runs). The cost is not the suite — it is
re-paying the same lane per task instead of once per cohort.

## 1. Cohort identity (canonical)

A cohort is identified by the SHA-256 over the canonical serialization of:

1. **sorted task membership** — slugs, sorted lexicographically; order never
   participates in identity;
2. **per-task fingerprints** — each member's `fingerprint` as served by
   `task show --package` (goal/AC/plan/relevant_files);
3. **union scope** — the deduplicated, sorted union of `relevant_files` over
   membership (empty set ⇒ `unscoped`, which never forms a close cohort);
4. **content hashes** — file content digests of the union scope at open time;
5. **gate signature** — the enabled-gate set + per-gate config hash;
6. **selected tests** — the test-selection evidence list (the
   `affected-tests-*.json` selection), so a changed selector invalidates;
7. **repository state** — `git rev-parse HEAD` plus the dirty-file list
   digest (a cohort cannot silently span a commit).

Identity is computed at cohort OPEN and re-asserted before any reuse
decision. Any component mismatch = a different cohort, never a "close
enough".

## 2. Lifecycle

```
OPEN → REVIEW-READY? → POOLED VERIFY → ATOMIC CLOSE
```

- **OPEN**: identity computed and persisted with the cohort record.
- **REVIEW-READY gate (AC-3)**: a task enters a CLOSE cohort only with
  plan complete and AC evidence logged; story/epic closure is atomic —
  either every member closes or none does (a partial close is a corrupt
  state, not a success).
- **POOLED VERIFY**: one gate execution over the union scope produces ONE
  signed receipt covering every member.
- **ATOMIC CLOSE**: members close on that receipt in one transaction.

## 3. Red handling (incremental rerun)

After a red pooled run, the next required set is:

```
previous FAILURES  ∪  tests affected by files changed since that run
```

A prior green result is reusable **only when its dependency inputs are
unchanged** (content hashes of its scope files + the gate signature + the
test-selection evidence). Reuse is per-evidence, never per-vibes.

## 4. Invalidators (the negative contract)

Reuse of ANY receipt — pooled or single — is refused, and the run widens to
the full applicable lane, when any of:

- membership drift (a task joined or left the cohort);
- task edits (fingerprint of any member changed);
- config or gate-signature drift;
- security-sensitive scope in the union (hooks, auth, billing, payment —
  stricter, never pooled across such a boundary without explicit consent);
- uncertain dependency mapping (the affected-tests evidence is missing or
  stale for any changed file);
- missing evidence (no selection list, no content digests, no repo state).

A refusal names WHICH invalidator fired; silence is not an invalidation and
must not become one.

## 5. Schema/API migration and backward compatibility

- `verification_runs` gains nullable cohort columns (`cohort_id`,
  `cohort_size`) — existing rows read as cohorts of one, and every
  historical behavior is preserved;
- single-task `verify --task` keeps its exact semantics and its signed
  handle (`<run_id>.<nonce>`, single-use, TTL) — a pooled receipt uses the
  same signing key and the same redemption rules, extended to N members;
- `task done --verify-handle` accepts either; a pooled handle redeems
  against every listed member in one transaction.

## Out of scope

Gate implementation of pooling itself (receipts task), hierarchy semantics
(story/epic close task), and the rollout proof live in the three follow-up
tasks named above.
