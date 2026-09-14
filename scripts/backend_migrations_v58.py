"""Migration v58: usage_events can say "not measured" instead of "zero".

Measured on this project in session #231, before anything was designed:

    55,583 usage_events
    55,288 (99.5%) carry tokens_input=0, tokens_output=0, model_id=NULL
    55,471 carry cost_usd=0; NOT ONE carries NULL
         0 tasks have cost_actual_usd > 0; 669 have exactly 0

The cause is not another vendor's payload shape, which is what the task was
raised about. `_extract_usage` read `tool_response.usage` — and a TOOL result
structurally has no usage, because usage belongs to the model's message. Bash
(26,129 rows), Read (7,385), Edit (6,346), Grep, Write and every MCP tool have
never carried it and never will. The only tool that does is `Agent`, 75 rows.

So the product asserted "this work cost $0.00" 55,471 times, on its own vendor,
on its own model. That is decision #334 — a quantity that cannot be measured
yields ABSENCE, not zero — broken at scale inside the very telemetry the release
means to make a claim from.

WHY NULLABLE COLUMNS RATHER THAN A FLAG. SQLite's SUM skips NULL and returns NULL
when every input is NULL. So a task with no measurement rolls up to NULL — "not
measured" — and a task with measurements rolls up over exactly those, with no
consumer needing a special case for the difference. The honest semantics fall out
of the storage instead of being maintained on top of it.

THE CHECKS ARE KEPT. Allowing NULL is not an excuse to stop rejecting a negative
token count: `CHECK(x IS NULL OR x >= 0)` still refuses nonsense. Relaxing one
constraint must not quietly relax its neighbour.

FROZEN LITERAL, NOT AN IMPORT — the rule v52, v56 and v57 all state. The DDL below
is a COPY of the shape as of v58, deliberately not re-extracted from
`backend_schema.SCHEMA_SQL`: reading the live schema would make a later column
addition retroactively change what this migration created.
"""

from __future__ import annotations

#: `usage_events` as it stands from v58 on. A copy on purpose — see the note.
_USAGE_EVENTS_AS_OF_V58 = """CREATE TABLE usage_events_v58 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    model_id TEXT,
    tokens_input INTEGER CHECK(tokens_input IS NULL OR tokens_input >= 0),
    tokens_output INTEGER CHECK(tokens_output IS NULL OR tokens_output >= 0),
    tokens_total INTEGER CHECK(tokens_total IS NULL OR tokens_total >= 0),
    cost_usd REAL CHECK(cost_usd IS NULL OR cost_usd >= 0),
    tool_calls INTEGER NOT NULL DEFAULT 0 CHECK(tool_calls >= 0),
    source TEXT NOT NULL CHECK(source IN ('session_record', 'manual', 'posttool')),
    recorded_at TEXT NOT NULL,
    tool_name TEXT
);"""

#: Rows about which it is PROVABLE that no measurement took place: written by the
#: PostToolUse hook, carrying no model, and zero on both token counts. A row with
#: a model, or with any non-zero number, is left exactly as it is — a real zero is
#: a real measurement and rewriting it would be the same crime in the other
#: direction (AC7).
_UNMEASURED = (
    "source = 'posttool' AND model_id IS NULL "
    "AND COALESCE(tokens_input, 0) = 0 AND COALESCE(tokens_output, 0) = 0 "
    "AND COALESCE(tokens_total, 0) = 0 AND COALESCE(cost_usd, 0) = 0"
)

MIGRATION_V58: list[str] = [
    # The table may not exist on a partial fixture that jumps straight to head.
    """CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
    task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
    model_id TEXT,
    tokens_input INTEGER NOT NULL CHECK(tokens_input >= 0),
    tokens_output INTEGER NOT NULL CHECK(tokens_output >= 0),
    tokens_total INTEGER NOT NULL CHECK(tokens_total >= 0),
    cost_usd REAL NOT NULL DEFAULT 0 CHECK(cost_usd >= 0),
    tool_calls INTEGER NOT NULL DEFAULT 0 CHECK(tool_calls >= 0),
    source TEXT NOT NULL CHECK(source IN ('session_record', 'manual', 'posttool')),
    recorded_at TEXT NOT NULL,
    tool_name TEXT
);""",
    _USAGE_EVENTS_AS_OF_V58,
    # One statement moves every row, so a partial result is not reachable: the
    # id is carried across, so nothing that references a row by id is orphaned.
    "INSERT INTO usage_events_v58 ("
    "id, session_id, task_slug, model_id, tokens_input, tokens_output, "
    "tokens_total, cost_usd, tool_calls, source, recorded_at, tool_name) "
    "SELECT id, session_id, task_slug, model_id, tokens_input, tokens_output, "
    "tokens_total, cost_usd, tool_calls, source, recorded_at, tool_name "
    "FROM usage_events",
    "DROP TABLE usage_events",
    "ALTER TABLE usage_events_v58 RENAME TO usage_events",
    # DROP TABLE took the indexes with it. Recreated by hand rather than left to
    # `ensure_schema`: a rebuild that silently returns the table without its
    # indexes is a rebuild that makes every rollup slower and says nothing.
    "CREATE INDEX IF NOT EXISTS idx_usage_events_session "
    "ON usage_events(session_id, recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_usage_events_task ON usage_events(task_slug, recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_usage_events_tool ON usage_events(tool_name, recorded_at)",
    # Only now, on the table that can hold it, is the absence written down.
    f"UPDATE usage_events SET tokens_input = NULL, tokens_output = NULL, "
    f"tokens_total = NULL, cost_usd = NULL WHERE {_UNMEASURED}",
]
