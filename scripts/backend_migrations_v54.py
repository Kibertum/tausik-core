"""v54 migration SQL -- RENAR AT (Acceptance Test) artifacts
(at-acceptance-tests-derived-by-an-isolated-agent).

Held in its own module to keep backend_migrations.py under the filesize gate.
AT's first migration reuses backend_schema_at.AT_STATEMENTS verbatim -- same
premise ACTZ's v52 started from. See backend_schema_actz's docstring for what
to do the day this entity gets a SECOND migration: freeze this module's own
copy then, do not keep sharing the reference.
"""

from __future__ import annotations

from backend_schema_at import AT_STATEMENTS

MIGRATION_V54: list[str] = AT_STATEMENTS
