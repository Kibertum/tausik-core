"""Migration v90: durable L3 infrastructure receipts (TB-009)."""

MIGRATION_V90 = [
    """CREATE TABLE IF NOT EXISTS review_cohort_infrastructure_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cohort_pk INTEGER NOT NULL REFERENCES review_cohorts(id) ON DELETE CASCADE,
        round_number INTEGER NOT NULL CHECK(round_number IN (1, 2)),
        receipt_kind TEXT NOT NULL CHECK(receipt_kind = 'review_infrastructure_blocked'),
        code TEXT NOT NULL,
        reason TEXT NOT NULL,
        detail TEXT,
        packet_digest TEXT NOT NULL,
        recorded_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_review_infra_cohort "
    "ON review_cohort_infrastructure_events(cohort_pk, round_number, id)",
]
