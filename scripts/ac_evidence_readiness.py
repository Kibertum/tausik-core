"""Cohort/hierarchy readiness: numbered AC evidence via the shared parser.

TB-008: `LIKE '%AC-%'` missed documented forms such as
`AC verified: 1. ✓ …`. Callers share this helper so readiness and packet
assembly cannot disagree with QG-2's `build_report`.
"""

from __future__ import annotations

from service_ac_evidence import build_report, parse_evidence_lines


def has_numbered_evidence_logged(ac_text: str, notes_text: str) -> bool:
    """True when notes carry numbered AC evidence the shared parser recognizes."""
    notes = notes_text or ""
    report = build_report(ac_text or "", notes)
    if report.covered > 0:
        return True
    return any(ev.ac_index is not None for ev in parse_evidence_lines(notes))
