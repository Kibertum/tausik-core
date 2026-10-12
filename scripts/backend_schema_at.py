"""Baseline DDL for RENAR AT (Acceptance Test) artifacts (at-acceptance-tests-derived-by-an-isolated-agent).

RENAR Sec8A (ADR-012, accepted): traceability closes TC -> SR -> ADAPT -> ТЗ,
which cannot catch a class of defect that lives ABOVE it -- a wrong
interpretation makes every TC pass because the system perfectly matches the
wrong reading, and fails acceptance at the client. AT closes exactly that gap
and only that gap.

Three properties the standard makes mandatory:

1. Derived by an ISOLATED agent from the final TZ (final_tz_snapshot) alone --
   no ADAPT, BR, SR, SPEC, TC or code in its input. Isolation here is a
   GENERATION mechanism, not a policy: an agent that has seen the
   interpretation reproduces its mistake. TAUSIK is stdlib-only (no LLM calls
   from scripts/), so this table does not enforce isolation itself -- the
   procedure lives in docs/en/at-generation-procedure.md, and this table
   records the RESULT plus enough provenance (``generated_by``,
   ``source_as_of``) to audit that the procedure was followed.
2. Regenerated before every trial from the CURRENT edition -- ``source_as_of``
   pins which moment of final_tz_snapshot an AT was derived from;
   ``at_freshness`` (gate_at_freshness.py, warn) compares it against the LIVE
   snapshot for the same tz_ref and names what changed.
3. ``tz_text`` is mandatory: a verbatim quote of the contract clause, not a
   paraphrase -- the one field that makes an AT traceable back to what the
   client actually signed, independent of whatever ``scenario`` prose says
   about it.

CURRENT CUMULATIVE SHAPE, not a migration delta -- ``at_results`` below is v55
(at-red-with-tc-green-routes-to-interpretation-not-code); backend_migrations_v54
holds its own frozen copy of what v54 shipped WITHOUT it. See
backend_schema_actz's docstring for the full reasoning (same relationship,
one entity earlier).

``at_results`` is APPEND-ONLY history, the same shape as ``verification_runs``/
``gate_runs``: an AT can be exercised more than once over time, and each trial
is a fact, not a value to overwrite. ``route_at_tc`` (service_at.py) reads the
LATEST row per AT, never mutates one.
"""

from __future__ import annotations

AT_STATEMENTS: list[str] = [
    """CREATE TABLE IF NOT EXISTS ats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        tz_ref TEXT NOT NULL,
        -- Verbatim quote of the governing ACTZ/ТЗ text at generation time
        -- (Sec8A property 3) -- not a paraphrase, and not derived from
        -- scenario, which is the agent's OWN acceptance-check prose.
        tz_text TEXT NOT NULL,
        scenario TEXT NOT NULL,
        -- Which moment of final_tz_snapshot this AT was derived from --
        -- the freshness gate's comparison key (Sec8A property 2).
        source_as_of TEXT NOT NULL,
        -- Free text: which isolated agent/session produced this AT. Filled
        -- by the ORCHESTRATING agent transcribing the isolated agent's
        -- output (SKILL.md) -- never the isolated agent itself, which has
        -- no access to this table by design.
        generated_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ats_tz_ref ON ats(tz_ref)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS fts_ats USING fts5(
        slug, tz_ref, tz_text, scenario,
        content='ats', content_rowid='id'
    )""",
    """CREATE TRIGGER IF NOT EXISTS ats_ai AFTER INSERT ON ats BEGIN
        INSERT INTO fts_ats(rowid, slug, tz_ref, tz_text, scenario)
        VALUES (new.id, new.slug, new.tz_ref, new.tz_text, new.scenario);
    END""",
    """CREATE TRIGGER IF NOT EXISTS ats_ad AFTER DELETE ON ats BEGIN
        INSERT INTO fts_ats(fts_ats, rowid, slug, tz_ref, tz_text, scenario)
        VALUES ('delete', old.id, old.slug, old.tz_ref, old.tz_text, old.scenario);
    END""",
    """CREATE TRIGGER IF NOT EXISTS ats_au AFTER UPDATE ON ats BEGIN
        INSERT INTO fts_ats(fts_ats, rowid, slug, tz_ref, tz_text, scenario)
        VALUES ('delete', old.id, old.slug, old.tz_ref, old.tz_text, old.scenario);
        INSERT INTO fts_ats(rowid, slug, tz_ref, tz_text, scenario)
        VALUES (new.id, new.slug, new.tz_ref, new.tz_text, new.scenario);
    END""",
    """CREATE TABLE IF NOT EXISTS at_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        at_slug TEXT NOT NULL REFERENCES ats(slug) ON DELETE CASCADE,
        outcome TEXT NOT NULL CHECK(outcome IN ('red', 'green')),
        note TEXT,
        recorded_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_at_results_slug ON at_results(at_slug, recorded_at)",
]

# Fresh-DB path (backend_init.py). This is AT's first migration -- no history
# to diverge from yet (the same premise ACTZ's v52 started from; see that
# module's docstring for what happens the day it stops being true).
AT_SQL = ";\n".join(AT_STATEMENTS) + ";\n"
