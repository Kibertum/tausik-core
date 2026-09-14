"""Ask about THIS task's citations while the author is still here.

THE DETECTOR ALREADY EXISTED and that is the whole point of this module. Across
1,404 closed tasks and 4,026 citations, `audit_closure_evidence` reports 20 that
name a test git NEVER had and 31 that name one which vanished AFTER the closure.
Nothing was missing but the ASKING: the detector runs on demand — `tausik
coherence`, `tausik audit evidence` — and nobody ran it at the moment a citation
was written. So an invented reference is discovered months later, when the
journal is append-only and there is nothing left to correct.

This asks about ONE task, at its close, when the person who wrote the reference
can still fix it.

WHY A NOTICE AND NOT A BLOCK. The error direction is over-detection: a citation
may fail to resolve because the file is not committed yet, because the name was
quoted as an EXAMPLE, or because the test lives outside the scanned roots.
Refusing a close on that teaches the agent not to cite at all — destroying the
evidence in order to check it. The detector already separates the three
outcomes; only `never_existed` is worth a word here, and `rotted` is not: a test
renamed after THIS closure cannot exist yet at THIS closure.

MEASURED COST (session #240, this repository): the check runs over one task's
notes, and the file index it needs is built once per call — 0.3 s on a tree of
513 test files. That is the price of a close, not of a keystroke, and a close
already runs thirteen gates.
"""

from __future__ import annotations

from typing import Any

__all__ = ["check_citations", "warning_for", "citation_warning"]


def check_citations(repo_root: str, slug: str, notes: str) -> list[str]:
    """Citations in `notes` that name a test which never existed.

    Returns the references themselves, so the caller can name them. An empty
    list means either "everything resolves" or "nothing was cited" — the two are
    not distinguished here because the closure path already warns separately
    about citing nothing.

    Never raises. A check that can break a close is a check that gets removed,
    and this one is advisory by design.
    """
    if not notes:
        return []
    try:
        from audit_closure_evidence import NEVER_EXISTED, audit_closure_evidence

        report = audit_closure_evidence(repo_root, [{"slug": slug, "notes": notes}])
    except Exception:  # noqa: BLE001 — advice must never break a close
        return []

    findings: list[dict[str, Any]] = report.get("findings") or []
    return [
        str(f.get("ref")) for f in findings if f.get("verdict") == NEVER_EXISTED and f.get("ref")
    ]


def warning_for(repo_root: str, slug: str, notes: str) -> str:
    """The line `task done` prints, or an empty string.

    Names the references rather than counting them: "2 citations do not resolve"
    sends the reader back to the journal to find which, and that search is the
    whole cost the notice exists to save.
    """
    bad = check_citations(repo_root, slug, notes)
    if not bad:
        return ""
    listed = ", ".join(bad[:5])
    more = f" (+{len(bad) - 5} more)" if len(bad) > 5 else ""
    return (
        f"NOTE: {len(bad)} closure citation(s) name a test this repository has "
        f"never had: {listed}{more}. Not a block — the name may be an example, or "
        "the file may be uncommitted. But if it was written from memory, this is "
        "the last moment it can be corrected: the journal is append-only."
    )


def citation_warning(slug: str, notes: str) -> str:
    """`warning_for` with the project root resolved, for the closure path.

    Lives here rather than in `service_task_done` because that module sits at
    the 500-line cap: a nine-line helper there costs a split, and the root
    resolution belongs beside the check that needs it anyway.
    """
    import os

    return warning_for(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(), slug, notes)
