"""Factor collection for the closure risk score (v15-risk-compute-on-done).

Gathers the five canonical risk_model factors from what task_done already
has at hand — the latest signed verify receipt, declared relevant_files,
AC text + notes, and git numstat — then delegates to risk_model.compute_risk.

Best-effort by contract: this module must NEVER block a task close. Any
collection failure drops the factor (risk_model defaults it to a
conservative 1.0 and lists it in `defaulted`); a total failure returns
None and the caller skips risk recording entirely.
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
from typing import Any

import git_exec

_log = logging.getLogger("tausik.risk")


def _is_test_file(path: str) -> bool:
    p = path.replace("\\", "/").lower()
    name = p.rsplit("/", 1)[-1]
    return p.startswith("tests/") or "/tests/" in p or name.startswith("test_")


def _factor_gate_coverage(conn: sqlite3.Connection, slug: str) -> float | None:
    """Gates that actually ran vs configured — both from the signed receipt.

    The configured count is read from `configured_gates_count`, captured in the
    receipt at VERIFY time (risk-gate-coverage-configured-count-in-check). The old
    code recomputed the denominator from `get_gates_for_trigger(load_config())` at
    task-done, so a trust-tier flip between verify and done compared two different
    gate sets and made the factor machine-dependent.

    Legacy receipts (written before this field existed) have no count, so the
    old recompute path is preserved as a FALLBACK — old closes reproduce exactly,
    and a missing field never becomes a crash or a divide-by-zero.
    """
    from verify_receipt_emit import load_receipt

    stored = load_receipt(conn, task_slug=slug)
    if stored is None:
        return None
    receipt = stored["envelope"].get("receipt") or {}
    # Receipts exclude skipped gates by design — len() is the "ran" count.
    ran_gates = receipt.get("gates") or []
    configured = receipt.get("configured_gates_count")
    if not isinstance(configured, int) or configured <= 0:
        # Legacy receipt (no verify-time count) or an unusable value: fall back to
        # the prior behaviour — recompute from the current config. Trust-tier
        # sensitivity returns here, but only for receipts too old to know better.
        from project_config import get_gates_for_trigger, load_config

        configured = len(get_gates_for_trigger("verify", load_config()))
        if configured <= 0:
            return None  # nothing to cover — let the model default conservatively
    return round(1.0 - min(len(ran_gates), configured) / configured, 4)


def _git_numstat_lines(args: list[str], relevant: set[str], cwd: str) -> int:
    # git_exec closes stdin: inside the MCP server sys.stdin is the JSON-RPC pipe;
    # on Windows git probes it (paginator / credential) and blocks, hanging
    # task_done (v14b-defect-mcp-task-done-stdin-hang). This call once shipped
    # unguarded (v15-risk-compute-on-done); the guard now lives in git_exec and
    # cannot be lost by copy-paste again.
    result = git_exec.run(args, cwd=cwd, timeout=10)
    if result.returncode != 0:
        # git_exec.run does NOT raise on nonzero (check=False), unlike the
        # check_output this replaced. Re-raise so _factor_code_churn's except
        # drops the factor → risk_model defaults code_churn to the conservative
        # 1.0 (fail-VISIBLE). Without this, a git failure (unborn HEAD, bad
        # revision, corrupt repo) would yield empty stdout → total=0 → the LOWEST
        # risk reading — a silent fail-OPEN (risk-compute-numstat-fail-open).
        raise subprocess.CalledProcessError(result.returncode, ["git", *args])
    out = result.stdout
    total = 0
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        norm = path.strip().replace("\\", "/")
        if relevant and norm not in relevant:
            continue
        try:
            total += int(added) + int(deleted)
        except ValueError:
            continue  # binary files report '-'
    return total


def _factor_code_churn(
    relevant_files: list[str], started_at: str | None, project_dir: str
) -> float | None:
    """Lines touched: uncommitted diff first, committed-since-start fallback."""
    from risk_model import norm_code_churn

    relevant = {f.replace("\\", "/") for f in relevant_files}
    try:
        lines = _git_numstat_lines(["diff", "--numstat", "HEAD"], relevant, project_dir)
        if lines == 0 and started_at:
            lines = _git_numstat_lines(
                ["log", "--numstat", "--pretty=format:", f"--since={started_at}"],
                relevant,
                project_dir,
            )
        return norm_code_churn(lines)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError):
        return None


def compute_task_risk(
    conn: sqlite3.Connection,
    task: dict[str, Any],
    relevant_files: list[str] | None,
    *,
    project_dir: str = ".",
) -> dict[str, Any] | None:
    """Collect factors and score the closure. Returns None on total failure."""
    try:
        from risk_model import (
            compute_risk,
            norm_ac_evidence,
            norm_security_hits,
            norm_test_delta,
        )

        files = relevant_files or []
        factors: dict[str, float] = {}

        gc = _factor_gate_coverage(conn, str(task.get("slug") or ""))
        if gc is not None:
            factors["gate_coverage"] = gc

        if files:
            tests = sum(1 for f in files if _is_test_file(f))
            factors["test_delta"] = norm_test_delta(len(files) - tests, tests)
            factors["security_hits"] = norm_security_hits(files)

        try:
            from service_ac_evidence import build_report

            rep = build_report(task.get("acceptance_criteria") or "", task.get("notes") or "")
            factors["ac_evidence"] = norm_ac_evidence(rep.total_ac, rep.covered)
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            _log.warning("risk: AC evidence factor failed", exc_info=True)

        churn = _factor_code_churn(files, task.get("started_at"), project_dir)
        if churn is not None:
            factors["code_churn"] = churn

        return compute_risk(factors)
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        try:
            slug = task.get("slug")
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            slug = "?"
        _log.warning("risk computation failed for %s", slug, exc_info=True)
        return None
