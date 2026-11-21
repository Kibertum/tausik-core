"""L3 host capability preflight — TB-009 / bugs.txt Codex read-only path.

A bounded L3 cohort may only consume a repair round after an independent
reviewer can READ the repository under a mechanically read-only surface.
When the host exposes write tools, or a Codex ``read-only`` sandbox still
blocks repository reads (``Get-Content``, ``rg``, ``cmd /c type``), that is
infrastructure — not a product finding. Recording it as ``red`` burned both
defect-repair rounds in dogfood.

This module classifies a declared tool/command surface. It does not launch
Codex; conformance tests pin the matrix that production dispatch must use
before ``cohort-record``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

RECEIPT_KIND = "review_infrastructure_blocked"

#: Tools that make a host write-capable for Rule 4 L3 (mutation editors).
#: Shell/Bash alone is not enough — Codex L3 uses a sandboxed shell for reads;
#: write capability is decided by sandbox probes and explicit editor tools.
_WRITE_TOOLS = frozenset(
    {
        "write",
        "edit",
        "apply_patch",
        "applypatch",
        "strreplace",
        "multiedit",
        "notebookedit",
        "delete",
        "create",
    }
)
#: Tools that are acceptable on a mechanical read-only surface.
_READ_TOOLS = frozenset(
    {"read", "grep", "glob", "search", "webfetch", "websearch", "bash", "shell", "powershell"}
)

#: PowerShell / cmd forms that MUST succeed under Codex L3 read-only.
READONLY_READ_PROBES = (
    "Get-Content",
    "rg",
    "cmd /c type",
)
#: Forms that MUST fail under the same policy.
READONLY_WRITE_PROBES = (
    "Set-Content",
    "Out-File",
    "Remove-Item",
    "New-Item",
)


@dataclass(frozen=True)
class L3Capability:
    """Result of assessing whether an L3 reviewer can do useful work.

    ``enforced`` is False when the project never declared ``review.l3_host``:
    open still reports the gap, but ``cohort-record`` stays compatible with
    hosts that have not opted into the Codex conformance gate yet.
    """

    ok: bool
    code: str
    detail: str
    enforced: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "enforced": self.enforced,
            "receipt_kind": RECEIPT_KIND if (self.enforced and not self.ok) else None,
            "code": self.code,
            "detail": self.detail,
        }


def _norm_tool(name: str) -> str:
    return "".join(ch for ch in name.strip().lower() if ch.isalnum() or ch == "_")


def assess_declared_tools(tools: Iterable[str] | None) -> L3Capability:
    """Classify a declared tool allowlist for mechanical L3 read-only.

    Empty/unknown → not ok (fail-closed: an undeclared surface cannot prove
    read-only). Write-capable names → blocked. Pure read set → ok.
    """
    names = [_norm_tool(t) for t in (tools or []) if str(t).strip()]
    if not names:
        return L3Capability(
            False,
            "L3_HOST_TOOLS_UNDECLARED",
            "no tool allowlist was declared for the L3 reviewer host",
        )
    writes = sorted({n for n in names if n in _WRITE_TOOLS or n.startswith("write")})
    if writes:
        return L3Capability(
            False,
            "L3_HOST_WRITE_CAPABLE",
            "host exposes write-capable tools: " + ", ".join(writes),
        )
    reads = [n for n in names if n in _READ_TOOLS or n.startswith("read")]
    if not reads:
        return L3Capability(
            False,
            "L3_HOST_NO_READ_TOOLS",
            "allowlist has no Read/Grep-class tools, so the reviewer cannot inspect files",
        )
    return L3Capability(True, "L3_HOST_MECHANICAL_READONLY", "read-only tool surface")


def assess_read_probe_results(results: dict[str, bool]) -> L3Capability:
    """Classify live probe outcomes: True means the command was allowed.

    A Codex ``--sandbox read-only`` session that blocks every read probe is
    infrastructure-blocked — the same failure dogfood saw with Get-Content/rg.
    """
    if not results:
        return L3Capability(
            False,
            "L3_READ_PROBES_MISSING",
            "no read-probe results were supplied",
        )
    blocked_reads = [
        name for name in READONLY_READ_PROBES if name in results and results[name] is False
    ]
    if blocked_reads:
        return L3Capability(
            False,
            "L3_READONLY_POLICY_BLOCKS_READS",
            "read-only sandbox blocked repository reads: " + ", ".join(blocked_reads),
        )
    allowed_writes = [
        name for name in READONLY_WRITE_PROBES if name in results and results[name] is True
    ]
    if allowed_writes:
        return L3Capability(
            False,
            "L3_READONLY_POLICY_ALLOWS_WRITES",
            "read-only sandbox allowed mutating commands: " + ", ".join(allowed_writes),
        )
    return L3Capability(True, "L3_READONLY_PROBES_PASS", "read probes allowed; write probes denied")


def assess_l3_host(
    *,
    tools: Iterable[str] | None = None,
    read_probe_results: dict[str, bool] | None = None,
) -> L3Capability:
    """Combine declared tools and optional live probes (fail-closed)."""
    tool_cap = assess_declared_tools(tools)
    if not tool_cap.ok:
        return tool_cap
    if read_probe_results is None:
        return tool_cap
    return assess_read_probe_results(read_probe_results)


def preflight_from_config(cfg: dict[str, Any] | None) -> L3Capability:
    """Read ``review.l3_host`` from config.

    Missing block → advisory (``enforced=False``) so existing Claude L3 cohorts
    keep working. When the block is present, assessment is fail-closed and
    ``cohort-record`` must not consume a repair round on a blocked surface.
    """
    review = cfg.get("review") if isinstance(cfg, dict) else None
    host = review.get("l3_host") if isinstance(review, dict) else None
    if not isinstance(host, dict):
        return L3Capability(
            True,
            "L3_HOST_UNCONFIGURED",
            "config.review.l3_host is unset — capability not enforced; "
            "Codex L3 hosts must declare tools and optional read_probe_results",
            enforced=False,
        )
    tools = host.get("tools")
    probes = host.get("read_probe_results")
    if probes is not None and not isinstance(probes, dict):
        return L3Capability(
            False,
            "L3_HOST_CONFIG_INVALID",
            "review.l3_host.read_probe_results must be an object of bools",
        )
    return assess_l3_host(
        tools=tools if isinstance(tools, list) else None,
        read_probe_results={str(k): bool(v) for k, v in probes.items()} if probes else None,
    )


def load_preflight() -> L3Capability:
    """Effective preflight from the merged project config."""
    try:
        from project_config import load_config

        return preflight_from_config(load_config())
    except Exception as exc:  # noqa: BLE001 — unknown policy is not "ok"
        return L3Capability(
            False,
            "L3_HOST_CONFIG_UNREADABLE",
            f"{type(exc).__name__}: {exc}",
        )
