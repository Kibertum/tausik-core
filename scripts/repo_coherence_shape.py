"""What a finding IS, and how a collector is run safely.

THE SEAM, chosen when `repo_coherence` crossed the 500-line cap (session #240).
The shape of a finding, the volume ceiling, the severity order, the safe-run
wrapper and the stated boundary of what is NOT examined change almost never.
The collectors change every time one is added. Splitting on that line is what
lets both halves stay small, and it is the same seam used twice already this
release: `gate_spec` from `gate_registry`, `gate_shellless_exec` from
`gate_command_runner`.

Everything here is re-exported by `repo_coherence`, so every existing
`from repo_coherence import Finding` keeps working.
"""

from __future__ import annotations

from typing import Any, Callable

MAX_FINDINGS = 40

#: Risk order. Not a score with invented precision — a coarse ordering, which is
#: all a ranked list needs, and all the evidence below can honestly support.
SEVERITY_ORDER = ("high", "medium", "low")


class Finding:
    """One observation, with the collector that made it and why it matters."""

    __slots__ = ("kind", "severity", "summary", "detail", "source", "count")

    def __init__(
        self,
        kind: str,
        severity: str,
        summary: str,
        *,
        source: str,
        count: int = 1,
        detail: str = "",
    ) -> None:
        self.kind = kind
        self.severity = severity
        self.summary = summary
        self.detail = detail
        self.source = source
        self.count = count

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "summary": self.summary,
            "detail": self.detail,
            "source": self.source,
            "count": self.count,
        }


def _safe(
    name: str,
    fn: Callable[[], list[Finding]],
    skipped: list[str],
    ran: list[str] | None = None,
) -> list[Finding]:
    """Run one collector; a failure DEMOTES it to a named gap, never to silence.

    A lens that quietly drops a collector reports a cleaner repository than it
    measured, which is the one failure mode that makes the whole thing worse
    than nothing.

    `ran` records the ATTEMPT, before the call, so the reported total counts what
    was actually asked rather than a literal kept in step by hand. The previous
    `6 + ...` went stale the moment a seventh collector was added — the same
    class of defect this lens exists to find, sitting in the lens.
    """
    if ran is not None:
        ran.append(name)
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — one collector must not take the lens down
        skipped.append(f"{name}: {type(e).__name__}: {e}")
        return []


NOT_EXAMINED = (
    "runtime behaviour — nothing here executes the product",
    "semantic correctness of any document; only staleness and pairing",
    "whether a test is GOOD; only whether it is distinguishable from another",
    "security properties",
    "anything outside version control",
)
