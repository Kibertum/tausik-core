# Cost Telemetry — Per-Task Token Attribution

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

`metrics cost` excludes rows where `task_slug IS NULL`, so no-active-task events stay in the ledger but don't pollute attribution.

## Schema

`usage_events` (since v1.4 / migration v24):

| column | type | notes |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | |
| `session_id` | INTEGER NOT NULL | FK → sessions(id) |
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

## Limitations

- Token counts only land when the harness actually exposes `tool_response.usage`. Claude Code currently emits this for some tools but not all; rows without usage still get written with `tokens=0` so the call count is preserved.
- Multi-active-task projects (rare) lose per-task attribution — `task_slug` is `NULL` and the event survives in `metrics cost --no-task-only` style queries (TODO).
- Migration v24 rebuilds `usage_events` via a temp table to extend the `source` CHECK and add `tool_name`. Existing rows survive but back-fill `tool_name=NULL`.
