"""TAUSIK task_done report generation — extracted from service_task.py.

Holds the heavy `_task_done_report` body and the `_format_task_done_failures`
helper. Mixed into TaskMixin via TaskDoneReportMixin so existing call-sites
(svc._task_done_report, harness/*/mcp/project/handlers.py) keep working
unchanged. Pure re-org for the 400-line filesize gate
(filesize-debt-paydown-2). No semantic changes.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from tausik_utils import ServiceError, utcnow_iso
from model_pinning import model_done_updates
from service_recording import record_call_actual, record_cost_actual

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


def _root_cause_hard_enabled() -> bool:
    """config task_done.root_cause_hard, default True (fail-closed policy —
    see docs/ru/research/failclosed-gates-audit.md)."""
    try:
        from project_config import load_config

        td = load_config().get("task_done", {})
        if isinstance(td, dict):
            return bool(td.get("root_cause_hard", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True


def _checklist_hard_enabled() -> bool:
    """config task_done.checklist_hard, default True (SENAR Rule 5 hard gate
    for substantial/deep planning tiers — v15s-rule5-checklist-hardgate)."""
    try:
        from project_config import load_config

        td = load_config().get("task_done", {})
        if isinstance(td, dict):
            return bool(td.get("checklist_hard", True))
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass
    return True


def _format_task_done_failures(report: dict[str, Any]) -> str:
    """v1.4: aggregate ALL blocking failures into the v1 ServiceError message.

    Pre-1.4 behavior surfaced only ``failures[0]["message"]`` which silently
    hid AC-stage and gate-stage failures when both happened (e.g. AC missing
    AND filesize gate failing — only AC was reported, then closing the AC
    issue would surface the gate failure on the next attempt). After 1.4 the
    agent sees every blocking issue at once.

    Falls back to the legacy 'task_done failed' string when blocking_failures
    is empty (defensive — should not happen in practice). Per-failure message
    cap at 180 chars matches existing _task_done_report formatting.
    """
    failures = report.get("blocking_failures") or []
    if not failures:
        return "task_done failed"
    if len(failures) == 1:
        return failures[0].get("message") or "task_done failed"
    parts = ["task_done blocked by multiple failures:"]
    for i, f in enumerate(failures, start=1):
        msg = (f.get("message") or "")[:180]
        stage = f.get("stage") or "?"
        gate = f.get("gate")
        prefix = f"  [{i}] stage={stage}"
        if gate:
            prefix += f" gate={gate}"
        parts.append(f"{prefix}: {msg}")
    return "\n".join(parts)


class TaskDoneReportMixin:
    """Mixin providing _task_done_report. Composed into TaskMixin.

    Relies on sibling mixins for: _require_task (ProjectService),
    _verify_ac / _verify_plan_complete / _run_quality_gates_report /
    _check_verification_checklist (GatesMixin), _cascade_done (CascadeMixin),
    task_log (TaskMixin itself).
    """

    be: SQLiteBackend

    def _task_done_report(
        self,
        slug: str,
        *,
        relevant_files: list[str] | None,
        ac_verified: bool,
        no_knowledge: bool,
        evidence: str | None,
        evidence_json: str | None = None,
        progress_fn: Any | None = None,
    ) -> dict[str, Any]:
        # v14b-token-t15: structured evidence — convert JSON to canonical
        # prose before the existing log path. Mutex with --evidence prose
        # (caller intent must be unambiguous; prose wins by virtue of being
        # the legacy form, but disallowing both keeps the behavior obvious).
        if evidence is not None and evidence_json is not None:
            raise ServiceError("task_done: 'evidence' and 'evidence_json' are mutually exclusive")
        if evidence_json is not None:
            from service_ac_evidence import evidence_json_to_prose

            evidence = evidence_json_to_prose(evidence_json)
        report: dict[str, Any] = {
            "ok": False,
            "slug": slug,
            "plan_complete": False,
            "ac_verified": False,
            "gates_passed": False,
            "gates": [],
            "blocking_failures": [],
            "warnings": [],
            "cache_status": None,
            "message": "",
        }
        task = self._require_task(slug)  # type: ignore[attr-defined]
        # Verify-First: `tausik verify --task` uses DB relevant_files; `task done`
        # often omits CLI --relevant-files — merge so cache hash matches verify runs.
        if relevant_files is None:
            rf_raw = task.get("relevant_files")
            if rf_raw:
                try:
                    parsed = json.loads(rf_raw)
                    if isinstance(parsed, list):
                        relevant_files = parsed
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
        # v14-task-done-relevant-files-fallback: when both caller and DB row are
        # silent, recover the file set from the most recent fresh verify-row so
        # `tausik verify --task X` then `task done X` (no CLI args) hits cache.
        # Security-sensitive paths bypass the fallback — auth/payment/etc. always
        # require an explicit list to avoid stale-green leakage.
        if relevant_files is None:
            from verify_recent_lookup import lookup_relevant_files_from_recent_verify
            from service_verification import is_security_sensitive

            recovered = lookup_relevant_files_from_recent_verify(self.be._conn, slug)
            if recovered and not is_security_sensitive(recovered):
                relevant_files = recovered
        if task["status"] == "done":
            raise ServiceError(f"Task '{slug}' is already done")
        if evidence:
            self.task_log(slug, evidence)  # type: ignore[attr-defined]
            task = self._require_task(slug)  # type: ignore[attr-defined]
        try:
            ac_warnings = self._verify_ac(slug, task, ac_verified)  # type: ignore[attr-defined]
            report["ac_verified"] = True
        except ServiceError as e:
            report["blocking_failures"].append({"stage": "ac", "message": str(e)})
            return report
        try:
            self._verify_plan_complete(slug, task)  # type: ignore[attr-defined]
            report["plan_complete"] = True
        except ServiceError as e:
            report["blocking_failures"].append({"stage": "plan", "message": str(e)})
            return report
        gate_report = self._run_quality_gates_report(  # type: ignore[attr-defined]
            slug, relevant_files, progress_fn=progress_fn
        )
        report["gates"] = gate_report.get("results", [])
        report["cache_status"] = gate_report.get("cache_status")
        report["gates_passed"] = bool(gate_report.get("passed"))
        if not gate_report.get("passed"):
            failures = gate_report.get("blocking_failures", [])
            report["blocking_failures"] = [
                {
                    "stage": "gates",
                    "gate": f.get("gate"),
                    "files": f.get("files") or [],
                    "output": f.get("output"),
                    "remediation": f.get("remediation"),
                    "message": (
                        f"QG-2 Implementation Gate failed: {f.get('gate')} — "
                        f"{(f.get('output') or '')[:180]}"
                    ),
                }
                for f in failures
            ]
            return report

        checklist_warning = self._check_verification_checklist(slug, task)  # type: ignore[attr-defined]
        # SENAR Rule 5 (v15s-rule5-checklist-hardgate): a missing checklist is a
        # HARD block for substantial/deep planning tiers; lower tiers escalate
        # through the nudge framework (silent→hint→warning→strong) and reset on
        # compliance. Opt out of the hard block: config task_done.checklist_hard.
        checklist_nudge = ""
        from gate_ac_check import checklist_hard_block, checklist_missing

        _cl_block, _cl_msg = checklist_hard_block(task)
        if _cl_msg:
            if _checklist_hard_enabled():
                report["blocking_failures"].append(
                    {"stage": "checklist", "gate": "rule5-checklist", "message": _cl_msg}
                )
                return report
            checklist_nudge = f"WARNING (checklist_hard=false): {_cl_msg}"
        else:
            try:
                from nudge_escalation import escalate, reset

                if checklist_missing(task):
                    checklist_nudge = escalate(
                        self.be._conn,
                        "checklist",
                        "verification checklist missing in notes (SENAR Rule 5)",
                    )
                else:
                    reset(self.be._conn, "checklist")
            except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
                checklist_nudge = ""
        # SENAR Core Rule 7: defect tasks must document root cause.
        # v15-failclosed-gate-audit: hard gate by default — a defect closed
        # without its root cause is the exact fail-open the audit targets;
        # remediation is one `task log` line. FP escape (keyword phrasing
        # mismatch): config task_done.root_cause_hard=false.
        root_cause_warning = ""
        root_cause_nudge = ""
        if task.get("defect_of"):
            notes_raw = task.get("notes") or ""
            notes_lower = notes_raw.lower()
            # Rule-7 message text (template + closed-list categories, quoted
            # inline) lives in root_cause so it can't drift from the parser
            # (rule7-rootcause-nag-inline-template).
            _rc_kw = (
                "root cause",
                "причина",
                "cause:",
                "caused by",
                "из-за",
                "потому что",
                "because",
            )
            if not any(kw in notes_lower for kw in _rc_kw):
                from root_cause import missing_root_cause_message

                rc_msg = missing_root_cause_message(slug, task["defect_of"])
                if _root_cause_hard_enabled():
                    report["blocking_failures"].append({"stage": "root-cause", "message": rc_msg})
                    return report
                root_cause_warning = f"WARNING: {rc_msg}"
            else:
                # Keyword floor satisfied. Decision #96: nudge — never block —
                # toward the structured form (category + description +
                # prevention). Compliance resets the escalation counter.
                try:
                    from nudge_escalation import escalate, reset
                    from root_cause import (
                        has_structured_root_cause,
                        structured_nudge_message,
                    )

                    if has_structured_root_cause(notes_raw):
                        reset(self.be._conn, "root_cause")
                    else:
                        root_cause_nudge = escalate(
                            self.be._conn,
                            "root_cause",
                            structured_nudge_message(slug),
                        )
                except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
                    root_cause_nudge = ""

        # Knowledge capture warning (SENAR Rule 8).
        # v1.3.4 (med-batch-2-qg #5): --no-knowledge refused for complex
        # /defect tasks (SENAR Rule 8 upgrades from warning to refusal —
        # those are the cases where knowledge capture matters most).
        _kw = ("dead end", "decided", "decision", "memory", "pattern", "gotcha")
        notes = task.get("notes") or ""
        is_complex = (task.get("complexity") or "").lower() == "complex"
        is_defect = bool(task.get("defect_of"))
        if no_knowledge and (is_complex or is_defect):
            reason = "complex" if is_complex else "defect"
            report["blocking_failures"].append(
                {
                    "stage": "knowledge",
                    "message": (
                        f"--no-knowledge refused for {reason} task '{slug}'. "
                        f"SENAR Rule 8 requires knowledge capture. Either capture "
                        f"first (memory_add / decide / dead-end) and re-run without "
                        f"the flag, or downgrade complexity if truly trivial."
                    ),
                }
            )
            return report
        knowledge_warning = ""
        if not any(kw in notes.lower() for kw in _kw) and not no_knowledge:
            if (
                self.be.memory_count_for_task(slug) == 0
                and self.be.decision_count_for_task(slug) == 0
            ):
                knowledge_warning = "NOTE: No knowledge captured for this task (no memories, decisions, or dead ends). Use --no-knowledge to confirm none needed."
        if no_knowledge:
            self.be.event_add(
                "task",
                slug,
                "knowledge_confirmed_none",
                "Explicitly confirmed: no knowledge to capture",
            )
        # SENAR Rule 6 (v15s-rule6-rollback-plan): QG-0 blocks new
        # medium/complex tasks without a rollback_plan; here we only WARN so
        # tasks started before the field existed remain closable.
        rollback_warning = ""
        if (
            task.get("complexity") in ("medium", "complex")
            and not (task.get("rollback_plan") or "").strip()
        ):
            rollback_warning = (
                "WARNING: no rollback_plan (SENAR Rule 6). Document how to "
                "undo this change: task update --rollback-plan '...'"
            )
        updates: dict[str, Any] = {"status": "done", "completed_at": utcnow_iso()}
        if relevant_files:
            updates["relevant_files"] = json.dumps(relevant_files)
        # v15-risk-compute-on-done: closure risk score — best-effort, never
        # blocks the close. None (total collection failure) just skips the
        # columns; downstream (metrics, L3 trigger) treats NULL as "unknown".
        risk_note = ""
        try:
            from risk_compute import compute_task_risk

            risk = compute_task_risk(self.be._conn, task, relevant_files)
        except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
            risk = None
        if risk is not None:
            updates["risk_score"] = risk["score"]
            updates["risk_json"] = json.dumps(risk, ensure_ascii=False)
            report["risk"] = risk
            risk_note = f"Risk: {risk['score']} ({risk['level']})"
            if risk.get("defaulted"):
                risk_note += f" — unmeasured: {', '.join(risk['defaulted'])}"
            # v15-l3-risk-trigger: measured-high closures need an L3 review.
            from risk_l3_trigger import check_l3_required

            l3_block, l3_note = check_l3_required(self.be._conn, slug, risk)
            if l3_block:
                report["blocking_failures"].append(
                    {"stage": "risk", "gate": "l3-review", "message": l3_note}
                )
                return report
            if l3_note:
                risk_note += f" | {l3_note}"
        # Atomic: task update + cascade + audit in one transaction
        self.be.begin_tx()
        try:
            # v16r: pin done-model + flag mismatch (inside tx: lock-covered read).
            model_updates, model_mismatch_msg = model_done_updates(self.be, task)
            updates.update(model_updates)
            self.be.task_update(slug, **updates)
            msgs = [f"Task '{slug}' completed."]
            if risk_note:
                self.be.task_append_notes(slug, risk_note)
                msgs.append(risk_note)
            if model_mismatch_msg:
                self.be.task_append_notes(slug, model_mismatch_msg)
                msgs.append(model_mismatch_msg)
            msgs.extend(ac_warnings)
            if knowledge_warning:
                msgs.append(knowledge_warning)
                report["warnings"].append(knowledge_warning)
            if checklist_warning:
                msgs.append(checklist_warning)
                report["warnings"].append(checklist_warning)
            if checklist_nudge:
                msgs.append(checklist_nudge)
                report["warnings"].append(checklist_nudge)
            if root_cause_warning:
                msgs.append(root_cause_warning)
                report["warnings"].append(root_cause_warning)
            if root_cause_nudge:
                msgs.append(root_cause_nudge)
                report["warnings"].append(root_cause_nudge)
            if rollback_warning:
                msgs.append(rollback_warning)
                report["warnings"].append(rollback_warning)
            budget_warning = record_call_actual(self.be, slug, task)
            if budget_warning:
                msgs.append(budget_warning)
                report["warnings"].append(budget_warning)
            cost_warning = record_cost_actual(self.be, slug, task)
            if cost_warning:
                msgs.append(cost_warning)
                report["warnings"].append(cost_warning)
            msgs.extend(self._cascade_done(slug))  # type: ignore[attr-defined]
            self.be.commit_tx()
        except Exception:
            self.be.rollback_tx()
            raise
        report["ok"] = True
        report["message"] = " ".join(msgs)
        return report
