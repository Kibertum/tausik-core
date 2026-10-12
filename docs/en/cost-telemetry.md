**English** | [Русский](../ru/cost-telemetry.md)

# Cost Telemetry — Per-Task Token Attribution

<!-- doc-map: reader=user; zone=quality -->

TAUSIK records LLM usage in two places that work together:

| Table | Source | Granularity | When |
|---|---|---|---|
| `session_usage_metrics` | `scripts/hooks/session_metrics.py` | per-session rollup | SessionEnd |
| `usage_events` | `scripts/hooks/posttool_usage.py` (v1.4) | per-tool-call | PostToolUse |

The session rollup answers "how much did this session cost?" The per-tool ledger answers "how much did this *task* cost?" — needed for the model-recommendation banner, per-task budgets, and the cost dashboard.

## Per-tool ledger

Every tool call (Read, Edit, Bash, MCP, etc.) triggers `posttool_usage.py`. The hook:

1. Reads the harness payload from stdin.
2. Pulls `tool_name` and (best-effort) `tool_response.usage.input_tokens` / `output_tokens` / `model`.
3. Looks up the active task — single row in `tasks WHERE status='active'`. If zero or more than one, attribution is `NULL`.
4. Computes `cost_usd` via `cost_pricing.calculate_cost_usd()`.
5. Inserts a `usage_events` row with `source='posttool'`.

Failures never block the harness. Five graceful-degradation paths are tested:

- malformed stdin JSON,
- no active task (writes `task_slug=NULL`),
- unknown `model_id` (writes `cost_usd=0` + stderr warning),
- locked database (3-attempt retry, then stderr warning),
- no `.tausik/tausik.db` (silent exit 0).

## Querying

```bash
.tausik/tausik metrics cost                       # rollup per task_slug
.tausik/tausik metrics cost --since 2026-05-01    # window
```

`metrics cost` excludes rows where `task_slug IS NULL` from the per-task table, so no-active-task
events neither pollute attribution nor double-count. Since v48 they are no longer invisible: an
explicit «вне задачи» bucket is printed below the table — how many such events, their tokens and
cost, and how many of them had no session either. It prints even when the per-task table is empty.

## Schema

`usage_events` (since v1.4 / migration v24; `session_id` relaxed by migration v48):

| column | type | notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | |
| `session_id` | INTEGER NULL | FK → sessions(id) ON DELETE SET NULL; NULL when no session is open (v48) |
| `task_slug` | TEXT NULL | FK → tasks(slug); NULL when no/multiple active task |
| `model_id` | TEXT NULL | canonical Anthropic model id |
| `tokens_input` / `tokens_output` / `tokens_total` | INTEGER ≥ 0 | |
| `cost_usd` | REAL ≥ 0 | computed at insert time |
| `tool_calls` | INTEGER ≥ 0 | always 1 for posttool rows |
| `source` | TEXT | `session_record` / `manual` / `posttool` |
| `recorded_at` | TEXT | ISO-8601 UTC |
| `tool_name` | TEXT NULL | `Read`, `Edit`, `Bash`, MCP method, … |

## Pricing

`scripts/cost_pricing.py` is the single source of truth. Update both this module and `docs/{en,ru}/cost-telemetry.md` when Anthropic pricing changes.

## Per-task cost / token budget (v14c-token-budget-task)

Sister to `call_budget` — sets a runaway-protection cap on USD spend or token total per task.

```bash
# Plan: 1.20 USD and 50k tokens for a complex refactor.
tausik task add "Token-budget feature" --slug v14c-token-budget-task \
    --cost-budget 1.20 --token-budget 50000 --complexity complex

# Tighten or relax later.
tausik task update v14c-token-budget-task --cost-budget 2.50

# Detail view shows actual / budget once events accrue.
tausik task show v14c-token-budget-task
# → cost: actual=$0.4321 / budget=$1.2000
# → tokens: actual=12000 / budget=50000
```

**Schema (v27):** four nullable columns on `tasks`:

| Column | Type | Set by | Read by |
|---|---|---|---|
| `cost_budget_usd` | REAL | `task add/update --cost-budget` | hook + `task_done` |
| `cost_actual_usd` | REAL | `record_cost_actual` at `task_done` | `task show` |
| `token_budget` | INTEGER | `task add/update --token-budget` | hook + `task_done` |
| `tokens_actual` | INTEGER | `record_cost_actual` at `task_done` | `task show` |

**Two enforcement points:**

1. **`task_done`** — `service_recording.record_cost_actual` rolls up `usage_events` for `task_slug = <slug>` since `started_at`, writes `cost_actual_usd` / `tokens_actual` to the row, and emits a `WARNING:` line to the done message when actual exceeds 1.5× the budget (cost or tokens — independent triggers).
2. **PostToolUse hook `task_cost_budget_check.py`** — runs after every tool call; same rollup; emits one stderr line per tool call when the active task crosses a threshold:
   - `[TAUSIK cost-budget WARN]` at ≥ 1.5× budget AND < 2.0× — soft cap, advisory.
   - `[TAUSIK cost-budget BLOCKER]` at ≥ 2.0× budget — hard cap. The agent reads the line next turn and is expected to stop, re-plan, or run `tausik task update --cost-budget` to widen the cap. (Hooks can't physically block Claude Code; this is soft refuse.)

   Each `(slug, level)` pair is throttled to one emission per 30 seconds via atomic write to `.tausik/.cost_budget_throttle.json`. The hook is silent when:
   - `TAUSIK_SKIP_HOOKS=1`
   - 0 active tasks (no attribution target)
   - ≥ 2 active tasks (multi-agent ambiguity — same policy as `task_call_counter`)
   - The single active task has neither `cost_budget_usd` nor `token_budget` set
   - DB is missing or locked

**Out of scope (separate tasks):** session-level token cap (mirror of `session_capacity_calls`), HUD/status display of tokens-vs-budget, token-tier mapping in `/plan` SKILL.md.

## The cost of a task, in turns

```bash
python scripts/turn_economy.py          # the report
python scripts/turn_economy.py --json   # the same, machine-readable
```

**Why the unit is a TURN, not a request.** Across 5,964 telemetry rows the input side is 99.5%
`cache_read`: 2,876,911,173 tokens against 22,099 of fresh input. The prefix is re-sent whole on
every call, so an extra CALL costs about 482,000 tokens while shortening a request saves
hundreds. An edit that trims the request and adds a turn loses by roughly a hundred to one.

**What the measurement says** (1,230 closed tasks carrying a `call_actual`): median 20 turns, p90
78, max 1,900. By month: 2026-04 median 6 → 2026-09 median 32, p90 35 → 114. In tokens, 9.6M for
the median task and 37.6M at p90.

**Where the turns go** (8,195 measured calls): `Bash` 87.6% and 3.64 of 4.07 billion
`cache_read`, `Write` 7.7%, `Edit` 2.7%, everything else together under 2%.

Both halves are LOCAL: `call_actual` lives in this project's database and the sidecar is written
by a hook on this machine. Neither travels, so on a fresh clone the report says absence in words
rather than printing a zero.

## Native Codex and Kilo reports (1.11)

```bash
tausik metrics tokens --host codex --json
tausik metrics tokens --host kilo --json
```

CLI and `tausik_metrics({"host": "codex" | "kilo"})` call the same reporting
implementation. A missing source returns `source_available: false` and unknown
counters instead of zero.

The Codex adapter follows explicit `task start` / successful `task done`
boundaries in native response order. It includes failed closure attempts and
their rework, then admits a task to `accepted_task_cost` only when project state
says `done`. Each task reports response rounds, input/cached/output/reasoning,
attempts/retries and observed model/reasoning/speed identity. Fork history,
nested or incomplete windows and responses outside a boundary remain
unattributed. Commands and tool output are inspected transiently for lifecycle
success markers and are never persisted in the cache.

The Kilo adapter reads its documented local SQLite store in read-only mode. It
selects only response identity, provider/model/version and the five token counters;
prompts, tool payloads, credentials and raw project paths never enter the project
cache. Kilo stores plain input, cache read, cache write, plain output and reasoning as
disjoint counters, so TAUSIK reconstructs common input and output totals before
reporting them. Incremental reads key responses by identity and update timestamp;
session aggregates provide an independent reconciliation check.
Completed and failed assistant records are reported separately, so an API error with
zero tokens cannot be mistaken for a successful GLM run.

Kilo does not expose account subscription quota through this store. The report keeps
`account_quota: null`, applies no price table and makes no savings claim. Provider API
documentation about cached tokens does not prove that a particular host surfaced the
same value. Task attribution is also unknown because Kilo responses do not carry a
TAUSIK task slug.

## Natural project cohorts (1.11.1)

`tausik metrics cohorts` (or `tausik_metrics({"view":"cohorts"})`) inventories
real accepted work before any comparison. Native Codex/Kilo reads upsert only
normalized response evidence to `benchmark_observations`; repeated reads converge
by an opaque response hash, while a finalized native response replaces its earlier
partial counters. The ledger stores identity provenance and input,
cached-input, cache-write, output and reasoning-output counters. It never stores
prompts, responses, tool payloads, credentials or raw transcript paths.

Matching task start and completion boundaries supply the TAUSIK version. Missing
or different boundaries remain `legacy/unclassified`; the importer never guesses
which side of an upgrade produced a response. Cohorts split when host, provider, model, reasoning
effort or speed mode changes. Only `done` tasks without an obsolete resolution
count as accepted. Failed attempts and every review/verification run remain inside
the task evidence. Task-level evidence for work spanning more than one identity is
reported once in the unsplit bucket instead of being charged to every cohort.
Inexact work and exact work that has not been accepted are separate visible buckets.

Missing identity, counters, task linkage or quality evidence stays `null` and
reduces coverage. Cached input is a subset of input and reasoning output is a
subset of output; neither is added to its parent total. The inventory includes
sample dates, task counts, attribution coverage, attempts/retries, verification
outcome and review depth/invocations. It calculates no API-equivalent USD and
makes no savings claim; pricing belongs to the subsequent comparison task.
Elapsed start-to-completion time is not active duration; active duration stays
unknown unless a source measured it.

### Compare two natural cohorts

Work normally on one TAUSIK version, upgrade, and keep working normally. After
both sides have enough accepted tasks, compare the naturally accumulated
cohorts. Do not buy repeated runs, replay prompts, execute a synthetic corpus,
or fill a version×model matrix.

```bash
# Same observed model, before and after an upgrade.
tausik metrics compare \
  --left-label before --left-version 1.11.0 --left-model gpt-5 \
  --right-label after --right-version 1.11.1 --right-model gpt-5 \
  --minimum-sample 5 --save .tausik/reports/1.11.0-vs-1.11.1.json

# Same TAUSIK version, two models that the project actually used.
tausik metrics compare \
  --left-version 1.11.1 --left-model gpt-5 \
  --right-version 1.11.1 --right-model gpt-6
```

`tausik_metrics` exposes the same operation with `view="comparison"` and a
`compare` object containing `left`/`right` selectors. Selectors accept `tausik_version`, `provider`,
`model`, `reasoning_effort`, `speed_mode`, `since`, `until`, and a display
`label`. A complete Cartesian matrix is never required.

The report aggregates responses per task before calculating median and p90.
It shows coverage for response rounds, tool calls, measured active duration,
attempts/retries, total/cached/uncached input, output, reasoning-output subset,
and total tokens (`input + output`). Cached input remains part of input and
reasoning remains part of output, so neither subset is double-counted.

API-equivalent USD is optional and never means subscription spend, credits, or
remaining quota. Supply a dated provider table in `.tausik/config.json`:

```json
{
  "api_equivalent_usd_rate_card": {
    "source": "https://provider.example/pricing/2026-10-01",
    "as_of": "2026-10-01",
    "valid_until": "2026-12-31",
    "unit": "usd_per_million_tokens",
    "models": {
      "openai/gpt-5": {
        "uncached_input": 1.25,
        "cached_input": 0.125,
        "output": 10.0
      }
    }
  }
}
```

Use the provider's dated rates; the numbers above only illustrate the schema.
An absent, invalid, expired, or unmatched card yields `null`, never zero.
Subscription credits and included quota remain separate unknown fields.

Quality stays beside cost: verification failure/retry rates, L1/L2/L3/deep
review mix, reviewer invocations, confirmed critical/high findings, and defect
escapes after the declared maturation window. Complexity, assurance profiles,
and impact form strata. Different pooled task mixes produce a warning. Small
samples, mixed model/settings, or simultaneous version and model changes make
the result `inconclusive`; the report never turns an observational difference
into a causal savings claim or a universal efficiency score.

A saved snapshot contains the selectors, coverage, price provenance, exact
version/model identities, opaque cohort-membership hashes, and generation
time. It omits task names and raw conversation content.

## Limitations

- **Session tokens recorded before 1.10 are overstated and are not re-derived**. Claude Code writes one API message with N content blocks as N transcript entries carrying the same usage, and the meter added it N times: 1.81x on the replay transcript of session #263. Since 1.10 usage is counted once per message id. The overstatement depends on the block count, so old rows cannot be divided by a constant; do not compare them with new ones.
- **`tausik metrics tokens` does not attribute cost per tool, and says so before
  it shows you anything.** API usage is reported per *message*, not per tool
  call — the capture hook states this about itself. What reaches
  `.tausik/token_metrics.jsonl` is a message-level figure stamped onto whichever
  tool happened to run, so `in_p50` and `in_p90` come out near-identical for
  every tool, `in_total` tracks the call count, and summing `cache_read`
  re-counts one cached conversation on every call. Read the table as **call
  volume**, which it measures honestly. Attributing spend per tool needs a
  transcript-level parser that does not exist yet. This is also why the
  sub-agent token question was never answerable: `Agent` invocations record ~2
  input tokens, so a sub-agent's own consumption is invisible here.
- Token counts only land when the harness actually exposes `tool_response.usage`. Claude Code currently emits this for some tools but not all; rows without usage still get written with `tokens=0` so the call count is preserved.
- Multi-active-task projects (rare) lose per-task attribution — `task_slug` is `NULL` and the event survives in `metrics cost --no-task-only` style queries (TODO).
- Migration v24 rebuilds `usage_events` via a temp table to extend the `source` CHECK and add `tool_name`. Existing rows survive but back-fill `tool_name=NULL`.
