"""Migration v74: memory layers, hit counters and the tail-by-relevance opt-in.

memory-tail-by-relevance-not-recency. The CLAUDE.md tail selects the latest
N records per type, so a two-month-old record cited twenty times loses its
line to yesterday's unopened one. Relevance cannot be computed without
per-record access counts, and none existed anywhere (brain_events carries a
query and a result_count, never a memory id) — which is why this task spent
a release deferred.

What lands now:
- hit_count/last_hit_at: bumped by every explicit `memory show <id>` — the
  one access that is unambiguous. Search results are exposure, not access,
  and are deliberately NOT counted.
- layer: core/hot/warm/cold/frozen, assigned by accumulation (hits, age),
  never by schedule. Existing rows start NULL; `memory hygiene` fills them.
- pinned: the AC5 guarantee — a pinned record is never auto-demoted and
  always sorts first in the tail.
- memory_hygiene_snapshots: prev-layer rows per apply, so `--revert` undoes
  the last apply in one command. Nothing is ever deleted: a demoted record
  stays reachable by direct request; that is the whole difference between a
  layer and the archive.

The tail keeps ordering by recency until config.json sets
memory_tail_by_relevance=true (AC7: opt-in, default off — the flag earns
its default on this corpus before it becomes one).
"""

MIGRATION_V74: list[str] = [
    "ALTER TABLE memory ADD COLUMN hit_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE memory ADD COLUMN last_hit_at TEXT",
    "ALTER TABLE memory ADD COLUMN layer TEXT",
    "ALTER TABLE memory ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0",
    """CREATE TABLE IF NOT EXISTS memory_hygiene_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        memory_id INTEGER NOT NULL REFERENCES memory(id) ON DELETE CASCADE,
        prev_layer TEXT,
        applied_at TEXT NOT NULL
    )""",
]
