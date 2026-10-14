"""Migration v79: bounded L3 review cohorts and task-indexed receipts."""

MIGRATION_V79: list[str] = [
    """CREATE TABLE IF NOT EXISTS review_cohorts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cohort_key TEXT NOT NULL UNIQUE,
        selector_kind TEXT NOT NULL CHECK(selector_kind IN ('tasks', 'story', 'epic')),
        selector_value TEXT NOT NULL,
        members_json TEXT NOT NULL,
        routes_json TEXT NOT NULL,
        policy_signature TEXT NOT NULL,
        opening_lineage TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'open'
            CHECK(state IN ('open', 'round1_red', 'green', 'owner_decision',
                            'accepted_risk', 'awaiting_manual_review', 'repair_open',
                            'invalidated')),
        current_round INTEGER NOT NULL DEFAULT 0 CHECK(current_round BETWEEN 0 AND 2),
        owner_identity TEXT,
        owner_reason TEXT,
        finding_refs_json TEXT,
        policy_result TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS review_cohort_rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cohort_pk INTEGER NOT NULL REFERENCES review_cohorts(id) ON DELETE CASCADE,
        round_number INTEGER NOT NULL CHECK(round_number IN (1, 2)),
        packet_json TEXT NOT NULL,
        author_model TEXT NOT NULL,
        reviewer_model TEXT NOT NULL,
        reviewer_context TEXT NOT NULL CHECK(reviewer_context='different-model'),
        reviewer_invocations INTEGER NOT NULL CHECK(reviewer_invocations=1),
        usage_json TEXT,
        recorded_at TEXT NOT NULL,
        UNIQUE(cohort_pk, round_number)
    )""",
    """CREATE TABLE IF NOT EXISTS review_cohort_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cohort_pk INTEGER NOT NULL REFERENCES review_cohorts(id) ON DELETE CASCADE,
        round_number INTEGER NOT NULL CHECK(round_number IN (1, 2)),
        task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        verdict TEXT NOT NULL CHECK(verdict IN ('green', 'advisory', 'red', 'accepted_risk')),
        critical_findings INTEGER NOT NULL DEFAULT 0,
        high_findings INTEGER NOT NULL DEFAULT 0,
        warnings INTEGER NOT NULL DEFAULT 0,
        reviewed_state_fingerprint TEXT NOT NULL,
        route_json TEXT NOT NULL,
        carried_forward INTEGER NOT NULL DEFAULT 0 CHECK(carried_forward IN (0, 1)),
        supersedes_result_id INTEGER REFERENCES review_cohort_results(id) ON DELETE SET NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(cohort_pk, task_slug, round_number)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_review_cohort_results_task ON review_cohort_results(task_slug, id DESC)",
]
