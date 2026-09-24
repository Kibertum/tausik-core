"""TAUSIK CLI handler for `tausik drift` (v16r-drift-detectors).

Runs the implemented RENAR §3.11 drift detectors on demand — the same read-only
scans wired as warning-mode task-done gates. Exit code stays 0 even with findings
(drift is a warning, never a hard block); the agent reads the listing and acts.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService
from renar_drift import format_findings, run_all, run_detector


def cmd_drift(svc: ProjectService, args: Any) -> None:
    which = getattr(args, "detector", "all") or "all"
    conn = svc.be._conn
    findings = []
    if which in ("all", "standard"):
        findings.extend(_standard_findings(svc))
    if which in ("all", "senar"):
        findings.extend(_senar_findings(svc))
    if which not in ("standard", "senar"):
        findings.extend(run_all(conn) if which == "all" else run_detector(conn, which))
    print(format_findings(findings))


def _standard_findings(svc: ProjectService) -> list[dict[str, str]]:
    """The corpus detector, and a LINE SAYING WHETHER IT RAN.

    It takes a path, not a connection, so it does not live in `renar_drift`'s
    dispatcher. The status line is printed even when there are no findings: the
    epic this belongs to exists because a silence was read as agreement for
    months, and "no drift" must not look like "no corpus".
    """
    import renar_standard_drift as std
    from project_root import root_from_service

    root = std.corpus_root()
    print(std.corpus_status(root))
    if root is None:
        return []
    repo = root_from_service(svc) or "."
    return std.detect_standard_drift(root, repo_mentions=std.adrs_mentioned_in(repo))


def _senar_findings(svc: ProjectService) -> list[dict[str, str]]:
    """The SENAR corpus detector, with its status line (1.10, story F)."""
    import senar_standard_drift as senar
    from project_root import root_from_service

    root = senar.corpus_root()
    print(senar.corpus_status(root))
    if root is None:
        return []
    return senar.detect_senar_drift(root, root_from_service(svc) or ".")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
