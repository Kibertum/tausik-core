"""Baseline DDL for RENAR ACTZ artifacts (actz-the-contract-contour-artifact-is-missing).

RENAR Sec5A (ADR-011, accepted): ACTZ is the contractual clarification protocol
-- "Протокол уточнения ТЗ N N" -- with a two-signature lifecycle draft -> sent
-> signed -> superseded (Sec5.5.3). Unlike ADAPT (Sec7, an internal document the
client never sees), ACTZ IS the client-facing artifact: what the client
approves belongs here, not in ADAPT (ADR-011's own withdrawal rationale for
ADAPT's client-signature role names ACTZ as its correct home).

CURRENT CUMULATIVE SHAPE, not a migration delta -- exactly the relationship
``backend_schema_adapts.ADAPTS_SQL`` has to ``backend_migrations_v36``: this
module is what a FRESH database gets today, migrations are what an EXISTING
one replays to arrive at the same place. ``actz_points.tz_ref`` below is v53
(final-tz-is-the-acceptance-reference-and-we-have-none); ``backend_migrations_v52``
holds its own frozen copy of what v52 shipped WITHOUT that column, and
``backend_migrations_v53.MIGRATION_V53`` ALTERs it in on the upgrade path.

The two are kept independently correct on purpose, checked by
``test_migration_v52_creates_tables_clean`` + ``test_migration_v53_adds_tz_ref``
running migrations in sequence and comparing the result to THIS module's shape
-- the byte-equivalence discipline ADAPT's v36/v50 docstring names, applied
from ACTZ's second migration onward rather than its first (v52 alone had no
history to diverge from yet, which is exactly what stopped being true here).

``actz_points`` gives ACTZ item-level granularity: RENAR ties `decided-in`
(ADAPT backward-finding -> ACTZ) to a POINT of the protocol, not the document as
a whole (cardinality 1..N ADAPT findings per ACTZ point). ``actz_decided_in``
carries provenance (``linked_by``, ``created_at``) that ``adapt_links`` does not
-- a genuinely new requirement, not a copy of that table's shape.

Signatures (Sec5.5.3, two independent persons): there is exactly ONE project
ed25519 key (crypto_keys.py), not one per role. ``role='architect'`` signs for
real with it, exactly like adapt_signatures. ``role='client'`` records
``signed_by``+``signed_at`` only (``key_fingerprint``/``signature`` stay NULL)
-- an honest audit trail of a recorded approval, not a simulated independent
cryptographic signature the project has no key to produce. See
actz-the-contract-contour-artifact-is-missing's reasoning trace for why this is
not the same fiction ADR-011 withdrew from ADAPT: that withdrawal was about
AUDIENCE (the client never saw ADAPT), not about name+timestamp being invalid
evidence of approval.
"""

from __future__ import annotations

ACTZ_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS actz (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        tz_ref TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN
            ('draft', 'sent', 'signed', 'superseded')),
        -- parent_actz: self-ref for a future delta chain, symmetric to
        -- adapts.parent_adapt. ON DELETE SET NULL so deleting one ACTZ never
        -- cascade-wipes a whole lineage.
        parent_actz TEXT REFERENCES actz(slug) ON DELETE SET NULL,
        delta_n INTEGER NOT NULL DEFAULT 0,
        supersession_rationale TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS actz_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actz_slug TEXT NOT NULL REFERENCES actz(slug) ON DELETE CASCADE,
        point_no INTEGER NOT NULL,
        -- tz_ref (v53): which clause of the original ТЗ (or a prior ACTZ
        -- point) this point clarifies/overrides -- final_tz_snapshot groups
        -- by this column. NOT NULL DEFAULT '' at the DB level (no deployed
        -- rows existed when this was added); an empty string is refused at
        -- the service layer, same shape as adapt_interpretations.tz_ref.
        tz_ref TEXT NOT NULL DEFAULT '',
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(actz_slug, point_no)
    )""",
    """CREATE TABLE IF NOT EXISTS actz_signatures (
        actz_slug TEXT NOT NULL REFERENCES actz(slug) ON DELETE CASCADE,
        -- Both roles are REQUIRED today (Sec5.5.3, decision #255 defers the
        -- unilateral ADR-017 path). 'client' carries no signature/fingerprint
        -- -- see module docstring.
        role TEXT NOT NULL CHECK(role IN ('architect', 'client')),
        signed_by TEXT NOT NULL,
        signed_at TEXT NOT NULL,
        key_fingerprint TEXT,
        signature TEXT,
        PRIMARY KEY (actz_slug, role)
    )""",
    """CREATE TABLE IF NOT EXISTS actz_links (
        actz_slug TEXT NOT NULL REFERENCES actz(slug) ON DELETE CASCADE,
        -- Polymorphic target (task|spec), no hard FK on target_slug -- same
        -- design as adapt_links, same reason (SQLite cannot FK a
        -- type-discriminated column); existence is checked in service_actz.
        target_type TEXT NOT NULL CHECK(target_type IN ('task', 'spec')),
        target_slug TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (actz_slug, target_type, target_slug)
    )""",
    """CREATE TABLE IF NOT EXISTS actz_decided_in (
        -- An ADAPT backward finding decided-in a POINT of a signed ACTZ, WITH
        -- provenance. Composite FK to actz_points(actz_slug, point_no) relies
        -- on that table's UNIQUE(actz_slug, point_no).
        adapt_slug TEXT NOT NULL REFERENCES adapts(slug) ON DELETE CASCADE,
        finding_id INTEGER NOT NULL REFERENCES adapt_findings(id) ON DELETE CASCADE,
        actz_slug TEXT NOT NULL,
        actz_point_no INTEGER NOT NULL,
        linked_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (adapt_slug, finding_id, actz_slug, actz_point_no),
        FOREIGN KEY (actz_slug, actz_point_no)
            REFERENCES actz_points(actz_slug, point_no) ON DELETE CASCADE
    )""",
    "CREATE INDEX IF NOT EXISTS idx_actz_parent ON actz(parent_actz)",
    "CREATE INDEX IF NOT EXISTS idx_actz_points_actz ON actz_points(actz_slug)",
    # idx_actz_points_tz_ref is NOT here: this whole list re-runs unconditionally
    # on EVERY init_schema call (including against a pre-v53 database that
    # already has actz_points WITHOUT tz_ref -- CREATE TABLE IF NOT EXISTS
    # no-ops safely on that old table, but an index statement referencing the
    # new column would not). It is created by a guarded postseed step instead
    # (backend_migrations_v53.ensure_actz_points_tz_ref_index), which runs
    # AFTER the column is guaranteed to exist on both paths. See that module.
    "CREATE INDEX IF NOT EXISTS idx_actz_links_target ON actz_links(target_type, target_slug)",
    "CREATE INDEX IF NOT EXISTS idx_actz_decided_in_adapt ON actz_decided_in(adapt_slug, finding_id)",
    "CREATE INDEX IF NOT EXISTS idx_actz_decided_in_actz ON actz_decided_in(actz_slug, actz_point_no)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_actz USING fts5(
        slug, title, tz_ref,
        content='actz', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS actz_ai AFTER INSERT ON actz BEGIN
        INSERT INTO fts_actz(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS actz_ad AFTER DELETE ON actz BEGIN
        INSERT INTO fts_actz(fts_actz, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
    END""",
    """CREATE TRIGGER IF NOT EXISTS actz_au AFTER UPDATE ON actz BEGIN
        INSERT INTO fts_actz(fts_actz, rowid, slug, title, tz_ref)
        VALUES ('delete', old.id, old.slug, old.title, old.tz_ref);
        INSERT INTO fts_actz(rowid, slug, title, tz_ref)
        VALUES (new.id, new.slug, new.title, new.tz_ref);
    END""",
]

# Fresh-DB path (backend_init.py): one executescript string, joined from the
# same statements the v52 migration applies individually.
ACTZ_SQL = ";\n".join(ACTZ_STATEMENTS) + ";\n"
