"""TAUSIK GatesMixin — QG-0/QG-2 verification logic for task lifecycle.

Thin aggregator: QG-0 Context Gate + QG-2 AC/Plan/Checklist checks live as
pure free functions in `gate_qg0_check` / `gate_ac_check`; the mixin keeps
the verify-pipeline + Verify-First Contract enforcement (which depend on
`self.be._conn` / `self.be.task_append_notes`).

Re-exports for backward compatibility (the `# noqa: F401` import block below is
authoritative — existing callers can still do `from service_gates import …`):
- `SECURITY_KEYWORDS`, `SECURITY_AC_KEYWORDS`, `check_qg0_start` — from `gate_qg0_check`
- `NEGATIVE_SCENARIO_KEYWORDS`, `has_negative_scenario` — from `gate_negative_scenario`
- `qg0_dimensions_score` — from `gate_qg0_score`
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from gate_ac_check import (
    check_verification_checklist,
    determine_checklist_tier,
    verify_ac,
    verify_plan_complete,
)
from gate_negative_scenario import (  # noqa: F401
    NEGATIVE_SCENARIO_KEYWORDS,
    has_negative_scenario,
)
from gate_qg0_check import (  # noqa: F401
    SECURITY_AC_KEYWORDS,
    SECURITY_KEYWORDS,
    check_qg0_start,
)
from gate_qg0_score import qg0_dimensions_score  # noqa: F401
from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


class GatesMixin:
    """QG-0 and QG-2 verification methods for task lifecycle."""

    be: SQLiteBackend

    def run_verify_for_task(
        self,
        task_slug: str | None,
        relevant_files: list[str] | None = None,
        scope: str = "standard",
        trigger: str = "verify",
    ) -> dict[str, Any]:
        """Public Verify-First entry point — wraps run_gates_with_cache.

        v1.4: replaces the prior MCP `_handle_verify` direct access to
        `svc.be._conn`, keeping CLI/MCP layered through the service. Returns
        a structured dict so MCP can format consistently.

        Behavior:
          - With `task_slug`: scoped verify against the task's relevant_files
            (if not passed explicitly) and recorded in `verification_runs`.
          - Without `task_slug`: full-suite, file-scope empty, no DB write.
            Mirrors `tausik verify` CLI without --task.
          - `trigger` defaults to "verify" so this is the canonical entrypoint
            for the Verify-First Contract; pass "task-done" to dry-run the
            cheap-gate pipeline.
        """
        from service_verification import run_gates_with_cache

        files: list[str] = list(relevant_files or [])
        task_created_at: str | None = None
        if task_slug:
            task = self.be.task_get(task_slug)
            if task is None:
                raise ServiceError(f"Task '{task_slug}' not found")
            if not files:
                raw = task.get("relevant_files") or "[]"
                try:
                    import json as _json

                    files = _json.loads(raw) if raw else []
                except (TypeError, ValueError):
                    files = []
            # v1.5: prefer started_at — see verify_git_diff docstring; the
            # cross-check window is "since work started", not "since the
            # backlog entry was created" (permanent false mismatch otherwise).
            task_created_at = task.get("started_at") or task.get("created_at")
        passed, results, status = run_gates_with_cache(
            self.be._conn,
            task_slug or "",
            files or None,
            scope=scope,
            append_notes_fn=(self.be.task_append_notes if task_slug else None),
            task_created_at=task_created_at,
            trigger=trigger,
        )
        return {
            "passed": passed,
            "status": status,
            "scope": scope,
            "trigger": trigger,
            "task_slug": task_slug,
            "results": results,
        }

    def _check_qg0_start(self, slug: str, task: dict[str, Any]) -> list[str]:
        """QG-0 Context Gate — delegates to gate_qg0_check.check_qg0_start.

        Threads optional `audit_check` / `session_check_duration` callbacks
        from the composing service (ProjectService) when available.
        """
        from gate_qg0_renar import renar_qg0_advisory

        return check_qg0_start(
            slug,
            task,
            audit_check_fn=getattr(self, "audit_check", None),
            session_check_duration_fn=getattr(self, "session_check_duration", None),
            renar_advisory_fn=lambda: renar_qg0_advisory(self.be, task, slug),
        )

    def _verify_ac(self, slug: str, task: dict[str, Any], ac_verified: bool) -> list[str]:
        """QG-2 AC verification — delegates to gate_ac_check.verify_ac."""
        return verify_ac(slug, task, ac_verified)

    def _verify_plan_complete(self, slug: str, task: dict[str, Any]) -> None:
        """Plan-complete check — delegates to gate_ac_check.verify_plan_complete."""
        verify_plan_complete(slug, task)

    def _determine_checklist_tier(
        self,
        task: dict[str, Any],
        relevant_files: list[str] | None = None,
    ) -> str:
        """Tier auto-detect — delegates to gate_ac_check.determine_checklist_tier."""
        return determine_checklist_tier(task, relevant_files)

    def _check_verification_checklist(self, slug: str, task: dict[str, Any]) -> str:
        """SENAR Rule 5 checklist — delegates to gate_ac_check.check_verification_checklist."""
        return check_verification_checklist(task)

    @staticmethod
    def _extract_files_from_gate_output(output: str) -> list[str]:
        files = re.findall(r"^\s+([^\s:]+):\s+\d+\s+lines", output or "", re.MULTILINE)
        return files

    def _run_quality_gates_report(
        self,
        slug: str,
        relevant_files: list[str] | None,
        progress_fn: Any | None = None,
        trigger: str = "task-done",
    ) -> dict[str, Any]:
        """Return detailed gate report for MCP/agent-friendly handling.

        Verify-First Contract (v1.4): when called with trigger="task-done"
        (the default — i.e. via the `task_done` flow), this method ALSO
        checks whether a fresh `tausik verify` green exists for this task
        and refuses to close the task if not. The check is opt-out via
        `config.task_done.auto_verify=true` for the legacy "run heavy gates
        inline" behavior — useful in CI where one long step is fine but
        interactive MCP hosts (VS Code Claude Extension) hang.

        When called with trigger="verify" (i.e. via `tausik verify --task`),
        this method runs the verify-trigger gates and records the result in
        `verification_runs`. No "fresh verify run" check — that would be
        circular.
        """
        report: dict[str, Any] = {
            "passed": True,
            "results": [],
            "cache_status": None,
            "blocking_failures": [],
            "scope": None,
        }
        try:
            from service_verification import (
                is_security_sensitive,
                run_gates_with_cache,
            )
        except ImportError:
            import logging

            logging.getLogger("tausik.gates").warning("service_verification not available")
            return report

        task = self.be.task_get(slug) or {}
        scope = self._determine_checklist_tier(task, relevant_files=relevant_files)
        if is_security_sensitive(relevant_files or []):
            scope = "critical"
        report["scope"] = scope

        passed, results, status = run_gates_with_cache(
            self.be._conn,
            slug,
            relevant_files,
            scope=scope,
            append_notes_fn=self.be.task_append_notes,
            task_created_at=task.get("started_at") or task.get("created_at"),
            progress_fn=progress_fn,
            trigger=trigger,
        )
        report["passed"] = passed
        report["results"] = results
        report["cache_status"] = status

        if not passed:
            failed = [r for r in results if not r.get("passed") and r.get("severity") == "block"]
            report["blocking_failures"] = [
                {
                    "gate": r.get("name"),
                    "files": self._extract_files_from_gate_output(r.get("output", "")),
                    "output": r.get("output", ""),
                    "remediation": (
                        "Fix gate issues and rerun task_done. For filesize: "
                        "split oversized modules or configure "
                        "gates.filesize.exempt_files in .tausik/config.json."
                    ),
                }
                for r in failed
            ]
            return report

        # Verify-First Contract enforcement: only on the task-done path,
        # only when there ARE verify-trigger gates configured (otherwise no
        # heavy verification was ever expected — small projects are fine),
        # and only when auto_verify is NOT explicitly opted-in.
        if trigger == "task-done":
            self._enforce_verify_first(report, slug, relevant_files)
        return report

    def _enforce_verify_first(
        self,
        report: dict[str, Any],
        slug: str,
        relevant_files: list[str] | None,
    ) -> None:
        """Add a synthetic blocking_failure if no fresh `tausik verify` run
        exists for this task and the project has verify-trigger gates.

        Three opt-out paths:
          - config.task_done.auto_verify = true  →  legacy inline behavior;
            in that case we run the verify-trigger gates inline right here.
          - No verify-trigger gates configured (small projects, no pytest
            etc.) →  nothing to wait on, skip enforcement.
          - Security-sensitive files →  cache always refused, but we still
            require an explicit verify run; the agent must call `tausik
            verify` immediately before `task done` to avoid stale greens.
        """
        from service_verification import (
            DEFAULT_CACHE_TTL_S,
            has_fresh_verify_run,
            run_gates_with_cache,
        )

        try:
            from project_config import get_gates_for_trigger, load_config

            cfg = load_config()
            verify_gates = get_gates_for_trigger("verify", cfg)
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            verify_gates = []
            cfg = {}
        if not verify_gates:
            return  # no heavy gates configured, nothing to enforce

        td_cfg = cfg.get("task_done", {}) if isinstance(cfg, dict) else {}
        auto_verify = bool(td_cfg.get("auto_verify", False))
        ttl = int(
            cfg.get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
            if isinstance(cfg, dict)
            else DEFAULT_CACHE_TTL_S
        )

        fresh, hit = has_fresh_verify_run(self.be._conn, slug, relevant_files, max_age_s=ttl)
        if fresh and hit is not None:
            # v15-receipt-check-on-done: a cached green only counts if its
            # signed receipt still verifies — tamper-evidence for QG-2.
            from verify_receipt_check import check_receipt_for_hit

            ok, note = check_receipt_for_hit(self.be._conn, hit["id"], slug)
            self.be.task_append_notes(
                slug,
                f"Verify-First: cache hit (verify run #{hit['id']} at {hit['ran_at']}) | {note}",
            )
            if not ok:
                report["passed"] = False
                report["blocking_failures"].append(
                    {
                        "gate": "receipt-signature",
                        "files": [],
                        "output": note,
                        "remediation": (
                            f"Re-run `tausik verify --task {slug}` to record a "
                            f"freshly signed receipt; inspect `tausik receipt "
                            f"show --run {hit['id']}` and `tausik key show` if "
                            "it persists."
                        ),
                    }
                )
            return

        if auto_verify:
            # Legacy CI-style behavior: run the verify trigger inline.
            self.be.task_append_notes(
                slug,
                "Verify-First: auto_verify=true — running verify gates inline "
                "(legacy behavior; task_done will block until they finish).",
            )
            try:
                passed, results, _status = run_gates_with_cache(
                    self.be._conn,
                    slug,
                    relevant_files,
                    scope=report.get("scope") or "standard",
                    append_notes_fn=self.be.task_append_notes,
                    trigger="verify",
                )
            except Exception as e:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
                report["passed"] = False
                report["blocking_failures"].append(
                    {
                        "gate": "verify-first",
                        "files": [],
                        "output": f"auto_verify run crashed: {e}",
                        "remediation": (
                            "Fix the failing verify gate or set "
                            "config.task_done.auto_verify=false and run "
                            "`tausik verify` manually."
                        ),
                    }
                )
                return
            if not passed:
                report["passed"] = False
                blocking = [
                    r for r in results if not r.get("passed") and r.get("severity") == "block"
                ]
                report["blocking_failures"].extend(
                    {
                        "gate": r.get("name"),
                        "files": self._extract_files_from_gate_output(r.get("output", "")),
                        "output": r.get("output", ""),
                        "remediation": (
                            "Fix gate issues and rerun task_done. "
                            "(auto_verify=true caused inline run.)"
                        ),
                    }
                    for r in blocking
                )
            return

        # Default v1.4 behavior: refuse to close.
        gate_names = ", ".join(g.get("name", "?") for g in verify_gates)
        report["passed"] = False
        report["blocking_failures"].append(
            {
                "gate": "verify-first",
                "files": list(relevant_files or []),
                "output": (
                    f"QG-2: no fresh `tausik verify` run for this task "
                    f"(verify gates configured: {gate_names}). "
                    f"Run `tausik verify --task {slug}` first — it caches; "
                    f"then `task done` closes in milliseconds. To opt out "
                    f"set config.task_done.auto_verify=true (legacy)."
                ),
                "remediation": (
                    f".tausik/tausik verify --task {slug}  &&  "
                    f".tausik/tausik task done {slug} --ac-verified"
                ),
            }
        )

    def _run_quality_gates(
        self, slug: str, relevant_files: list[str] | None, progress_fn: Any | None = None
    ) -> None:
        """QG-2 Implementation Gate: scoped gates with verify cache.

        Delegates to `service_verification.run_gates_with_cache` — see that
        module for cache rules (10 min TTL, files_hash invalidation,
        security-sensitive bypass). The scope passed in (and recorded with
        the verify run) is derived from the task's complexity tier per
        SENAR Rule 5: simple→lightweight, medium→standard, complex→high.
        Security-sensitive `relevant_files` (per `is_security_sensitive`)
        promote to `critical`.
        """
        gate_report = self._run_quality_gates_report(slug, relevant_files, progress_fn=progress_fn)
        if not gate_report["passed"]:
            failures = gate_report.get("blocking_failures", [])
            details = "; ".join(
                f"{f.get('gate')}: {(f.get('output') or '')[:140]}" for f in failures
            )
            raise ServiceError(
                f"QG-2 Implementation Gate: blocking gates failed for '{slug}'. "
                f"Fix issues first: {details}"
            )
