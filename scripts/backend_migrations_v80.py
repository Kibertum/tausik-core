"""Migration v80: immutable review packets and trusted cohort generations."""

MIGRATION_V80: list[str] = [
    "ALTER TABLE review_cohorts ADD COLUMN family_key TEXT",
    "ALTER TABLE review_cohorts ADD COLUMN generation INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE review_cohorts ADD COLUMN parent_cohort_pk INTEGER REFERENCES review_cohorts(id)",
    "UPDATE review_cohorts SET family_key=cohort_key WHERE family_key IS NULL",
    "ALTER TABLE review_cohort_results ADD COLUMN author_model TEXT",
    "ALTER TABLE review_cohort_results ADD COLUMN dependency_map_complete INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE review_cohort_results ADD COLUMN critical_reason TEXT",
    "ALTER TABLE review_cohort_results ADD COLUMN finding_refs_json TEXT",
    """CREATE TABLE IF NOT EXISTS review_cohort_packets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cohort_pk INTEGER NOT NULL REFERENCES review_cohorts(id) ON DELETE CASCADE,
        round_number INTEGER NOT NULL CHECK(round_number IN (1, 2)),
        packet_json TEXT NOT NULL,
        packet_digest TEXT NOT NULL,
        issued_at TEXT NOT NULL,
        UNIQUE(cohort_pk, round_number)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_review_cohort_family ON review_cohorts(family_key, generation DESC)",
    """CREATE TRIGGER IF NOT EXISTS review_cohort_results_counts_insert
        BEFORE INSERT ON review_cohort_results
        WHEN NEW.critical_findings < 0 OR NEW.high_findings < 0 OR NEW.warnings < 0
        BEGIN SELECT RAISE(ABORT, 'review finding counts must be non-negative'); END""",
    """CREATE TRIGGER IF NOT EXISTS review_cohort_results_counts_update
        BEFORE UPDATE OF critical_findings, high_findings, warnings ON review_cohort_results
        WHEN NEW.critical_findings < 0 OR NEW.high_findings < 0 OR NEW.warnings < 0
        BEGIN SELECT RAISE(ABORT, 'review finding counts must be non-negative'); END""",
]
