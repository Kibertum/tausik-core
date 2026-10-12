# Codex economy baseline for 1.11

**English** | [Русский](../ru/codex-economy-baseline.md)

<!-- doc-map: reader=maintainer; zone=reference -->

`tausik metrics tokens --host codex --json` and MCP `tausik_metrics(host="codex")`
read native local Codex journals. The incremental cache is local at
`.tausik/usage-codex.sqlite`; it contains allowlisted counters and opaque IDs,
not prompts or tool output. Repeating a scan reads only complete appended lines.
Deleting the cache rebuilds it from source without altering the source.

Response records take precedence over cumulative fallback; they are not added
together. Fork history is deduplicated by response ID and inherited records are
not assigned to the child's project. Cumulative-only data is explicitly
unattributed. Project matching uses the recorded working directory exactly;
subdirectory ambiguity and missing task linkage are not guessed away. Conflicts,
malformed records, source coverage and counter resets remain visible. A report
with unreliable totals cannot substantiate savings. Local source absence means
unknown usage. Quota is account-wide: read its observation time and reset before
using it; an old snapshot is not current remaining allowance.

## Frozen comparison protocol

Baseline revision: `72862321c50a1dc47005c551d719734a1b8d31be` (before 1.11
economy changes). Native instrumentation is additive and does not change model
prompts. Baseline capture: 2026-10-01. Primary host/model: Codex / gpt-6-astra;
hold reasoning effort, speed mode, tool catalog and user specification fixed
per matched pair. Any unknown or changed setting makes the pair inconclusive.

Use six isolated tasks, two per complexity, with these independent acceptance
families frozen before context/workflow optimization:

| Case | Complexity | Task | Independent acceptance |
|---|---|---|---|
| S1 | Simple | Reject malformed/missing usage without fabricating zero | counter and privacy cases in `tests/test_usage_observation.py` |
| S2 | Simple | Preserve model identity across configured/observed values | `tests/test_model_profiles.py` plus observation provenance cases |
| M1 | Medium | Select impacted behavior tests without losing consumers | `tests/test_gate_test_resolver.py` |
| M2 | Medium | Refuse stale or incomplete verification evidence | `tests/test_verify_handle.py` |
| C1 | Complex | Upgrade an existing database with preserved data | `tests/test_migrations.py` |
| C2 | Complex | Exercise verification and closure through the real service | `tests/test_verify_handle_integration.py` |

For each case record response IDs/rounds, input/cache/output/reasoning separately,
acceptance result, review findings and rework. Task cost requires an explicit
response set, not the active task or a broad session-time allocation. Reuse
normal development work where a matched case is available. Do not launch paid
model fan-out to fill the table. Maximum benchmark: one baseline and one candidate
attempt per case; a failed or ambiguous pair is reported, not rerun until green.
Independent checks are held fixed for comparison; test-suite deletions do not
delete this acceptance evidence.

The shared `summarize_accepted_tasks` contract accepts only exact task-attributed
response records, deduplicates response IDs and reports retries from task attempts.
Its comparable total is input plus output. Cached input and reasoning output are
reported as subsets and are never added again. Missing counters leave a task
unmeasured rather than turning the gap into zero.

Initial six-case token/rework cells are **unmeasured**, not zero. The live
reconciliation proves native counters can be collected, not that these six
matched tasks have been run. Their model-driven quality/economy comparison is
the release acceptance task; until then there is no savings claim. Acceptance
target: at least 30% fewer measured tokens per accepted fixed-model task with
no degraded failure detection. This is not a quota or price multiplier.

The first live project capture found 98 native responses: 11,815,495 input,
11,389,952 cached-input subset, 79,184 output and 13,510 reasoning-output subset.
These are project observations with unknown per-task attribution. Of 39 source
files, 27 had native response records; 1,054 other/unattributed responses were
excluded from the project total. The account quota snapshot covered all projects.

## Subscription-credit weighting

Raw counters remain the evidence. A project may additionally configure
`codex_subscription_credit_rates` to compare accepted work using the current
ChatGPT/Codex credit rate card. TAUSIK ships no default card because rates and
availability change. The card must name `source`, `as_of`, the unit
`credits_per_million_tokens`, and rates for uncached `input`, `cached_input`,
and `output` under model prefixes.

The report subtracts cached input from total input, applies the cached rate to
that subset, and prices total output once; reasoning output is displayed but is
not added again. Missing counters, malformed cards and unknown models produce
an explicit unknown credit result while leaving raw telemetry intact. Credits
are not API dollars, remaining included allowance, or guaranteed task counts.
