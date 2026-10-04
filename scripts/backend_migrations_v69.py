"""Migration v69: structured residual-assurance review records."""

MIGRATION_V69 = [
    """CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        run_type TEXT NOT NULL CHECK(run_type IN ('L1','L2','L3')),
        critical_findings INTEGER NOT NULL DEFAULT 0,
        warnings INTEGER NOT NULL DEFAULT 0,
        run_at TEXT NOT NULL,
        notes TEXT
    )""",
    "ALTER TABLE reviews ADD COLUMN high_findings INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE reviews ADD COLUMN profiles_json TEXT",
    "ALTER TABLE reviews ADD COLUMN reasons_json TEXT",
    "ALTER TABLE reviews ADD COLUMN hard_floor TEXT",
    "ALTER TABLE reviews ADD COLUMN author_model TEXT",
    "ALTER TABLE reviews ADD COLUMN reviewer_model TEXT",
    "ALTER TABLE reviews ADD COLUMN reviewer_context TEXT",
    "ALTER TABLE reviews ADD COLUMN reviewer_invocations INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE reviews ADD COLUMN usage_json TEXT",
    "ALTER TABLE reviews ADD COLUMN route_json TEXT",
]
