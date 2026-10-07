# Verification Cohort Contract (1.11.3 pooled verification, Track A)

<!-- doc-map: reader=agent; zone=quality -->

SPEC `verification-cohort-contract` · status draft · task
`r1112-verification-cohort-contract` → superseded by the implementation tasks
`r1112-cohort-receipts-and-incremental-rerun`,
`r1112-hierarchy-verify-and-atomic-close`,
`r1112-pooled-verification-proof-and-rollout`.

## Why (measured, not felt)

`scripts/verify_baseline.py` on this repository (recounted 2026-10-07 on the
fixed counter — 3605 recorded task-linked runs over 1418 tasks): **2187
invocations (60.7%) are re-runs of a task that already had a run**; 1085 tasks
were verified twice or more; 255 tasks went red at least once. Cohorts of ≥5
tasks (a release story closing in a 2h window) paid **1147 invocations /
~8.4 hours over 58 cohorts (466 task seats)**; the dominant fallback reason
there is `under-declared` (658 runs). The first published cut (2049 / ~12.5 h
/ 1175) came from the counter's two defects — a slug re-entering a story
after a gap opened a duplicate seat, and every member's runs were attributed
to every window containing it — and overstated the very waste it measured.
Sizes 3-4 (previously dropped by having no bucket) paid 625 invocations
across 71 cohorts separately. The cost is not the suite — it is re-paying
the same lane per task instead of once per cohort.

## 1. Cohort identity (canonical)

A cohort is identified by the SHA-256 over the canonical serialization of:

1. **sorted task membership** — slugs, sorted lexicographically; order never
   participates in identity;
2. **per-task fingerprints** — each member's `fingerprint` as served by
   `task show --package` (goal/AC/plan/relevant_files), plus the member's
   status (a member blocked or reopened after verify is not the cohort that
   was verified);
3. **union scope** — the deduplicated, sorted union of `relevant_files` over
   membership (empty set ⇒ `unscoped`, which never forms a close cohort);
4. **content hashes** — a content-only digest (path + full-content SHA-256,
   sorted; no mtimes — identity is recomputed at close time and a checkout
   stamps mtimes on files nobody edited) of the union scope at open time;
5. **gate signature** — the enabled-gate set + per-gate config hash;
6. **repository state** — `git rev-parse HEAD` plus the dirty-file list
   digest (a cohort cannot silently span a commit).

Originally drafted with a seventh input — the test-selection evidence list —
and shipped with placeholder strings for it and for content hashes. Both were
dishonest in opposite directions: selection evidence exists only AFTER the
run, and identity is minted BEFORE it, so the input could never carry a real
value; a constant placeholder, conversely, is a term that can never
invalidate anything. The 1.11.3 audit killed both: content hashes are now
the real pre-run digest, and selected tests are no longer an identity input
(the affected-tests selection still participates through the delegated
run's own digest).

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
unchanged** (content hashes of its scope files + the gate signature).
Reuse is per-evidence, never per-vibes.

Honest state of the fine-grained set: `required_after_red` is a pure
function proven by unit tests, but the live pooled path does NOT select it —
after a red pooled run, the next pooled run re-executes the full lane,
exactly as a widening does. Wiring the incremental selection is follow-up
work; this contract claims the set's definition and its proof, not its
wiring.

## 4. Invalidators (the negative contract)

When any of these fires, reuse of prior GREEN evidence is refused — and the
run **widens**: the full lane EXECUTES, the prior cohort row is marked
`invalidated`, and a new cohort row records the attempt:

- membership drift (a task joined or left the cohort);
- task edits (fingerprint of any member changed);
- member-status drift (a member blocked or reopened after verify);
- config or gate-signature drift;
- security-sensitive scope in the union (hooks, auth, billing, payment —
  stricter: refused outright, on a fresh cohort exactly as much as on a
  drifted one, never pooled across such a boundary without explicit
  consent);
- uncertain dependency mapping (the affected-tests evidence is missing or
  stale for any changed file);
- missing evidence (a member task that no longer exists — the cohort cannot
  form; re-form it without the deleted slug).

A refusal names WHICH invalidator fired; silence is not an invalidation and
must not become one. Widening must not degrade into a refusal loop: the
first implementation returned a refusal instead of running, which
permanently bricked the membership — the operator cannot un-drift a cohort,
so every retry met the same wall. An invalidator refuses the CARRY-FORWARD
of old evidence, never the execution of new verification.

## 5. Schema/API migration and backward compatibility

- `verification_runs` gains a nullable `cohort_identity` column (v75) —
  existing rows read as cohorts of one, and every historical behavior is
  preserved;
- single-task `verify --task` keeps its exact semantics and its signed
  handle (`<run_id>.<nonce>`, single-use, TTL) — a pooled receipt uses the
  same signing key and the same redemption rules, extended to N members;
- **a pooled handle redeems through `story done --verify-handle` /
  `epic done --verify-handle` ONLY.** An earlier draft promised "`task done
  --verify-handle` accepts either; a pooled handle redeems against every
  listed member in one transaction" — that clause is removed: the handle is
  single-use, so a per-task redemption would spend the whole cohort's
  receipt on one member and refuse the rest. Ad-hoc cohorts without a
  parent close per task through their own single-task runs;
- per-unit provenance granularity (v75): the recorded unit is the
  **cohort-union-scope** unit, `covered_by` naming every member and
  `inputs_digest` carrying the delegated run's `files_hash` (or the
  identity's content digest). Per-test provenance is a declared non-goal —
  a pooled run is one gate pass, and fragmenting it into per-test rows
  would re-create the per-task duplication this contract exists to cut.

## Rollout proof (measured, session #295, live corpus)

The seven tasks of this release's Track A/C work were verified twice —
once the old way, once pooled — on the same evening, same tree class:

- **Baseline (per-task scoped runs, recorded)**: 34 executions,
  1,492.1 s total — an average of 4.9 verify executions per task; this is
  the 60.7%-duplicate economy the baseline script measures, lived.
- **Pooled (`verify --tasks <all seven>`)**: ONE execution over the 44-file
  union scope, 314.6 s wall including fixed preparation. **The saving:
  34 → 1 executions (34×), 1,492.1 s → 314.6 s (4.7×), ~19.6 min returned.**
- **The red path ran live too**: pooled runs #3587/#3588 went red on the two
  preparation gates (`ruff_format`, `bootstrap_drift`) — the pooled lane had
  skipped preparation; after fixing, run #3589 went green. Two contract
  corrections came out of it, both now load-bearing code: the pooled lane
  pays the same fixed preparation as the single-task lane, and only GREEN
  evidence is refused reuse (a red predecessor with a different identity is
  the next attempt, not a dead end — otherwise fixes, which change the
  tree, would make a red cohort unfixable).
- The fine-grained incremental set (previous failures ∪ affected-by-delta)
  is a pure function proven by unit tests (`required_after_red`); the live
  proof above exercises gate-level red-then-fix. Per-test carry-forward
  composes green evidence only when its recorded inputs still match.

When task-level affected tests remain required: a single task's closure
(`verify --task`), security-sensitive scopes (never pooled silently), and
any cohort whose dependency mapping is uncertain. Pooling applies when ≥2
review-ready tasks share a lane — release stories above all.

## Out of scope

Gate implementation of pooling itself (receipts task), hierarchy semantics
(story/epic close task), and the rollout proof live in the three follow-up
tasks named above.
