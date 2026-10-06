"""Migration v75: pooled-verification cohort storage (Track A, 1.11.3).

r1112-cohort-receipts-and-incremental-rerun, per SPEC
verification-cohort-contract §5. Backward compatible by construction:
`verification_runs` gains one NULLable column (existing rows read as
cohorts of one), and the two new tables carry what a pooled run needs that
a single-task run never had — membership with the identity inputs it was
admitted under, and per-test outcomes with the dependency digest each green
claim rests on.
"""

MIGRATION_V75: list[str] = [
    "ALTER TABLE verification_runs ADD COLUMN cohort_identity TEXT",
    """CREATE TABLE IF NOT EXISTS verification_cohorts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identity TEXT NOT NULL UNIQUE,
        members_json TEXT NOT NULL,
        identity_inputs_json TEXT NOT NULL,
        union_files_hash TEXT NOT NULL,
        gate_signature TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'open'
            CHECK(state IN ('open', 'green', 'red')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS verification_cohort_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cohort_pk INTEGER NOT NULL
            REFERENCES verification_cohorts(id) ON DELETE CASCADE,
        unit TEXT NOT NULL,
        outcome TEXT NOT NULL CHECK(outcome IN ('passed', 'failed', 'skipped')),
        covered_by TEXT,
        inputs_digest TEXT NOT NULL,
        ran_at TEXT NOT NULL,
        UNIQUE(cohort_pk, unit)
    )""",
]
