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
    findings = run_all(conn) if which == "all" else run_detector(conn, which)
    print(format_findings(findings))
