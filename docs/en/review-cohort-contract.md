# Bounded L3 Review Cohort Contract (1.11.5)

**English** | [Russian](../ru/review-cohort-contract.md)

<!-- doc-map: reader=agent; zone=quality -->

SPEC `bounded-l3-review-cohort` · status implemented · task
`r1115-l3-cohort-contract` → implemented by
`r1115-l3-cohort-receipts` and accepted by
`r1115-l3-workflow-economy-acceptance`.

## Why

The current close gate binds the latest L3 record to the task contract and
reviewed file bytes. A repair therefore makes the record stale. The next
review can discover another issue, producing an unbounded review/repair loop.
The gate is professionally conservative but operationally unbounded.

`scripts/review_baseline.py` measures the local history without inventing
missing telemetry. On 2026-10-13 this repository contained 55 L3 records.
The most-reviewed tasks paid five L3 records each; structured token telemetry
was unavailable for the sampled L3 records. A user's observed 25-pass loop is
the motivating external report, not a number claimed by this repository.

| Natural cohort | Cohorts / task seats | L3 records | Measured reviewer calls | Repeated task reviews | Token coverage |
|---|---:|---:|---:|---:|---:|
| 1 task | 21 / 21 | 36 | 24 (18/36 records) | 15 | 0/36 |
| 2 tasks | 2 / 4 | 4 | unavailable | 0 | 0/4 |
| 3–4 tasks | 2 / 7 | 10 | unavailable | 3 | 0/10 |
| 5+ tasks | 1 / 5 | 5 | unavailable | 0 | 0/5 |

These are descriptive historical rows, not projected savings. Older records
store `reviewer_invocations=0`; the baseline reports those calls as unavailable
rather than interpreting zero as a free review.

The replacement bounds automatic reviewer work without treating an unresolved
blocking finding as green.

## Components and data flow

```text
task/story/epic selection
          │
          ▼
review cohort identity ──► round 1 packet ──► external L3 reviewer
          │                                      │
          │                              task-indexed verdicts
          │                                      │
          ├── unchanged GREEN ◄──────────────────┤
          │                                      ▼
          └── RED ∪ affected-by-delta ──► round 2 packet
                                                 │
                                  composite review receipt
                                                 │
                         task/hierarchy close or owner decision
```

The verification cohort remains a separate subsystem. Review cohorts reuse
its identity and invalidation concepts, not its deterministic gate receipt.

## Canonical selection

One request supplies exactly one selector: an explicit task list, one story,
or one epic. Task lists reject missing slugs and deduplicate before sorting.
Hierarchy selectors expand to non-done descendants, then sort by slug. An
empty expansion is refused.

Candidates must be `active` or `review`, have complete plan steps and AC
evidence, and have an effective normal-L3 route. A not-ready L3 candidate
blocks opening and names the missing condition. L1/L2 candidates are reported
as `review_not_required` and stay outside the cohort. An L3-deep route is not
silently mixed with normal L3; it requires the explicit deep workflow. These
rules produce the same member set for CLI and MCP.

## Identity and receipts

A review has two identities instead of one hash that repairs would destroy:

- **cohort key** — stable across its two rounds: selector kind/value, sorted
  eligible membership, per-member route signature, review-policy signature,
  and opening repository lineage;
- **issued packet digest** — immutable evidence binding: repository HEAD plus
  each participating task's contract, numbered AC evidence, relevant-file
  hashes, dependency edges, route/risk, and trusted author provenance.

The stable cohort key is the SHA-256 of canonical JSON containing:

1. normalized selector and sorted eligible membership;
2. each member's normal-L3 route signature;
3. reviewer-separation requirements and review-policy signature;
4. the repository lineage at cohort open.

Each issued packet is inserted once and cannot be overwritten. `cohort-record`
must return its exact digest; task, file, dependency, route, policy, AC-evidence
or scoped repository drift is refused. A repair happens before the round-2
status call issues its packet. Drift of an already-issued active packet
invalidates that generation and opens a fresh one instead of rebinding a
verdict to unseen state.

The cohort envelope stores the identity and round state. Each member stores a
task-indexed verdict, severity counts, reviewed-state fingerprint, reviewer
identity, and whether its evidence was executed or carried forward. A cohort
receipt never converts one task's verdict into another task's evidence.

## Two-round state machine

```text
OPEN → ROUND_1_FULL → GREEN
                    ↘ RED → REPAIR → ROUND_2_DELTA → GREEN
                                                   ↘ OWNER_DECISION
```

- Round 1 reviews every eligible member once.
- The round-1 verdict is recorded before any repair. Only then may repair and
  deterministic verification precede issuance of the round-2 packet.
- `HIGH` or `CRITICAL` makes that member red. `MEDIUM` and `LOW` are recorded
  as warnings and never block closure.
- Round 2 contains exactly the prior red members union members affected by
  changes after round 1.
- An unchanged green member is carried forward without a reviewer invocation.
- Round 2 is terminal for automation. TAUSIK never schedules round 3.
- A round-2 `HIGH`/`CRITICAL` produces one owner action: accept the documented
  risk, request a manual audit, or continue repair without automatic closure.

Explicit human-requested `/review --deep` is outside the automatic budget. It
may add evidence and supersede a blocking task verdict, but automation cannot
invoke it to evade the two-round cap.

## Affected-member rule

The round-2 set is:

```text
round_1_blocking_members ∪ members_affected_by_post_round_1_delta
```

A task is affected when its contract or relevant files changed, or when a
changed shared file has a declared dependency edge to it. If dependency
mapping is missing or stale, the system widens to every member whose scope may
contain the change. Unknown is never treated as unaffected.

Membership or policy drift opens a new cohort; it does not silently mutate an
existing receipt. New membership does not erase still-current task-indexed
green evidence, but hierarchy closure requires a receipt covering every live
member.

## Closure and owner decision

Closure accepts a current composite receipt when every member is green,
advisory-only, or has a policy-valid `ACCEPTED_RISK` disposition. After round
2, unresolved blocking findings set `OWNER_DECISION` and stop automation. The
owner chooses one terminal transition:

1. `ACCEPTED_RISK`: store owner identity, reason, finding references, time and
   policy result; closure is allowed only when project policy makes the
   severity waivable. Critical/hard-floor findings are non-waivable by default;
2. `AWAITING_MANUAL_REVIEW`: leave tasks open; only an explicit valid manual
   receipt created strictly after the owner disposition may supersede it;
3. `REPAIR_OPEN`: leave tasks open with no automatic reviewer scheduled. A
   later owner action may open a new cohort or request manual review.

Risk acceptance is evidence, not erasure: the finding and its severity remain
visible. The implementation must preserve any non-waivable project policy.

## Compatibility and non-goals

- Existing single-task `review record` and `task done` continue to work.
- `review list/metrics` combine legacy rows with executed cohort results;
  carried-forward rows are excluded because they are not reviewer executions.
- Existing review rows remain readable and act as single-member evidence when
  their current binding is valid.
- Deterministic pooled verification and its signed handles do not change.
- Severity definitions do not change.
- Per-finding issue tracking, semantic dependency inference, and automatic
  rewriting of reviewer findings are out of scope for 1.11.5.

## Economy and communication acceptance

`scripts/review_economy.py` compares the declared one-repair acceptance case.
These are exact protocol counts, not historical savings or model-latency
measurements:

| Tasks | Legacy reviewer calls | Bounded calls | Legacy green re-reviews | Bounded green re-reviews |
|---:|---:|---:|---:|---:|
| 1 | 2 | 2 | 0 | 0 |
| 2 | 4 | 2 | 1 | 0 |
| 5 | 10 | 2 | 4 | 0 |

This is a worked protocol model, not measured savings. External reviewer
latency and token telemetry are unavailable, so the report says `unavailable`
and does not estimate them.

User output has one compact denominator and one action:

```text
L3 cohort: 5 tasks · green 3 · advisory 0 · accepted-risk 1 · red 1 · carried 3 · rounds 2/2
Owner action: accept risk, request manual review, or keep the task open.
```
