"""The collectors themselves. `repo_coherence` is the shape; this is the data.

SPLIT AT THIS SEAM AND NOT ANOTHER (session #240, when the module crossed the
500-line cap). The two halves change for different reasons: what a finding IS —
its shape, how a collector is run safely, the volume ceiling, the severity order,
the stated boundary of what is not examined — changes almost never, while THIS
file changes every time a collector is added. That is the same seam already used
twice in this release: `gate_spec` split from `gate_registry`, and
`gate_shellless_exec` from `gate_command_runner`.

Every function here is imported BY `repo_coherence.collect`, inside the
function body — which is also what keeps the import one-directional: this module
takes `Finding` from there at module level, and nothing there needs this one
until it runs. The public surface of the lens is unchanged: callers keep
importing `collect`, `render_markdown`, `render_json` and `Finding` from
`repo_coherence`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from repo_coherence_shape import Finding


def _orphans(root: Path) -> list[Finding]:
    import audit_orphan_files

    orphans = audit_orphan_files.collect_orphans(root)
    if not orphans:
        return []
    return [
        Finding(
            "orphan_files",
            "medium",
            f"{len(orphans)} tracked file(s) nothing references",
            source="audit_orphan_files",
            count=len(orphans),
            detail="\n".join(orphans[:10]),
        )
    ]


def _duplicate_tests(root: Path) -> list[Finding]:
    import audit_pytest_dedupe

    groups = audit_pytest_dedupe.collect_duplicates(root)
    if not groups:
        return []
    # `members`, not `tests` — read off the real producer rather than guessed.
    # The first draft guessed and reported "covering 0 tests", which is the
    # under-reporting direction: a lens that undercounts looks like a cleaner
    # repository than it measured.
    total = 0
    for group in groups:
        members = group.get("members")
        if isinstance(members, list):
            total += len(members)
    return [
        Finding(
            "duplicate_tests",
            "medium",
            f"{len(groups)} group(s) of structurally indistinguishable tests "
            f"covering {total} test(s)",
            source="audit_pytest_dedupe",
            count=len(groups),
            detail="Tests that share an AST shape modulo names, strings and numbers.",
        )
    ]


def _stale_docs(root: Path) -> list[Finding]:
    import audit_stale_docs

    stale = audit_stale_docs.collect_stale(root)
    if not stale:
        return []
    return [
        Finding(
            "stale_docs",
            "medium",
            f"{len(stale)} document(s) older than the code they describe",
            source="audit_stale_docs",
            count=len(stale),
            detail="\n".join(stale[:10]),
        )
    ]


def _unused_python(root: Path) -> list[Finding]:
    import audit_unused_python

    rows = audit_unused_python.collect_unused(root)
    if not rows:
        return []
    return [
        Finding(
            "unreachable_python",
            "high",
            f"{len(rows)} Python module(s) nothing imports or runs",
            source="audit_unused_python",
            count=len(rows),
            detail="\n".join(str(r.get("path", r)) for r in rows[:10]),
        )
    ]


def _translation_drift(root: Path) -> list[Finding]:
    import audit_translation_drift

    drifts, en_only, ru_only, _abbrev = audit_translation_drift.audit_pairs(root)
    out: list[Finding] = []
    if drifts:
        out.append(
            Finding(
                "translation_drift",
                "low",
                f"{len(drifts)} document pair(s) whose two languages have drifted apart",
                source="audit_translation_drift",
                count=len(drifts),
            )
        )
    lonely = len(en_only) + len(ru_only)
    if lonely:
        out.append(
            Finding(
                "unpaired_docs",
                "low",
                f"{lonely} document(s) exist in one language only",
                source="audit_translation_drift",
                count=lonely,
            )
        )
    return out


def _doc_number_drift(root: Path) -> list[Finding]:
    """Numbers the prose states about itself, against what is actually there.

    THE CALIBRATION CLASS this lens would otherwise miss. "The docs say eleven
    breaking changes and the tree has nine" is a coherence defect no per-file
    gate can see: each document is internally fine, and only the whole
    disagrees. The scanners already exist and already know how to answer —
    they were simply never asked as part of one question.
    """
    import doc_drift_scanners
    import gen_doc_constants

    payload = gen_doc_constants.build_constants_doc(root)
    version = gen_doc_constants.read_project_version(root)
    messages: list[str] = []
    for label, scan in (
        ("version refs", lambda: doc_drift_scanners.scan_version_refs(root, version)),
        ("mcp tool counts", lambda: doc_drift_scanners.scan_mcp_tool_counts(root, payload)),
        ("closed-list enums", lambda: doc_drift_scanners.scan_closed_list_enums(root, payload)),
        ("test counts", lambda: doc_drift_scanners.scan_test_counts(root, payload)),
        ("code-state counts", lambda: doc_drift_scanners.scan_code_counts(root, payload)),
        (
            "counted table columns",
            lambda: doc_drift_scanners.scan_table_count_columns(root, payload),
        ),
    ):
        found = scan()
        messages += [f"{label}: {m}" for m in found]
    if not messages:
        return []
    return [
        Finding(
            "doc_number_drift",
            "high",
            f"{len(messages)} number(s) the documentation states about itself are wrong",
            source="doc_drift_scanners",
            count=len(messages),
            detail="\n".join(messages[:10]),
        )
    ]


def _senar_claim_citations(root: Path) -> list[Finding]:
    """The conformance pages cite code; does that code still exist?

    Belongs in THIS lens rather than in a gate because it is the same class the
    lens exists for: each page is internally fine, and only the pairing with the
    tree is wrong. A renamed module turns a true claim into an unfalsifiable one
    without editing a word of the claim.

    The uncited rows are surfaced at a lower severity because they are not rot —
    they are a statement about how evenly the page is evidenced, and the totals
    printed underneath count them the same as the rest.
    """
    import senar_self_check

    # Only pages that EXIST. Asked about a named page, `check` treats absence as
    # a broken citation and is right to — the page took its evidence with it.
    # Asked to audit a repository, that same rule would tell every consumer
    # project that its conformance citations are broken, when those pages are
    # ours and were never theirs. A lens that cries wolf in every installation
    # is a lens nobody reads twice.
    present = tuple(p for p in senar_self_check.MATRICES if (root / p).is_file())
    if not present:
        return []

    report = senar_self_check.check(root, present)
    findings: list[Finding] = []
    if report.broken:
        findings.append(
            Finding(
                "senar_claim_citations",
                "high",
                f"{len(report.broken)} citation(s) on the conformance pages point at code that is gone",
                source="senar_self_check",
                count=len(report.broken),
                detail="\n".join(f"{c.where()} {why}" for c, why in report.broken[:10]),
            )
        )
    if report.uncited:
        findings.append(
            Finding(
                "senar_claim_citations",
                "low",
                f"{len(report.uncited)} conformance row(s) cite nothing checkable",
                source="senar_self_check",
                count=len(report.uncited),
                detail="\n".join(f"{c.where()} {c.subject}" for c in report.uncited[:10]),
            )
        )
    return findings


def _tests_never_observed_red(root: Path) -> list[Finding]:
    """How much red history this checkout has accumulated, and what it is worth.

    RENAR §9.18.2: a test never seen failing has not shown it can fail. The
    history accumulates only by RUNNING the suite, so on a fresh clone it is
    empty — and an empty history is silence, not a verdict about the tests. The
    finding therefore reports the SIZE of the history rather than a list of
    unproven tests, which would be every test in the tree on day one and would
    be read as an accusation.

    Severity stays low while the rule is reporting-only. Raising it before the
    threshold in `red_history.REPORTING_ONLY` would put a number at the top of
    the report that nobody can act on.
    """
    import red_history

    db = str(root / ".tausik" / "tausik.db")
    if not os.path.isfile(db):
        return []
    known = red_history.count(db)
    ready = known >= red_history.BLOCKING_NEEDS_NODES
    return [
        Finding(
            "red_history",
            "low",
            f"{known} test node(s) have ever been observed failing on this checkout"
            + ("" if ready else f" — below the {red_history.BLOCKING_NEEDS_NODES} needed to judge"),
            source="red_history",
            count=known,
            detail=(
                "A test never seen red has not shown it can fail (RENAR 9.18.2). "
                "History accumulates only by running the suite and does NOT travel "
                "between machines: the database is not version-controlled."
            ),
        )
    ]


def _closure_evidence_baseline(root: Path) -> dict[str, int]:
    """The pinned historical remainder, or zeros when none is declared.

    Zeros rather than None: a project with no baseline has declared no
    remainder, so every finding is growth — which is the strict reading and the
    right default for a project that has not opted in.
    """
    try:
        node = json.loads((root / "tausik" / "gates.json").read_text(encoding="utf-8"))
        baseline = (node.get("closure_evidence") or {}).get("baseline") or {}
    except (OSError, ValueError, AttributeError):
        return {"rotted": 0, "never_existed": 0}
    return {
        key: int(baseline.get(key, 0)) if isinstance(baseline.get(key), int) else 0
        for key in ("rotted", "never_existed")
    }


def _rotted_evidence(root: Path, tasks: list[dict[str, Any]]) -> list[Finding]:
    """Closure citations that no longer resolve, against a DECLARED remainder.

    WHY A BASELINE AND NOT A RATCHET AT ZERO. Closure journals are append-only:
    these citations sit inside tasks closed long ago, and rewriting them would
    forge the very evidence this project exists to keep honest. So the
    historical set cannot be cleaned — but it also cannot grow unnoticed, since
    session #240, when `task done` began checking a task's own citations while
    the author is still there to fix them.

    A finding that repeats every run and cannot be acted on does not stay
    unread — it teaches the reader to skip its whole SEVERITY. Pinning the
    history is what keeps `high` meaning something.
    """
    import audit_closure_evidence

    report = audit_closure_evidence.audit_closure_evidence(str(root), tasks)
    # The producer returns {"counts": {...}, "findings": [...]}. Reading the
    # counts it publishes beats re-counting its findings here — one more place
    # to disagree with it, for nothing.
    counts = report.get("counts") or {}
    pinned = _closure_evidence_baseline(root)
    out: list[Finding] = []

    for key, kind, phrase, why in (
        (
            "rotted",
            "rotted_closure_evidence",
            "name a test that no longer exists",
            "A closure whose evidence cannot be resolved is unverifiable today.",
        ),
        (
            "never_existed",
            "invented_closure_evidence",
            "name a test git NEVER had",
            "Worse than rot: the reference was already wrong when written.",
        ),
    ):
        measured = int(counts.get(key) or 0)
        if not measured:
            continue
        allowed = pinned[key]
        if measured > allowed:
            out.append(
                Finding(
                    kind,
                    "high",
                    f"{measured} closure citation(s) {phrase} — ABOVE the declared "
                    f"remainder of {allowed}",
                    source="audit_closure_evidence",
                    count=measured - allowed,
                    detail=why + " New ones are caught at closure since #240.",
                )
            )
        elif measured < allowed:
            out.append(
                Finding(
                    kind,
                    "low",
                    f"the declared remainder for `{key}` is {allowed} and only "
                    f"{measured} remain — tighten it in tausik/gates.json",
                    source="audit_closure_evidence",
                    count=allowed - measured,
                    detail="A baseline above the truth is a lie in the other direction.",
                )
            )
        else:
            out.append(
                Finding(
                    kind,
                    "low",
                    f"{measured} historical closure citation(s) {phrase} — declared "
                    "remainder, unchanged",
                    source="audit_closure_evidence",
                    count=measured,
                    detail=(
                        "Journals are append-only, so these cannot be corrected; "
                        "new ones are caught at closure since session #240."
                    ),
                )
            )
    return out


def _graph_staleness(root: Path, service: Any) -> list[Finding]:
    """The artifact graph's own honesty, folded into the same report."""
    stale = service.graph_stale_artifacts(root=str(root))
    if not stale:
        return []
    return [
        Finding(
            "stale_graph",
            "low",
            f"{len(stale)} artifact(s) in the graph no longer match the file on disk",
            source="artifact_graph",
            count=len(stale),
            detail="Answers touching these are reported partially stale by design.",
        )
    ]


#: What this lens does NOT look at. Stated in the report itself, because a
#: reader who cannot see the boundary will read silence as a clean bill.
