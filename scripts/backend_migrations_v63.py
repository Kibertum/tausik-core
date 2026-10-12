"""Migration v63: a session knows which host session it is.

Decision #376 (1.10, story E): the TAUSIK session stops being a ritual the agent
performs with `/start` and `/end` and becomes the host session itself —
SessionStart opens it, SessionEnd closes it. For that the row has to carry the
host's own identifier (`session_id` in the Claude Code hook payload), so that
opening is idempotent per host session and closing ends exactly the session
the host is ending, not whichever one happens to be the newest open.

Measured before the change: session #265 stayed open nine days at 76 active
minutes because nobody ran `/end`, and one Claude Code transcript spanned
several TAUSIK sessions (72.4% duplicate token rows in the #227 measurement).

WHY THE INDEX IS NOT IN THIS LIST ALONE. `host_session_id` is also in the
`sessions` CREATE TABLE for fresh installs, and the index lives in
`POST_MIGRATION_INDEXES_SQL`, which runs AFTER migrations — an index in the
cumulative `INDEXES_SQL` would run before this ALTER on an upgraded database
and fail on a missing column, the same ordering trap that broke the 1.8 → 1.9
upgrade at v53 (memory #716). The `sessions` table exists on every database
old enough to be migrated, so the ALTER below never meets a column that the
cumulative script already created.

NULL for every existing row: a session opened by the CLI without a host id is
still a valid session, and every consumer keeps working with it.

THE LITERAL BELOW IS FROZEN (convention #646).
"""

from __future__ import annotations

MIGRATION_V63: list[str] = [
    "ALTER TABLE sessions ADD COLUMN host_session_id TEXT",
    "CREATE INDEX IF NOT EXISTS idx_sessions_host ON sessions(host_session_id)",
]
