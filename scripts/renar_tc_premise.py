"""Does TC exist here as an artifact class? One measurer, two consumers.

Two separate declarations in this repository rest on the SAME premise — that
TAUSIK holds no first-class TC (test case) artifacts:

  * `tc-pos-neg-pairing` in the conformance manifest (§13.3.5). The clause is
    conditional: pos/neg pairing is required for every normative assertion
    *covered by at least one TC*. With no TC there is nothing to violate, so the
    confirmation is an honest vacuous truth — and it is PUBLISHED, into an
    artifact we asked an external tracker to read.
  * ADR-013's `TC.environment-ref` duty on SPEC-TEST (§9 p.119), declared
    inapplicable by task
    adr-013-conditional-obligations-expire-when-subject-appears.

Before this module the two were unrelated: the manifest wrote `True` as a
literal with its premise in a comment, and the guard test looked for a table
named `test_cases` or prefixed `tc_`. Neither measured the premise. A mutation
proved it: a table `spec_tests` carrying `assertion_ref`, `polarity` and
`environment_ref`, with a row in it, left BOTH green. The declaration said
"TC does not exist"; the code asked "is there a table with one of two names".

So the premise is measured ONCE, here, and both consumers read this module.
Adding a third consumer means importing this, not writing a third cut.

WHY THE CUT IS THE SET OF CLASSES AND NOT A COLUMN NAME
-------------------------------------------------------
The obvious cut — look for an `environment_ref` column — is worse than useless,
and this is not a matter of taste. `environment-ref` is the field the duty
DEMANDS. A TC class that carries it is the COMPLIANT case; a TC class without it
is the VIOLATION the duty exists to catch. A detector keyed on that column
reddens on the compliant TC and stays silent on the non-compliant one, so its
green branch would be green for a reason unrelated to the protection being
checked (convention #491).

Any cut by name — of a table or of a column — is a guess about a class that does
not exist yet, and a guess we would be making on behalf of whoever creates it.
The one bounded question is: *has the set of artifact classes changed at all
since the declaration was made?* That question cannot be dodged by naming, and
it is the question this module asks.

WHY THE SET IS NOT DERIVED FROM backend_schema.SCHEMA_SQL
---------------------------------------------------------
It was the first design, and a measurement killed it. Convention #214 says
schema-object lists are derived, never hardcoded, and `test_ddl_fixture_parity`
derives its table list from `SCHEMA_SQL` exactly so. But `SCHEMA_SQL` does not
declare every class the live database holds: `specs` and the whole `adapts`
family, among others, are created by MIGRATIONS rather than by the canonical
DDL. A detector built on that source would report `specs` itself as an unknown
new class and be red from its first run. `SCHEMA_SQL` is the canonical DDL for
the tables it declares; it is not an inventory of artifact classes.

The live database is therefore the only honest source, and the baseline below is
what makes it a ratchet rather than a tautology.
"""

from __future__ import annotations

import sqlite3

# The artifact classes this project held on the day ADR-013's conditional
# obligations were declared inapplicable, and the day the manifest's
# `tc-pos-neg-pairing` vacuous truth was last re-earned.
#
# A SET, AND NOT A COUNT. A pinned count was the first attempt: it is smaller,
# and it dodges the objection that pinning names is a schema copy (convention
# #214). But a count cannot name the newcomer, and it treats a database holding
# FEWER classes as a change — while the question the declaration rests on is
# narrower: did a class APPEAR that was absent when we declared TC absent? Set
# difference asks exactly that. A class going away is not a TC arriving, so
# removals are not findings either.
#
# Widening the witness is NOT what made the suite green — see `classes_appeared`
# for what did, and for why this comparison is not part of the published clause.
#
# THIS IS A WITNESS, NOT A SETTING. A name may only join it together with an
# answer to the question the failure message asks: is the new class a TC?
# Appending a name to quiet a red, without answering, turns this machine into
# the appearance of one — the very defect the release it belongs to is about.
CLASSES_AT_DECLARATION = frozenset(
    {
        # actz-the-contract-contour-artifact-is-missing (RENAR §5A): the ACTZ
        # contractual clarification protocol and its child tables. NOT a TC
        # (test case) artifact class — ACTZ is a contract-contour artifact
        # (points/signatures/links/decided-in edges), unrelated to §13.3.5
        # pos/neg pairing or ADR-013's TC.environment-ref duty.
        "actz",
        "actz_decided_in",
        "actz_links",
        "actz_points",
        "actz_signatures",
        "adapt_findings",
        "adapt_interpretations",
        "adapt_links",
        "adapt_signatures",
        "adapts",
        # at-acceptance-tests-derived-by-an-isolated-agent (RENAR §8A): the AT
        # (Acceptance Test) header record. NOT a TC (test case) artifact class
        # — it records the RESULT of an isolated-generation procedure, not a
        # test case executable, and carries no assertion/polarity/environment
        # fields §13.3.5 pos/neg pairing or ADR-013's TC.environment-ref duty
        # are about.
        "ats",
        # p9-a-test-never-observed-red-is-not-evidence (RENAR §9.18.2): which
        # test NODES have ever been observed FAILING. NOT a TC (test case)
        # artifact class — it holds no assertion, no polarity and no environment
        # reference, only an observation that a node identified elsewhere was
        # once red. §13.3.5 pos/neg pairing and ADR-013's TC.environment-ref
        # duty stay dormant. Caught by this very guard when the table appeared,
        # which is what it is for.
        "test_red_history",
    # Artifact graph (v56). Code, docs and the edges between them: a map of what
    # the repository CONTAINS and how its parts move together, with the layer
    # each edge was obtained by. Not TC artifacts -- none of them records a
    # verification of a normative statement; an edge says "these co-changed" or
    # "this was declared", never "this requirement was checked".
    "artifacts",
    "artifact_symbols",
    "artifact_edges",
        # at-red-with-tc-green-routes-to-interpretation-not-code: append-only
        # history of OBSERVED AT trial outcomes (red/green). Still not a TC
        # artifact class — it records what happened when someone/something
        # exercised an AT scenario, not an executable test case; TC itself
        # (the entity route_at_tc's tc_outcome describes) still has no table.
        "at_results",
        "brain_events",
        "decisions",
        "epics",
        "events",
        "events_anchor",
        "explorations",
        "gate_runs",
        "memory",
        "memory_edges",
        "meta",
        "reasoning_steps",
        "redactions",
        "reviews",
        "roles",
        "session_usage_metrics",
        "sessions",
        "snippets",
        "specs",
        "stories",
        "task_deps",
        "task_logs",
        "task_specs",
        "tasks",
        "usage_events",
        "verification_runs",
    }
)

DECLARATION = (
    "TAUSIK holds no first-class TC artifacts, so §13.3.5 pos/neg pairing and "
    "ADR-013's TC.environment-ref duty are both vacuous. Re-earned whenever "
    "CLASSES_AT_DECLARATION gains a name with an explicit answer about that class."
)


def _shadow_tables(conn: sqlite3.Connection) -> set[str]:
    """Virtual tables and the shadow tables SQLite creates behind them.

    Derived, not matched by prefix. `fts_%` would be a hole: a TC table named
    `fts_test_cases` is not a shadow of anything and must count as a class. A
    shadow is identified by the virtual table it belongs to, which sqlite_master
    records as its own CREATE VIRTUAL TABLE row.
    """
    virtual = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE 'CREATE VIRTUAL TABLE%'"
        )
    }
    suffixes = ("_config", "_data", "_docsize", "_idx", "_content")
    shadows = set(virtual)
    for name in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        for owner in virtual:
            if name.startswith(owner) and name[len(owner) :] in suffixes:
                shadows.add(name)
    return shadows


def artifact_classes(conn: sqlite3.Connection) -> list[str]:
    """Every table that is an artifact class of this project, sorted.

    Excludes SQLite's own bookkeeping and the shadow tables of FTS indexes:
    neither is a class anyone can hold an obligation against.
    """
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    internal = {"sqlite_sequence", "sqlite_stat1", "sqlite_stat4"}
    return sorted(tables - _shadow_tables(conn) - internal)


def classes_appeared(conn: sqlite3.Connection) -> list[str]:
    """Classes absent when TC was declared absent, and present now.

    THIS IS A STATEMENT ABOUT OUR DECLARATION, NOT ABOUT A DATABASE, and that
    distinction was bought by eight red tests. `eval_mandatory_clauses` runs on
    whatever database it is handed, and fixtures build their own — one of them
    creates tables by DDL precisely because the production schema cannot hold
    what the fixture needs (`_satisfy_clause_13_3_3`). Against such a database
    this function reports an arrival, correctly and uselessly: the database is
    simply not the one the declaration was made about.

    So it is NOT part of `tc_evidence`, and the published clause does not rest on
    it. Its consumer is the repository's own guard test, which runs it against
    the live project database — the only database our declaration describes.
    """
    return sorted(set(artifact_classes(conn)) - CLASSES_AT_DECLARATION)


def tc_evidence(conn: sqlite3.Connection) -> list[str]:
    """Evidence, true of ANY database, that ADR-013's duties are no longer vacuous.

    Deliberately narrower than `classes_appeared`: everything here is a fact
    about the database in hand, so the manifest clause may rest on it whatever
    database it is generated from.

      * a SPEC-DOC artifact exists — the second conditional duty ADR-013 brought,
        whose executor (a doc lint bound to the type, blocking) does not exist:
        scripts/docs_lint.py returns 0 unconditionally and is bound to nothing.

    The SPEC-TEST type is deliberately NOT a finding on its own. §9 puts
    `environment-ref` on the TC, required when the SPEC-TEST's automation.kind is
    dynamic — a SPEC-TEST with no TC beneath it has nothing to carry the field,
    so the duty stays vacuous. The subject is the TC, and reddening on SPEC-TEST
    would be reddening on something that cannot yet violate anything.
    """
    findings: list[str] = []

    try:
        spec_docs = conn.execute("SELECT COUNT(*) FROM specs WHERE type='DOC'").fetchone()[0]
    except sqlite3.Error:
        spec_docs = 0
    if spec_docs:
        findings.append(
            f"{spec_docs} SPEC-DOC artifact(s) exist — ADR-013's doc-lint duty is live, "
            "and scripts/docs_lint.py is warning-only (returns 0 always) and not bound "
            "to the type."
        )

    return findings


def pairing_clause(conn: sqlite3.Connection) -> dict[str, object]:
    """§13.3.5 `tc-pos-neg-pairing`, derived from the premise instead of written.

    The neighbours in that manifest dict are already derived — `spec-types-closed-list`
    from `len(SPEC_TYPES)`, `closed-lists-backward-findings` from
    `len(FINDING_CATEGORIES)`, `adapt-per-tz` from a computed bundle. This one was
    the literal `True` among them, with its premise in a comment no measurer read.

    IT TAKES NO ARGUMENT, AND THAT IS THE POINT — read the whole paragraph before
    "simplifying" it back. The first version of this function derived the verdict
    from `tc_evidence`, and the quality sweep of session #202 measured what that
    actually did:

      * FALSE RED. `tc_evidence`'s only finding is a SPEC-DOC artifact, which
        belongs to ADR-013's doc-lint duty, NOT to §13.3.5. Adding a SPEC-DOC —
        an ordinary action that migration v49 had just legalised — flipped this
        mandatory clause to `false` and drove `infer_level` to pre-adoption. The
        manifest would have told an external tracker we violate a clause about TC
        pairing because a documentation artifact exists.
      * FALSE GREEN. Measured on a copy of the live database: a `spec_tests` table
        with `assertion_ref`, `polarity`, `environment_ref` and a row in it left
        this clause `true`. The clause could not red on its OWN premise, and the
        very mutation the module was written to defeat survived in the PUBLISHED
        path.

    So the clause is what it honestly is: vacuous while no TC exists, and unable
    to see the arrival itself. `classes_appeared` cannot fill the gap — it compares
    against OUR declaration and is meaningless on a database the declaration was
    not made about, which includes every fixture. That is not a hole being hidden:
    it is disclosed in `MEASURER_CAVEATS`, naming an open task, which is the
    mechanism this project built for a confirmation its measurer has not earned.

    The arrival IS watched, on the live database, by the repository's ADR-013 guard
    test — but NOT everywhere the manifest may be generated. `.tausik/` is
    gitignored and no CI workflow creates the database, so that guard skips in CI
    (task db-gated-ratchets-never-run-in-ci). The evidence string says where the
    watch really runs; the earlier wording claimed the suite gating every commit,
    and that was measurably false.
    """
    return {
        "confirmed": True,
        "evidence": (
            "no first-class TC artifacts → pairing obligation vacuous (§13.3.5); "
            "this clause cannot observe the arrival itself — its basis is published "
            "as `vacuous` in mandatory-clauses-basis, and the ADR-013 guard test "
            "watches the arrival on the live project database"
        ),
    }
