"""Baseline DDL for RENAR ACTZ artifacts (actz-the-contract-contour-artifact-is-missing).

RENAR Sec5A (ADR-011, accepted): ACTZ is the contractual clarification protocol
-- "Протокол уточнения ТЗ N N" -- with a two-signature lifecycle draft -> sent
-> signed -> superseded (Sec5.5.3). Unlike ADAPT (Sec7, an internal document the
client never sees), ACTZ IS the client-facing artifact: what the client
approves belongs here, not in ADAPT (ADR-011's own withdrawal rationale for
ADAPT's client-signature role names ACTZ as its correct home).

ONE LIST OF STATEMENTS, not two hand-synced literals. ADAPT's v36/v50 pair
predates a real schema; here ACTZ has no history yet -- v52 is its only
migration -- so the fresh-DB path (``ACTZ_SQL``, an executescript string) and
the migration path (``backend_migrations_v52.MIGRATION_V52``) both derive from
``ACTZ_STATEMENTS`` in this module rather than being retyped in each. A design
choice, not an oversight: the two-literal shape is exactly the mechanism named
by the open defect ``schema-index-drift-fresh-vs-migrated``, and there is no
reason to add a new instance of it for a brand-new table.

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
