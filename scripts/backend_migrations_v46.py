"""v46 migration SQL — the edge that makes a plan's ORDER expressible
(task-next-cannot-express-plan-order, wave 1 of release 1.9).

Held in its own module to keep backend_migrations.py under the filesize gate.
``MIGRATION_V46`` is the ordered statement list referenced by
backend_migrations._CURRENT_MIGRATIONS[46]. Purely additive: one new table, no
column touched, no rebuild.

WHY AN EDGE AND NOT A PRIORITY NUMBER. The statements this table has to carry
already exist, in the release plan and in the decision log, and they are all of
one shape: "this one first", "that one only after it". That is an edge. A
priority integer would have to be re-derived for the whole queue every time a
task is inserted between two others, and it would record the ORDER while losing
the REASON -- which is the half a reader needs to tell a deliberate sequence
from an accident of numbering.

WHY A SEPARATE TABLE AND NOT A COLUMN ON `tasks`. Two reasons, and the second is
the load-bearing one. A column holds one predecessor; the plan routinely names
several ("only after the gates are honest AND the copies are found"). And
`tasks` has 43 columns: adding one means a full table rebuild under SQLite's
older-version rules, which is a migration risk out of all proportion to an edge.

WHY `slug` AND NOT `id`. Every sibling child table (`task_logs`,
`reasoning_steps`) references `tasks(slug)`, and the state contract lists `id`
among the fields that do NOT travel to git: it is a local autoincrement with no
meaning in another clone. This edge IS serialised into the projection, so it has
to be keyed by the identity that survives the trip. Referencing `tasks(id)` was
tried first and rejected by `PRAGMA foreign_key_check` in the migration tests --
their minimal stand-in for `tasks` carries `slug`, precisely because that is
what the rest of the schema points at.

WHY `ON DELETE CASCADE` ON BOTH SIDES. An edge whose endpoint is gone is not a
constraint any more, it is a fact about nothing -- and a stale edge would hold
its dependent out of `task next` forever, with no visible cause. Deleting a task
must therefore take its edges with it, in both directions.

The PRIMARY KEY over the pair makes re-declaration idempotent, which is what
lets a plan be replayed: running the same sequence of declarations twice must
converge on the same graph, not accumulate duplicates.
"""

from __future__ import annotations

MIGRATION_V46: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS task_deps (
        task_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        depends_on_slug TEXT NOT NULL REFERENCES tasks(slug) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        PRIMARY KEY (task_slug, depends_on_slug),
        CHECK (task_slug <> depends_on_slug)
    )
    """,
    # Both directions are hot. "What is this task waiting for?" is asked when a
    # task is inspected; "what is waiting on this one?" is asked by every single
    # `task next`, once per candidate, and that is the query that must not
    # degrade as the backlog grows.
    "CREATE INDEX IF NOT EXISTS idx_task_deps_task ON task_deps(task_slug)",
    "CREATE INDEX IF NOT EXISTS idx_task_deps_on ON task_deps(depends_on_slug)",
]
