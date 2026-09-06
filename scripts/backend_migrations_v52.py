"""v52 migration SQL -- RENAR ACTZ artifacts (actz-the-contract-contour-artifact-is-missing).

Held in its own module to keep backend_migrations.py under the filesize gate,
matching v35/v36/v37's split. Purely additive -- new tables only, no ALTER on
any existing table.

Unlike v36 (ADAPT's original 3-status shape, later widened by v50), ACTZ has no
prior schema to be a delta against: v52 is its ONLY migration, so it reuses
``backend_schema_actz.ACTZ_STATEMENTS`` verbatim rather than retyping the same
DDL as a second literal -- see that module's docstring for why.
"""

from __future__ import annotations

from backend_schema_actz import ACTZ_STATEMENTS

MIGRATION_V52: list[str] = ACTZ_STATEMENTS
