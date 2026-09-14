"""Mandatory clause §13.3.3 (reactive ADAPT) — a measurer that can go red.

`renar_conformance` used to confirm this clause with ``adapts > 0``. A count of
rows goes red on none of the violations the clause exists to catch, which is the
degeneracy ADR-021 names: a control that has forgotten how to fail passes its
whole happy path. This module replaces the count with NAMED sub-checks, each
carrying its own outcome and its own evidence, so a red says *which* half of the
clause is broken rather than "the number is zero".

What §13.3.3 actually requires (corpus verified, `standard/13-conformance.md`):

* p.73 — every ТЗ must pass adversarial review (§7.10.2); the outcome must be
  ISSUED as an AR — an adversarial-review record in status ``issued``.
* p.77 — on verdict "findings present" (≥1 backward finding of the seven
  categories closed at §7.4.4) the ADAPT is mandatory in status ``approved``
  with an Architect signature (§7.5).
* p.80 — creating BR / SR / SPEC from a ТЗ with no recorded verdict violates
  the standard; p.90 states the negative scenario literally — BR/SR/SPEC
  produced with neither ``source.tz-section`` nor ``source.adapt``.

Vacuity is NOT available here, and that distinction is the reason this module
exists rather than a one-line vacuous-true beside `tc-pos-neg-pairing`. The
first half of the clause is indeed vacuous for us — our one ADAPT's ``tz_ref``
points at ``decisions#109``, a record, and ТЗ does not exist here as a class.
The second half is not: SPEC exists as a class and three of them are live, so
the provenance obligation has a subject and that subject violates it. A clause
with a live subject may not be declared vacuously true.

Read-only. Every function here queries; none writes. Introspection over
``sqlite_master``/``PRAGMA table_info`` is deliberate: for two of the four
sub-checks the violation is that the substrate has nowhere to PUT the required
state, and a query against a missing column would raise where it must report.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from renar_tc_premise import artifact_classes
from service_adapts import FINDING_CATEGORIES

# §7.4.4 closed list, v1.0. A finding in any of these categories puts the
# owning ADAPT on the "findings present" branch of the §13.3.3 table (p.77).
#
# AN ALIAS, NOT A COPY. The clause's own text calls them "backward findings",
# so the name earns its place here; the VALUES do not — this module declared
# them again a week after the service layer did, and a second literal is a
# second thing to amend when §7.4.4 next moves. The name is bound to the one
# list, so the two cannot disagree.
BACKWARD_FINDING_CATEGORIES = FINDING_CATEGORIES

# Provenance fields §13.3.3 p.77/p.78 admits on a derived BR/SR/SPEC. Either
# branch is satisfiable; carrying none of them is the p.90 negative scenario.
SPEC_PROVENANCE_FIELDS = ("source_adapt", "source_tz_section", "source_adversarial_review_ref")

# The record shape §7.4.6 makes mandatory on an AR (reference/02-schemas.md
# §7.1: tz-ref, verdict, produces-adapt, status), in the substrate's spelling
# of the standard's field names — `tz-ref` is already stored as `tz_ref` on
# `adapts`, and `source.adapt` as `source_adapt`. A class is an AR class when
# it carries all four: a cut by SHAPE, not by a guessed table name. FOUR, not
# three: with (tz_ref, verdict, status) the whole distance between an ADAPT
# and an adversarial review was one column — `adapts` already carries two of
# the three, and a migration giving it a verdict would have published "AR
# issued in adapts" (review #208, record #20). `produces_adapt` is the field
# an ADAPT can never carry innocently: §7.4.1 makes the AR the sole carrier of
# the verdict and the ADAPT the thing an AR PRODUCES. The schema's other
# mandatory members — `reviewer`, `primary`, `signature` — are nested records
# (vendor/model, author/timestamp), not scalar columns: a substrate may hold
# them as a child table or a JSON column, so they are NOT in the cut; the four
# here are the scalars every spelling must carry. The first version probed
# three names and would have kept publishing "AR does not exist" over an AR
# created under a fourth — the defect #202 found on TC, facing the other way:
# there a guessed name could publish a false `true`, here a false `false`,
# which under decision #295 is an unreported strengthening. The enumeration is
# `renar_tc_premise.artifact_classes`, so FTS shadow tables are excluded by
# derivation, not by prefix.
#
# Shape is NOT the column-name guess `renar_tc_premise` warns against. There
# the column was the DUTY — a compliant class carries it, a violating one does
# not, so keying on it reddens the compliant case. Here the columns are the
# IDENTITY of the class: an AR without a verdict is not a non-compliant AR, it
# is not an AR. Classes carrying part of the shape are still NAMED in the
# evidence with what they lack, so an AR spelled differently is visible to the
# reader even though it is not counted.
AR_SHAPE_FIELDS = ("tz_ref", "verdict", "produces_adapt", "status")


@dataclass(frozen=True)
class Subcheck:
    """One named half-obligation of §13.3.3 with its own verdict."""

    name: str
    ok: bool
    citation: str
    evidence: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.name,
            "ok": self.ok,
            "citation": self.citation,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class ReactiveAdaptState:
    """The substrate facts §13.3.3 is evaluated against.

    Split from :func:`evaluate` on purpose. The evaluator is then a pure
    function of declared facts, so a control can hand it a state that MUST go
    green — which is the only way to tell a working measurer from one that
    returns false unconditionally.
    """

    ar_tables: tuple[str, ...] = ()
    ar_issued_count: int = 0
    # Classes carrying tz_ref or verdict but not the whole shape: (table, lacks).
    ar_near_misses: tuple[tuple[str, tuple[str, ...]], ...] = ()
    artifact_class_count: int = 0
    # What the `reviews` table lacks of the shape, when it exists — it records
    # review of a task closure, and the evidence says so in measured terms.
    reviews_lacks: tuple[str, ...] = ()
    # ADAPT slugs carrying ≥1 backward finding → their status / signature roles.
    adapts_with_findings: dict[str, str] = field(default_factory=dict)
    adapt_signature_roles: dict[str, tuple[str, ...]] = field(default_factory=dict)
    spec_count: int = 0
    spec_provenance_columns: tuple[str, ...] = ()
    specs_without_provenance: int = 0
    adapt_status_domain: tuple[str, ...] = ()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(r[0]) for r in rows}


def _columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})"))


def _status_domain(conn: sqlite3.Connection) -> tuple[str, ...]:
    """Values the ``adapts.status`` CHECK admits, parsed from the stored DDL.

    Reported because a status the schema cannot hold is a stronger finding than
    a row that merely has the wrong one: it says the required state is
    unreachable, not merely absent.
    """
    # One CHECK parser for every closed list (renar_clause_closed_lists);
    # imported here rather than at module level because that module takes
    # `Subcheck` from this one.
    from renar_clause_closed_lists import check_domain

    return check_domain(conn, "adapts", "status") or ()


def collect_state(conn: sqlite3.Connection) -> ReactiveAdaptState:
    """Read the live substrate into a :class:`ReactiveAdaptState`."""
    tables = _table_names(conn)

    classes = artifact_classes(conn)
    ar_tables: list[str] = []
    near: list[tuple[str, tuple[str, ...]]] = []
    reviews_lacks: tuple[str, ...] = ()
    for t in classes:
        have = set(_columns(conn, t))
        lacks = tuple(f for f in AR_SHAPE_FIELDS if f not in have)
        if not lacks:
            ar_tables.append(t)
        elif have & {"tz_ref", "verdict"}:
            near.append((t, lacks))
        if t == "reviews":
            reviews_lacks = lacks
    ar_issued = 0
    for t in ar_tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE status='issued'").fetchone()
        ar_issued += int(row[0]) if row else 0

    with_findings: dict[str, str] = {}
    if {"adapts", "adapt_findings"} <= tables:
        placeholders = ",".join("?" for _ in BACKWARD_FINDING_CATEGORIES)
        for slug, status in conn.execute(
            "SELECT a.slug, a.status FROM adapts a WHERE EXISTS ("
            "  SELECT 1 FROM adapt_findings f"
            f"  WHERE f.adapt_slug = a.slug AND f.category IN ({placeholders}))",
            BACKWARD_FINDING_CATEGORIES,
        ):
            with_findings[str(slug)] = str(status)

    sig_roles: dict[str, tuple[str, ...]] = {}
    if "adapt_signatures" in tables:
        for slug in with_findings:
            roles = conn.execute(
                "SELECT role FROM adapt_signatures WHERE adapt_slug=?", (slug,)
            ).fetchall()
            sig_roles[slug] = tuple(str(r[0]) for r in roles)

    spec_count = 0
    prov_cols: tuple[str, ...] = ()
    specs_bare = 0
    if "specs" in tables:
        row = conn.execute("SELECT COUNT(*) FROM specs").fetchone()
        spec_count = int(row[0]) if row else 0
        cols = _columns(conn, "specs")
        prov_cols = tuple(c for c in SPEC_PROVENANCE_FIELDS if c in cols)
        if prov_cols:
            missing = " AND ".join(f"({c} IS NULL OR {c}='')" for c in prov_cols)
            row = conn.execute(f"SELECT COUNT(*) FROM specs WHERE {missing}").fetchone()
            specs_bare = int(row[0]) if row else 0
        else:
            # No provenance column at all: every SPEC is bare by construction.
            specs_bare = spec_count

    return ReactiveAdaptState(
        ar_tables=tuple(ar_tables),
        ar_issued_count=ar_issued,
        ar_near_misses=tuple(near),
        artifact_class_count=len(classes),
        reviews_lacks=reviews_lacks,
        adapts_with_findings=with_findings,
        adapt_signature_roles=sig_roles,
        spec_count=spec_count,
        spec_provenance_columns=prov_cols,
        specs_without_provenance=specs_bare,
        adapt_status_domain=_status_domain(conn) if "adapts" in tables else (),
    )


def _check_ar_issued(st: ReactiveAdaptState) -> Subcheck:
    shape = "(" + ", ".join(AR_SHAPE_FIELDS) + ")"
    if not st.ar_tables:
        near = (
            "; nearest: " + ", ".join(f"{t} lacks {', '.join(m)}" for t, m in st.ar_near_misses)
            if st.ar_near_misses
            else ""
        )
        reviews = (
            f" The reviews table is NOT counted: it lacks {', '.join(st.reviews_lacks)} — it "
            "records review of a task closure and its code, and an AR is the verdict of a "
            "ТЗ review."
            if st.reviews_lacks
            else ""
        )
        return Subcheck(
            "adversarial-review-issued",
            False,
            "§13.3.3 p.73, p.80",
            f"AR does not exist as an artifact class: none of {st.artifact_class_count} "
            f"artifact classes carries the §7.4.6 record shape {shape}{near} — no "
            "derivation can carry a recorded verdict." + reviews,
        )
    where = ", ".join(st.ar_tables)
    if st.ar_issued_count == 0:
        return Subcheck(
            "adversarial-review-issued",
            False,
            "§13.3.3 p.73",
            f"{where} carries the §7.4.6 shape {shape} but holds zero AR in status 'issued' "
            "— a verdict that was never issued is not a fixed verdict (§7.4.6).",
        )
    return Subcheck(
        "adversarial-review-issued",
        True,
        "§13.3.3 p.73",
        f"{st.ar_issued_count} AR record(s) in status 'issued' in {where} (§7.4.6 shape {shape})",
    )


def _check_adapt_approved(st: ReactiveAdaptState) -> Subcheck:
    unreachable = "approved" not in st.adapt_status_domain if st.adapt_status_domain else False
    bad = {s: v for s, v in st.adapts_with_findings.items() if v != "approved"}
    if unreachable:
        # Reported REGARDLESS of whether any row offends today. Until v50 this
        # sat as a rider on the `bad` branch, so a corpus with no ADAPT carrying
        # backward findings returned GREEN while the required state was
        # UNREACHABLE — the substrate would have rejected 'approved' outright.
        # A control that cannot go red on an empty corpus has forgotten how to
        # fail: the ADR-021 degeneracy this module exists to remove, one floor
        # below. Unreachability outranks the row-level check because no row can
        # ever satisfy it.
        offenders = ", ".join(f"{s}={v}" for s, v in sorted(bad.items())) or "none"
        return Subcheck(
            "adapt-approved-when-findings",
            False,
            "§13.3.3 p.77",
            f"adapts.status admits {list(st.adapt_status_domain)}, and 'approved' is "
            "not among them: the substrate cannot hold the state §13.3.3 requires, so "
            "the clause is unsatisfiable no matter what the rows say "
            f"(ADAPTs carrying backward findings: {offenders}).",
        )
    if bad:
        detail = ", ".join(f"{s}={v}" for s, v in sorted(bad.items()))
        return Subcheck(
            "adapt-approved-when-findings",
            False,
            "§13.3.3 p.77",
            f"{len(bad)} ADAPT(s) carry backward findings but are not 'approved' ({detail}).",
        )
    return Subcheck(
        "adapt-approved-when-findings",
        True,
        "§13.3.3 p.77",
        f"{len(st.adapts_with_findings)} ADAPT(s) with backward findings, all 'approved'"
        if st.adapts_with_findings
        else "no ADAPT carries a backward finding — the 'findings present' branch has no subject",
    )


def _check_architect_signature(st: ReactiveAdaptState) -> Subcheck:
    unsigned = [
        s for s in st.adapts_with_findings if "architect" not in st.adapt_signature_roles.get(s, ())
    ]
    if unsigned:
        return Subcheck(
            "architect-signature-when-findings",
            False,
            "§13.3.3 p.77 → §7.5",
            f"{len(unsigned)} ADAPT(s) with backward findings carry no Architect signature "
            f"({', '.join(sorted(unsigned))}).",
        )
    return Subcheck(
        "architect-signature-when-findings",
        True,
        "§13.3.3 p.77 → §7.5",
        f"{len(st.adapts_with_findings)} ADAPT(s) with backward findings, all signed by the "
        "Architect"
        if st.adapts_with_findings
        else "no ADAPT carries a backward finding — the signature obligation has no subject",
    )


def _check_spec_provenance(st: ReactiveAdaptState) -> Subcheck:
    if st.spec_count == 0:
        return Subcheck(
            "spec-provenance-source",
            True,
            "§13.3.3 p.77/p.78, negative scenario p.90",
            "no SPEC exists — the provenance obligation has no subject",
        )
    if not st.spec_provenance_columns:
        return Subcheck(
            "spec-provenance-source",
            False,
            "§13.3.3 p.90",
            f"{st.spec_count} live SPEC(s) and the specs table has NO provenance column at "
            f"all (looked for {list(SPEC_PROVENANCE_FIELDS)}) — neither source.adapt nor "
            "source.tz-section nor source.adversarial-review-ref can be stored, which is the "
            "negative scenario stated literally. The manifest's normative-inapplicability "
            "section declares why the tz-section half has no subject here; the declaration "
            "explains this red, it does not lift it.",
        )
    if st.specs_without_provenance:
        return Subcheck(
            "spec-provenance-source",
            False,
            "§13.3.3 p.90",
            f"{st.specs_without_provenance} of {st.spec_count} SPEC(s) carry none of "
            f"{list(st.spec_provenance_columns)}.",
        )
    return Subcheck(
        "spec-provenance-source",
        True,
        "§13.3.3 p.77/p.78",
        f"all {st.spec_count} SPEC(s) carry a provenance source",
    )


def evaluate(st: ReactiveAdaptState) -> list[Subcheck]:
    """Every §13.3.3 sub-check against `st`, in citation order. Pure."""
    return [
        _check_ar_issued(st),
        _check_adapt_approved(st),
        _check_architect_signature(st),
        _check_spec_provenance(st),
    ]


def assess(conn: sqlite3.Connection) -> dict[str, Any]:
    """The §13.3.3 clause verdict for the manifest: confirmed + per-check detail."""
    checks = evaluate(collect_state(conn))
    failed = [c for c in checks if not c.ok]
    if failed:
        evidence = f"{len(failed)} of {len(checks)} §13.3.3 sub-check(s) unmet: " + "; ".join(
            f"[{c.name}] {c.evidence}" for c in failed
        )
    else:
        evidence = f"all {len(checks)} §13.3.3 sub-checks met: " + "; ".join(
            f"[{c.name}] {c.evidence}" for c in checks
        )
    return {
        "confirmed": not failed,
        "evidence": evidence,
        "subchecks": [c.as_dict() for c in checks],
    }
