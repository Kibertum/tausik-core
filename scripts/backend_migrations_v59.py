"""Migration v59: an edge may say it was OBSERVED, not inferred or declared.

The graph's whole discipline is that an edge carries where it came from, and
`EDGE_LAYERS` is a closed list the database enforces. Until now it held three
kinds of provenance:

    git_cochange            inferred from commit history
    declared_crosscutting   a test's CROSSCUTTING_SCOPE
    declared_relevant_files a task's declaration
    declared_scope_paths    a task's scope ACL
    declared_renar          an existing RENAR link

Coverage observed while a test RUNS is none of those. It is not an inference
from history and not somebody's statement — it is a record of what happened, and
it is the strongest evidence the graph can hold about a test and a file. Reusing
one of the existing layers to avoid a migration would have been the one thing
this schema exists to prevent: two different claims summarised into one number.

WHY A MIGRATION IS RIGHT HERE, having been refused twice this release. Decision
#349's verdict was that the SHAPE of the schema held across three stacks, and
two later tasks were told not to migrate because their subject was reachable
without one — a suffix table, a coverage check. This subject is not: a new
provenance is exactly what the `layer` column enumerates, and there is no honest
way to record it without saying so.

THE LITERAL BELOW IS FROZEN, and that is not a style choice (convention #646). A
migration that read the live schema would change meaning whenever the live
schema changed, so a database migrated in June and one migrated today would end
up different while both reported v59. What is written here is what v59 means,
forever.
"""

from __future__ import annotations

#: SQLite cannot ALTER a CHECK constraint, so the table is rebuilt. The literal
#: is v58's `artifact_edges` with `observed_coverage` added to the layer list and
#: NOTHING else changed — the relations, the confidence column, the observation
#: count, the source reference, and the UNIQUE that lets one pair carry both an
#: inferred and a declared edge all stay exactly as they were.
MIGRATION_V59: list[str] = [
    """CREATE TABLE IF NOT EXISTS artifact_edges_v59 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        target_artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
        relation TEXT NOT NULL CHECK(relation IN (
            'co_changes', 'covers', 'documents', 'references', 'defines', 'implements'
        )),
        layer TEXT NOT NULL CHECK(layer IN (
            'git_cochange', 'declared_crosscutting', 'declared_relevant_files',
            'declared_scope_paths', 'declared_renar', 'observed_coverage'
        )),
        confidence REAL NOT NULL,
        observations INTEGER NOT NULL DEFAULT 1,
        source_ref TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(source_artifact_id, target_artifact_id, relation, layer)
    )""",
    # Copy by NAME, never `SELECT *`: a column added between v56 and here would
    # otherwise land in the wrong position and be silently mis-typed.
    """INSERT INTO artifact_edges_v59
        (id, source_artifact_id, target_artifact_id, relation, layer,
         confidence, observations, source_ref, created_at)
       SELECT id, source_artifact_id, target_artifact_id, relation, layer,
              confidence, observations, source_ref, created_at
       FROM artifact_edges""",
    "DROP TABLE artifact_edges",
    "ALTER TABLE artifact_edges_v59 RENAME TO artifact_edges",
    # The three indexes are recreated because DROP TABLE took them with it.
    # Leaving them out would keep every query correct and make the neighbour
    # lookup a table scan — a regression nothing would fail on.
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_source ON artifact_edges(source_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_target ON artifact_edges(target_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_artifact_edges_layer ON artifact_edges(layer)",
]
