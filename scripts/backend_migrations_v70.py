"""Migration v70: privacy-safe natural-work benchmark cohorts."""

MIGRATION_V70 = [
    "ALTER TABLE tasks ADD COLUMN started_tausik_version TEXT",
    "ALTER TABLE tasks ADD COLUMN done_tausik_version TEXT",
    """CREATE TABLE IF NOT EXISTS benchmark_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_key TEXT UNIQUE NOT NULL,
        task_slug TEXT REFERENCES tasks(slug) ON DELETE SET NULL,
        tausik_version TEXT,
        observed_at TEXT,
        host TEXT, host_version TEXT, provider TEXT, model TEXT,
        reasoning_effort TEXT, speed_mode TEXT,
        attribution_confidence TEXT NOT NULL
            CHECK(attribution_confidence IN ('unknown','project','exact')),
        response_rounds INTEGER CHECK(response_rounds IS NULL OR response_rounds >= 0),
        tokens_input INTEGER CHECK(tokens_input IS NULL OR tokens_input >= 0),
        tokens_cached_input INTEGER
            CHECK(tokens_cached_input IS NULL OR tokens_cached_input >= 0),
        tokens_cache_write INTEGER
            CHECK(tokens_cache_write IS NULL OR tokens_cache_write >= 0),
        tokens_output INTEGER CHECK(tokens_output IS NULL OR tokens_output >= 0),
        tokens_reasoning_output INTEGER
            CHECK(tokens_reasoning_output IS NULL OR tokens_reasoning_output >= 0),
        tool_calls INTEGER CHECK(tool_calls IS NULL OR tool_calls >= 0),
        active_duration_ms INTEGER
            CHECK(active_duration_ms IS NULL OR active_duration_ms >= 0),
        source_format TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        CHECK(tokens_cached_input IS NULL OR tokens_input IS NULL
            OR tokens_cached_input <= tokens_input),
        CHECK(tokens_reasoning_output IS NULL OR tokens_output IS NULL
            OR tokens_reasoning_output <= tokens_output)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_benchmark_task ON benchmark_observations(task_slug)",
    "CREATE INDEX IF NOT EXISTS idx_benchmark_cohort ON benchmark_observations(tausik_version, host, provider, model, reasoning_effort, speed_mode)",
    "CREATE INDEX IF NOT EXISTS idx_benchmark_observed ON benchmark_observations(observed_at)",
]
