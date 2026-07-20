"""Guard: SCHEMA_VERSION and the highest migration must agree.

Split out of backend_migrations.py, which sat at 399 of its 400 permitted
lines — adding migration v39 pushed it over. Worth naming plainly: this file
exists because of a line count, not because the guard wanted its own home. It
is at least a cohesive unit (a check, not a migration), so the split is
defensible on its own terms; the general pattern of splitting for the gate
rather than for cohesion is what l26-filesize-gate-revisit is about, and this
is one more data point for it.
"""

from __future__ import annotations


def check_schema_migration_parity(schema_version: int, migrations: dict[int, list[str]]) -> None:
    """Raise when SCHEMA_VERSION and the highest migration have drifted apart.

    The two live in different files and are bumped by hand, so drift is one
    copy-paste slip away — and it is silent in *both* directions. A
    SCHEMA_VERSION ahead of the migrations leaves every database permanently
    "stale but unmigratable" (``run_migrations`` has nothing to apply, yet the
    recorded version never reaches the code's). One behind means a migration
    that was written never runs at all.

    Checked at import so the mistake surfaces on the next command rather than on
    someone's database. Deliberately not ``assert`` — that vanishes under
    ``python -O``, which is precisely when you least want the guard gone.
    """
    highest = max(migrations)
    if schema_version != highest:
        raise RuntimeError(
            f"schema/migration drift: SCHEMA_VERSION={schema_version} "
            f"(backend_schema.py) but the highest migration is v{highest} "
            f"(backend_migrations.py). Bump both together."
        )
