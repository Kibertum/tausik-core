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

## Limitations

- Token counts only land when the harness actually exposes `tool_response.usage`. Claude Code currently emits this for some tools but not all; rows without usage still get written with `tokens=0` so the call count is preserved.
- Multi-active-task projects (rare) lose per-task attribution — `task_slug` is `NULL` and the event survives in `metrics cost --no-task-only` style queries (TODO).
- Migration v24 rebuilds `usage_events` via a temp table to extend the `source` CHECK and add `tool_name`. Existing rows survive but back-fill `tool_name=NULL`.
