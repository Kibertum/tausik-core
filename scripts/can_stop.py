"""Deterministic Stop policy bound to a trusted host turn and execution lease."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from service_ac_evidence import build_report
from service_execution_lease import normalize_project_identity
from tausik_utils import utcnow_iso

DECISIONS = frozenset(
    {
        "CONTINUE",
        "ALLOW_HANDOFF",
        "ALLOW_READ_ONLY",
        "ALLOW_DONE",
        "ALLOW_BLOCKED",
        "ADVISORY_UNTRUSTED",
    }
)


@dataclass(frozen=True)
class StopState:
    trusted: bool
    request_kind: str
    task_status: str | None
    next_action: str | None
    handoff_ready: bool = False
    blocker_verified: bool = False


@dataclass(frozen=True)
class StopDecision:
    code: str
    action: str


@dataclass(frozen=True)
class NativeStopVerdict:
    enforced: bool
    reason: str


def classify_native_stop_verdict(
    *, stdout: str, returncode: int | None, timed_out: bool = False
) -> NativeStopVerdict:
    """Count hard enforcement only when the host observed native block JSON."""
    if timed_out:
        return NativeStopVerdict(False, "host timeout produced no blocking verdict")
    if returncode != 0:
        return NativeStopVerdict(False, f"hook process exited {returncode}")
    try:
        payload = json.loads(stdout)
    except (TypeError, json.JSONDecodeError):
        return NativeStopVerdict(False, "hook stdout is missing or malformed")
    if isinstance(payload, dict) and payload.get("decision") == "block":
        reason = payload.get("reason")
        if isinstance(reason, str) and reason.strip():
            return NativeStopVerdict(True, reason.strip())
    return NativeStopVerdict(False, "host did not receive a native blocking verdict")


def run_native_stop_probe(
    command: list[str],
    *,
    payload: Mapping[str, object] | str = "",
    timeout: float = 5.0,
    env: Mapping[str, str] | None = None,
) -> NativeStopVerdict:
    """Run a native Stop process and classify only host-observable evidence."""
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    try:
        result = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=dict(env) if env is not None else None,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return classify_native_stop_verdict(stdout="", returncode=None, timed_out=True)
    except OSError as exc:
        return NativeStopVerdict(False, f"hook process failed to start: {type(exc).__name__}")
    return classify_native_stop_verdict(stdout=result.stdout, returncode=result.returncode)


def classify_request(prompt: str) -> str:
    """Classify only the host-supplied user prompt; answer prose is never input."""
    text = prompt.strip().lower()
    if not text:
        return "work"
    # This is a closed grammar, not an allowed prefix plus arbitrary prose.
    # Unknown objects, predicates, punctuation and suffixes remain governed work.
    read_only_forms = (
        r"status(?: of (?:this|the) (?:task|project|release))?",
        r"show (?:me )?(?:the )?status(?: of (?:this|the) (?:task|project|release))?",
        r"what is (?:the )?status(?: of (?:this|the) (?:task|project|release))?",
        r"(?:explain|describe|review|summarize) (?:this|that|it|the (?:task|project|change|code|plan|error|result|release))",
        r"explain (?:how (?:this|that|it) works|why (?:this|that|it) (?:fails|works))",
        r"покажи статус(?: (?:задачи|проекта|релиза))?",
        r"(?:объясни|проверь|суммируй) (?:это|задачу|проект|изменение|код|план|ошибку|результат|релиз)",
    )
    if any(re.fullmatch(form + r"[?.]?", text) for form in read_only_forms):
        return "read_only"
    return "work"


def can_stop(state: StopState) -> StopDecision:
    """Pure policy table. The caller proves every boolean from durable state."""
    if not state.trusted:
        return StopDecision("ADVISORY_UNTRUSTED", "host cannot enforce Stop")
    if state.request_kind == "read_only":
        return StopDecision("ALLOW_READ_ONLY", "read-only request answered")
    if state.task_status == "done":
        return StopDecision("ALLOW_DONE", "task is complete")
    if state.blocker_verified:
        return StopDecision("ALLOW_BLOCKED", state.next_action or "resume the blocked task")
    if state.handoff_ready:
        return StopDecision("ALLOW_HANDOFF", state.next_action or "resume in a fresh thread")
    return StopDecision("CONTINUE", state.next_action or "complete the active task")


def _payload_hash(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_trusted_turn(
    svc: Any,
    *,
    project_dir: str,
    host_instance: str,
    thread_id: str,
    turn_id: str | None,
    prompt: str,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Bind the current host turn to the one live lease and active task."""
    lease = svc.be._execution_lease_current(
        normalize_project_identity(project_dir), host_instance.casefold(), thread_id
    )
    if lease is None or lease.get("revoked_at") is not None:
        raise ValueError("TURN_LEASE_MISSING: trusted turn has no live execution lease")
    kind = classify_request(prompt)
    now = utcnow_iso()
    with svc.be.transaction():
        if not turn_id:
            sequence = svc.be._q1("SELECT COALESCE(MAX(id),0)+1 AS value FROM can_stop_turns")[
                "value"
            ]
            turn_id = f"{host_instance.casefold()}:{thread_id}:{sequence}"
        svc.be._ex(
            "UPDATE can_stop_turns SET consumed_at=COALESCE(consumed_at,?),decision=COALESCE(decision,'superseded') "
            "WHERE host_instance=? AND thread_id=? AND consumed_at IS NULL",
            (now, host_instance.casefold(), thread_id),
        )
        svc.be._ex(
            "INSERT INTO can_stop_turns(project_identity,host_instance,thread_id,turn_id,lease_id,task_slug,request_kind,payload_hash,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                normalize_project_identity(project_dir),
                host_instance.casefold(),
                thread_id,
                turn_id,
                int(lease["id"]),
                lease.get("task_slug"),
                kind,
                _payload_hash(payload),
                now,
            ),
        )
    return {"turn_id": turn_id, "request_kind": kind, "lease_id": int(lease["id"])}


def _next_action(
    task: Mapping[str, Any] | None, continuity: Mapping[str, Any] | None = None
) -> str | None:
    if not task:
        return "create and start a TAUSIK task for this work"
    pending = str((continuity or {}).get("pending_requirement") or "").strip()
    if pending:
        recoveries = (
            "reason-step, then block or decompose"
            if pending == "call_budget_exhausted"
            else "reason-step, then checkpoint, block, or decompose"
        )
        return f"resolve continuity requirement {pending}: {recoveries}"
    try:
        plan = json.loads(task.get("plan") or "[]")
    except (TypeError, ValueError):
        plan = []
    for index, item in enumerate(plan, 1):
        if isinstance(item, dict) and not item.get("done"):
            return f"complete plan step {index}: {str(item.get('step') or '').strip()}"
    report = build_report(str(task.get("acceptance_criteria") or ""), str(task.get("notes") or ""))
    for item in report.items:
        if not item.has_any_evidence:
            return f"verify acceptance criterion {item.ac_index}: {item.ac_text}"
    return f"verify and close task {task.get('slug')} with QG-2 evidence"


def _verified_blocker_action(
    svc: Any,
    turn: Mapping[str, Any],
    continuity: Mapping[str, Any],
    current_slug: str,
) -> str | None:
    raw = continuity.get("blocker_json")
    if not raw:
        return None
    try:
        blocker = json.loads(raw)
        event_ids = blocker["attempt_event_ids"]
        preflight_id = int(blocker["memory_preflight_id"])
        resume = str(blocker["resume_action"]).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if not resume or not isinstance(event_ids, list) or not event_ids:
        return None
    placeholders = ",".join("?" for _ in event_ids)
    rows = svc.be._q(
        f"SELECT id FROM task_attempt_events WHERE id IN ({placeholders}) "
        "AND task_slug=? AND lease_id=? AND event_kind IN ('capability','authority') "
        "AND status IN ('unavailable','verified')",
        (*event_ids, current_slug, int(turn["lease_id"])),
    )
    token = svc.be._q1(
        "SELECT id FROM memory_preflight_tokens WHERE id=? AND lease_id=? AND protected_kind='blocker' AND status='executed'",
        (preflight_id, int(turn["lease_id"])),
    )
    if len(rows) == len(set(event_ids)) and token is not None:
        return resume
    return None


def record_attempt_event(
    svc: Any,
    *,
    lease: Mapping[str, Any],
    event_kind: str,
    status: str,
    detail: Mapping[str, object],
) -> int:
    """Persist one observed failure against the exact current task lease."""
    slug = lease.get("task_slug")
    if not isinstance(slug, str) or not slug:
        raise ValueError("ATTEMPT_TASK_MISSING: lease is not bound to a task")
    live = svc.be._q1("SELECT * FROM execution_leases WHERE id=?", (int(lease["id"]),))
    if (
        live is None
        or live.get("revoked_at") is not None
        or live.get("task_slug") != slug
        or event_kind not in {"attempt", "capability", "authority"}
        or status not in {"failed", "unavailable", "verified"}
    ):
        raise ValueError("ATTEMPT_EVIDENCE_INVALID: event is not bound to the live task lease")
    return int(
        svc.be._ins(
            "INSERT INTO task_attempt_events(task_slug,lease_id,event_kind,status,detail_json,created_at) "
            "VALUES(?,?,?,?,?,?)",
            (
                slug,
                int(lease["id"]),
                event_kind,
                status,
                json.dumps(dict(detail), sort_keys=True),
                utcnow_iso(),
            ),
        )
    )


def persist_structured_blocker(
    svc: Any,
    *,
    lease: Mapping[str, Any],
    attempt_event_ids: list[int],
    resume_action: str,
) -> dict[str, int]:
    """Bind already-observed unavailable events to the reserved blocker action."""
    resume = resume_action.strip()
    event_ids = [int(value) for value in attempt_event_ids]
    if not resume or not event_ids or len(event_ids) != len(set(event_ids)):
        raise ValueError(
            "BLOCKER_EVIDENCE_INVALID: observed event IDs and resume_action are required"
        )
    tokens = svc.be._q(
        "SELECT id,package_fingerprint FROM memory_preflight_tokens "
        "WHERE lease_id=? AND protected_kind='blocker' AND status='reserved' "
        "ORDER BY id DESC LIMIT 2",
        (int(lease["id"]),),
    )
    if len(tokens) != 1:
        raise ValueError(
            "BLOCKER_PREFLIGHT_INVALID: exactly one reserved blocker preflight is required"
        )
    placeholders = ",".join("?" for _ in event_ids)
    observed = svc.be._q(
        f"SELECT id FROM task_attempt_events WHERE id IN ({placeholders}) "
        "AND task_slug=? AND lease_id=? AND event_kind IN ('capability','authority') "
        "AND status IN ('unavailable','verified')",
        (*event_ids, lease["task_slug"], int(lease["id"])),
    )
    if len(observed) != len(event_ids):
        raise ValueError("BLOCKER_EVIDENCE_INVALID: event was not observed on this task lease")
    token = tokens[0]
    blocker = json.dumps(
        {
            "attempt_event_ids": event_ids,
            "memory_preflight_id": int(token["id"]),
            "resume_action": resume,
        },
        sort_keys=True,
    )
    now = utcnow_iso()
    svc.be._ex(
        "INSERT INTO task_continuity_state(task_slug,package_fingerprint,blocker_json,updated_at) "
        "VALUES(?,?,?,?) ON CONFLICT(task_slug) DO UPDATE SET "
        "package_fingerprint=excluded.package_fingerprint,blocker_json=excluded.blocker_json,"
        "updated_at=excluded.updated_at",
        (lease["task_slug"], token["package_fingerprint"], blocker, now),
    )
    return {"attempt_event_id": event_ids[0], "memory_preflight_id": int(token["id"])}


def decide_persisted_stop(
    svc: Any, *, host_instance: str, thread_id: str, turn_id: str | None = None
) -> StopDecision:
    """Consume exactly this turn once and derive policy only from durable state."""
    with svc.be.transaction():
        if turn_id:
            turn = svc.be._q1(
                "SELECT * FROM can_stop_turns WHERE host_instance=? AND thread_id=? AND turn_id=?",
                (host_instance.casefold(), thread_id, turn_id),
            )
            latest = svc.be._q1(
                "SELECT id FROM can_stop_turns WHERE host_instance=? AND thread_id=? "
                "ORDER BY id DESC LIMIT 1",
                (host_instance.casefold(), thread_id),
            )
            if turn is not None and (latest is None or int(turn["id"]) != int(latest["id"])):
                turn = None
        else:
            turn = None
        if turn is None:
            return StopDecision("CONTINUE", "trusted turn record is missing; continue safely")
        retrying_continue = turn.get("consumed_at") is not None
        if retrying_continue:
            code = str(turn.get("decision") or "CONTINUE")
            if code != "CONTINUE":
                return StopDecision(code if code in DECISIONS else "CONTINUE", "duplicate Stop")
        lease = svc.be._q1("SELECT * FROM execution_leases WHERE id=?", (turn["lease_id"],))
        current_slug = lease.get("task_slug") if lease else None
        task = svc.be.task_get(current_slug) if current_slug else None
        if task is None and not current_slug:
            closed_slug = turn.get("task_slug")
            closed_task = svc.be.task_get(closed_slug) if closed_slug else None
            if closed_task and closed_task.get("status") == "done":
                current_slug = str(closed_slug)
                task = closed_task
        continuity = (
            svc.be._q1("SELECT * FROM task_continuity_state WHERE task_slug=?", (current_slug,))
            if current_slug
            else {}
        ) or {}
        session = svc.be._q1(
            "SELECT handoff FROM sessions WHERE id=(SELECT session_id FROM execution_leases WHERE id=?)",
            (turn["lease_id"],),
        )
        resume_command = f".tausik/tausik task start {current_slug} --package"
        budget_exhausted = bool(
            task
            and task.get("call_budget") is not None
            and int(task.get("call_actual") or 0) >= int(task["call_budget"])
        )
        hard_context_checkpoint = bool(
            lease and svc.be.meta_get(f"host_context_hard_lease:{lease['id']}") == resume_command
        )
        handoff_ready = bool(
            lease
            and lease.get("revoked_at")
            and session
            and resume_command in str(session.get("handoff") or "")
            and (
                hard_context_checkpoint
                or (
                    budget_exhausted
                    and continuity.get("recovery_consumed_at")
                    and continuity.get("recovery_action") == "checkpoint"
                )
            )
        )
        blocker_action = (
            _verified_blocker_action(svc, turn, continuity, current_slug)
            if task and task.get("status") == "blocked" and isinstance(current_slug, str)
            else None
        )
        next_action = (
            resume_command
            if handoff_ready
            else blocker_action
            if blocker_action
            else _next_action(task, continuity)
        )
        decision = can_stop(
            StopState(
                trusted=True,
                request_kind=str(turn["request_kind"]),
                task_status=str(task.get("status")) if task else None,
                next_action=next_action,
                handoff_ready=handoff_ready,
                blocker_verified=bool(blocker_action),
            )
        )
        now = utcnow_iso()
        if retrying_continue:
            return decision
        changed = svc.be._ex(
            "UPDATE can_stop_turns SET consumed_at=?,decision=? WHERE id=? AND consumed_at IS NULL",
            (now, decision.code, turn["id"]),
        )
        if changed != 1:
            return StopDecision("CONTINUE", "concurrent Stop already consumed this turn")
        return decision


def decision_json(decision: StopDecision) -> dict[str, str]:
    return asdict(decision)
