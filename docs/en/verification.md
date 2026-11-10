# Adherence verification

**English** | [Русский](../ru/verification.md)

<!-- doc-map: reader=maintainer; zone=quality -->

TAUSIK 1.11.8 defines a machine-readable adherence contract before it adds
Codex enforcement. The baseline is intentionally red: it proves that the
evaluator rejects missing identity, incomplete context, skipped memory,
broken continuity and premature completion. A red baseline is not evidence
that runtime enforcement already exists.

The public contract facade lives in `scripts/adherence_contract.py`. Its
policy, live registry, runtime recorder and evidence evaluator are split across
the adjacent `adherence_policy.py`, `adherence_registry.py`,
`adherence_runtime.py` and `adherence_evidence.py` modules. The evaluator hash
covers all five source files. Frozen policy, event cohorts, manifest and
baseline evidence live in
`tests/fixtures/adherence/`. The route registry is generated from the live
service, CLI, MCP and hook dispatch surfaces; the manifest pins its canonical
hash so surface drift fails verification.

## Frozen thresholds

| Metric | Release threshold |
|---|---:|
| Valid execution leases | 100% |
| Complete task packages | 100% |
| Required continuity events | 100% |
| Protected memory preflights | 100% |
| Active dead-end repeats without override | 0 |
| Premature stops | 0 |
| Correct hard-ceiling handoff resumes | 100% |

A rate with a zero denominator fails. Zero collected events cannot produce
release evidence.

## Event and route contract

Events use an allowlist-only schema. They carry opaque hashed identifiers,
route, boundary, kind, closed result, policy version and sequence. They do not
carry messages, details, prompts, command bodies or arbitrary prose.

The generated route registry classifies governed service, CLI, MCP and hook
entry points as `read`, `mutation`, `protected` or `stop`. Read routes use a
closed exact allowlist; every unknown route fails closed as a mutation. The
registry names required and conditional obligations. Validation groups events
by action and requires that action's exact ordered obligations. An unknown
route, mismatched boundary, missing or extra obligation, cross-action identity,
duplicate identifier or reordered sequence invalidates the cohort.

Changing the policy or registry requires both a policy-version increment and
an L3 review. The manifest pins their canonical SHA-256 hashes.

## Two distinct phases

The negative-control phase executes sixteen sentinels: one failing result for
each metric, one absent event for each event kind, plus duplicated and
reordered events. Evidence is produced only after every sentinel executes and
is rejected. A sentinel that is accepted or not executed fails the phase.

The acceptance phase uses events emitted through `AdherenceRecorder`, the
public producer intended for TAUSIK entry points. The pre-enforcement red
baseline probes real service, CLI, MCP and hook entry points, rejects failed
native calls and records an invocation census. It deliberately records zero
events when current entry points emit none; a census/event mismatch is the red
result. The frozen red event baseline is a separate deterministic arithmetic
cohort and does not itself prove probe provenance. Hand-authored events are
permitted only in isolated contract mutation tests.

Boundary-specific probe adapters derive routes from bound service methods,
parsed CLI commands, MCP tool names and hook matcher metadata. Each census row
records the emitted event count and digest. The evidence contract bundle binds
the frozen census hash. Hook probes use a temporary JSONL sink across the
subprocess boundary. Acceptance requires every census row to reconcile with
the corresponding action events; a green arithmetic cohort cannot override
zero real emissions.

Evidence records the declared base commit and hashes for the evaluator,
contract bundle, policy, registry and fixture. The base commit identifies the
starting point; this baseline does not claim that the uncommitted contract
already exists in that Git tree.
collected, passed, failed and deselected counts; every metric verdict; and a
hash of the evidence itself.

## Privacy check

The baseline validates a four-sink canary scanner. The 1.11.8 release gate must
collect and pass the real database, stdout, stderr and JSON evidence sinks;
this baseline alone does not prove release-pipeline coverage. All four scanner
inputs are mandatory. The event schema cannot be extended with free-text
fields without a policy change.

Run the focused contract suite:

```text
pytest -q tests/test_adherence_contract.py
```
