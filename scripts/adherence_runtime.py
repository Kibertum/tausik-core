"""Action recording, boundary probes and threshold evaluation."""

from __future__ import annotations

import contextvars
import copy
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Final, Mapping, Sequence, cast

from adherence_policy import (
    EVENT_FIELDS,
    EVENT_SCHEMA_VERSION,
    POLICY_VERSION,
    RATE_METRICS,
    RESULTS,
    ZERO_COUNT_METRICS,
    ContractError,
    Verdict,
    _OPAQUE_ID,
    _canonical_bytes,
    artifact_hash,
)
from adherence_registry import _hook_route, _route_by_name

_ACTIVE_RECORDER: contextvars.ContextVar[object | None] = contextvars.ContextVar(
    "tausik_adherence_recorder", default=None
)
_EVENT_SINK_ENV: Final[str] = "TAUSIK_ADHERENCE_EVENT_SINK"


def active_recorder() -> AdherenceRecorder | None:
    """Return the recorder installed by a boundary probe, if instrumentation uses it."""

    return cast(AdherenceRecorder | None, _ACTIVE_RECORDER.get())


def append_sink_events(events: Sequence[Mapping[str, object]]) -> None:
    """Append validated hook events to the cross-process probe sink."""

    sink = os.environ.get(_EVENT_SINK_ENV)
    if not sink:
        raise ContractError("cross-process adherence event sink is not configured")
    checked = _validated_events(events)
    with Path(sink).open("a", encoding="utf-8", newline="\n") as handle:
        for event in checked:
            handle.write(_canonical_bytes(event).decode("utf-8") + "\n")


class AdherenceRecorder:
    """Canonical event producer used by TAUSIK entry points and fixtures."""

    def __init__(self, task_slug: str, thread_id: str) -> None:
        if not task_slug or not thread_id:
            raise ContractError("task_slug and thread_id are required")
        self.task_id = _opaque("task", task_slug)
        self.thread_id = _opaque("thread", thread_id)
        self.events: list[dict[str, object]] = []
        self.probes: list[dict[str, object]] = []

    def record_action(
        self,
        route: str,
        results: Mapping[str, str],
    ) -> list[dict[str, object]]:
        """Record one route occurrence with one immutable action identity."""

        route_contract = _route_by_name().get(route)
        if route_contract is None:
            raise ContractError(f"route is not registered: {route}")
        required = cast(list[str], route_contract["required_events"])
        optional = cast(list[str], route_contract["optional_events"])
        if not required:
            raise ContractError(f"read route has no adherence obligations: {route}")
        supplied = set(results)
        allowed = set(required) | set(optional)
        unknown = supplied - allowed
        if unknown:
            raise ContractError(f"route {route} does not require events: {sorted(unknown)}")
        if not set(required).issubset(supplied):
            raise ContractError(
                f"route {route} requires events {required}; supplied {sorted(supplied)}"
            )

        action_index = len({event["action_id"] for event in self.events}) + 1
        action_id = _opaque("action", f"{route}:{action_index}")
        lease_id = _opaque("lease", f"{route}:{action_index}")
        package_id = _opaque("package", f"{route}:{action_index}")
        recorded: list[dict[str, object]] = []
        selected = required + [kind for kind in optional if kind in supplied]
        for kind in selected:
            result = results.get(kind, _missing_result(kind))
            if result not in RESULTS[kind]:
                raise ContractError(f"result {result!r} is not valid for {kind}")
            sequence = len(self.events) + 1
            event: dict[str, object] = {
                "action_id": action_id,
                "boundary": route_contract["boundary"],
                "event_id": _opaque("event", f"{action_id}:{kind}:{sequence}"),
                "kind": kind,
                "lease_id": lease_id,
                "package_fingerprint": package_id,
                "policy_version": POLICY_VERSION,
                "result": result,
                "route": route,
                "schema_version": EVENT_SCHEMA_VERSION,
                "sequence": sequence,
                "task_id": self.task_id,
                "thread_id": self.thread_id,
            }
            self.events.append(event)
            recorded.append(copy.deepcopy(event))
        return recorded

    def record_red_action(
        self,
        route: str,
        optional_failures: Mapping[str, str] | None = None,
    ) -> list[dict[str, object]]:
        """Build an arithmetic-only red action; never use as runtime evidence."""

        route_contract = _route_by_name().get(route)
        if route_contract is None:
            raise ContractError(f"route is not registered: {route}")
        required = cast(list[str], route_contract["required_events"])
        results = {kind: _missing_result(kind) for kind in required}
        results.update(optional_failures or {})
        return self.record_action(route, results)

    def _probe(
        self,
        route: str,
        invoke: object,
        *,
        expected_returncodes: frozenset[int] = frozenset({0}),
    ) -> object:
        if not callable(invoke):
            raise ContractError("integration probe must be callable")
        before = len(self.events)
        token = _ACTIVE_RECORDER.set(self)
        try:
            outcome = invoke()
        finally:
            _ACTIVE_RECORDER.reset(token)
        if getattr(outcome, "returncode", 0) not in expected_returncodes:
            raise ContractError(f"integration probe failed for {route}")
        if isinstance(outcome, Mapping) and (outcome.get("error") or outcome.get("isError")):
            raise ContractError(f"integration probe returned an error for {route}")
        if route not in _route_by_name():
            raise ContractError(f"route is not registered: {route}")
        emitted = self.events[before:]
        emitted_actions = {str(event["action_id"]) for event in emitted}
        if len(emitted_actions) > 1:
            raise ContractError(f"integration probe emitted multiple actions for {route}")
        action_id = (
            next(iter(emitted_actions))
            if emitted_actions
            else _opaque("action", f"probe:{route}:{len(self.probes) + 1}")
        )
        self.probes.append(
            {
                "action_id": action_id,
                "event_count": len(emitted),
                "event_sha256": artifact_hash(emitted),
                "route": route,
                "status": "executed",
            }
        )
        return outcome

    def probe_service(self, method: object, /, *args: object, **kwargs: object) -> object:
        """Invoke a bound ProjectService method and derive its canonical route."""

        owner = getattr(method, "__self__", None)
        name = getattr(method, "__name__", "")
        if owner is None or owner.__class__.__name__ != "ProjectService" or not name:
            raise ContractError("service probe requires a bound ProjectService method")
        call = cast(Callable[..., object], method)
        return self._probe(f"service.{name}", lambda: call(*args, **kwargs))

    def probe_cli(self, dispatcher: object, service: object, args: object) -> object:
        """Invoke a CLI dispatcher and derive the leaf route from its parsed args."""

        name = getattr(dispatcher, "__name__", "")
        if not name.startswith("cmd_"):
            raise ContractError("CLI probe requires a cmd_* dispatcher")
        group = name.removeprefix("cmd_")
        command = getattr(args, f"{group}_cmd", "")
        if not isinstance(command, str) or not command:
            raise ContractError("CLI probe requires parsed leaf-command args")
        call = cast(Callable[..., object], dispatcher)
        return self._probe(f"cli.{group}.{command}", lambda: call(service, args))

    def probe_mcp(
        self,
        dispatcher: object,
        service: object,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> object:
        """Invoke the MCP dispatcher using the tool name as canonical provenance."""

        if getattr(dispatcher, "__name__", "") != "_dispatch_tool":
            raise ContractError("MCP probe requires the canonical _dispatch_tool")
        call = cast(Callable[..., object], dispatcher)
        return self._probe(f"mcp.{tool_name}", lambda: call(service, tool_name, dict(arguments)))

    def probe_hook(
        self,
        event: str,
        script: str | os.PathLike[str],
        payload: Mapping[str, object],
        env: Mapping[str, str],
        *,
        expected_returncodes: frozenset[int],
    ) -> subprocess.CompletedProcess[str]:
        """Invoke a hook subprocess and derive its route from event plus script path."""

        script_path = Path(script)
        bootstrap_hooks = importlib.import_module("bootstrap_hooks")
        hooks = bootstrap_hooks.build_hooks_dict(lambda name, suffix="": f"{name}{suffix}")
        tool_name = str(payload.get("tool_name", ""))
        routes: list[str] = []
        for entry in hooks.get(event, []):
            matcher = str(entry.get("matcher", ""))
            matches_tool = not matcher or tool_name in matcher.split("|")
            commands = [str(hook.get("command", "")) for hook in entry.get("hooks", [])]
            if matches_tool:
                routes.extend(
                    _hook_route(event, matcher, command)
                    for command in commands
                    if script_path.name in command
                )
        if len(routes) != 1:
            raise ContractError("hook probe could not derive one canonical route")

        return self._probe_hook_process(
            routes[0], script_path, payload, env, expected_returncodes=expected_returncodes
        )

    def _probe_hook_process(
        self,
        route: str,
        script: str | os.PathLike[str],
        payload: Mapping[str, object],
        env: Mapping[str, str],
        *,
        expected_returncodes: frozenset[int],
    ) -> subprocess.CompletedProcess[str]:
        """Run one hook with a JSONL sink that crosses the subprocess boundary."""

        with tempfile.TemporaryDirectory(prefix="tausik-adherence-") as temp_dir:
            sink = Path(temp_dir) / "events.jsonl"
            child_env = dict(env, **{_EVENT_SINK_ENV: str(sink)})

            def invoke() -> subprocess.CompletedProcess[str]:
                completed = subprocess.run(
                    [sys.executable, str(script)],
                    input=json.dumps(dict(payload)),
                    text=True,
                    capture_output=True,
                    env=child_env,
                    check=False,
                )
                if completed.returncode not in expected_returncodes:
                    raise ContractError(f"hook probe returned {completed.returncode}: {route}")
                if sink.exists():
                    child_events = [
                        json.loads(line)
                        for line in sink.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                    for event in _validated_events(child_events):
                        event["sequence"] = len(self.events) + 1
                        self.events.append(event)
                return completed

            outcome = self._probe(route, invoke, expected_returncodes=expected_returncodes)
            return cast(subprocess.CompletedProcess[str], outcome)


def _opaque(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _missing_result(kind: str) -> str:
    return {
        "continuity": "missing",
        "dead_end_repeat": "unoverridden",
        "execution_lease": "missing",
        "handoff_resume": "incorrect",
        "memory_preflight": "missing",
        "stop_decision": "premature",
        "task_package": "missing",
    }[kind]


def _validated_events(
    events: Sequence[Mapping[str, object]],
    expected_actions: frozenset[str] | None = None,
) -> list[dict[str, object]]:
    validated: list[dict[str, object]] = []
    event_ids: set[str] = set()
    routes = _route_by_name()
    for expected_sequence, raw in enumerate(events, start=1):
        if set(raw) != EVENT_FIELDS:
            extra = sorted(set(raw) - EVENT_FIELDS)
            missing = sorted(EVENT_FIELDS - set(raw))
            raise ContractError(
                f"event fields differ from allowlist: extra={extra}, missing={missing}"
            )
        event = dict(raw)
        if type(event["schema_version"]) is not int or type(event["policy_version"]) is not int:
            raise ContractError("schema_version and policy_version must be exact integers")
        if (
            event["schema_version"] != EVENT_SCHEMA_VERSION
            or event["policy_version"] != POLICY_VERSION
        ):
            raise ContractError("event schema or policy version mismatch")
        if type(event["sequence"]) is not int or event["sequence"] != expected_sequence:
            raise ContractError("event sequence is missing or reordered")
        event_id = event["event_id"]
        if not isinstance(event_id, str) or not event_id or event_id in event_ids:
            raise ContractError("event_id is missing or duplicated")
        event_ids.add(event_id)

        kind = event["kind"]
        result = event["result"]
        route = event["route"]
        if not isinstance(kind, str) or kind not in RESULTS:
            raise ContractError(f"unknown event kind: {kind}")
        if not isinstance(result, str) or result not in RESULTS[kind]:
            raise ContractError(f"unknown result {result!r} for {kind}")
        route_contract = routes.get(str(route))
        if route_contract is None:
            raise ContractError(f"route {route!r} is not registered for {kind}")
        required_events = cast(list[str], route_contract["required_events"])
        optional_events = cast(list[str], route_contract["optional_events"])
        if kind not in required_events + optional_events:
            raise ContractError(f"route {route!r} is not registered for {kind}")
        if event["boundary"] != route_contract["boundary"]:
            raise ContractError("event boundary does not match its registered route")
        for identity_field in (
            "action_id",
            "event_id",
            "lease_id",
            "package_fingerprint",
            "task_id",
            "thread_id",
        ):
            value = event[identity_field]
            if not isinstance(value, str) or not _OPAQUE_ID.fullmatch(value):
                raise ContractError(f"{identity_field} must be an opaque bounded identifier")
        validated.append(event)

    actions: dict[str, list[dict[str, object]]] = {}
    for event in validated:
        actions.setdefault(str(event["action_id"]), []).append(event)
    if expected_actions is not None and frozenset(actions) != expected_actions:
        raise ContractError("event actions do not match the trusted invocation census")
    for action_id, action_events in actions.items():
        first = action_events[0]
        for field in (
            "boundary",
            "lease_id",
            "package_fingerprint",
            "route",
            "task_id",
            "thread_id",
        ):
            if any(event[field] != first[field] for event in action_events[1:]):
                raise ContractError(f"action {action_id} has inconsistent {field}")
        required = cast(list[str], routes[str(first["route"])]["required_events"])
        optional = cast(list[str], routes[str(first["route"])]["optional_events"])
        kinds = [str(event["kind"]) for event in action_events]
        expected = required + [kind for kind in optional if kind in kinds]
        if kinds != expected or len(kinds) != len(set(kinds)):
            raise ContractError(
                f"action {action_id} requires ordered events {required}; observed {kinds}"
            )
    return validated


def evaluate(
    events: Sequence[Mapping[str, object]],
    *,
    expected_actions: frozenset[str] | None = None,
) -> Verdict:
    """Evaluate one ordered event stream against every immutable threshold."""

    checked = _validated_events(events, expected_actions)
    metrics: dict[str, dict[str, object]] = {}
    for name, (kind, passing_result) in RATE_METRICS.items():
        relevant = [event for event in checked if event["kind"] == kind]
        numerator = sum(event["result"] == passing_result for event in relevant)
        denominator = len(relevant)
        metrics[name] = {
            "denominator": denominator,
            "numerator": numerator,
            "passed": denominator > 0 and numerator == denominator,
            "threshold": "100%",
        }
    for name, (kind, failing_result) in ZERO_COUNT_METRICS.items():
        relevant = [event for event in checked if event["kind"] == kind]
        count = sum(event["result"] == failing_result for event in relevant)
        metrics[name] = {
            "count": count,
            "denominator": len(relevant),
            "passed": count == 0,
            "threshold": 0,
        }
    return Verdict(
        accepted=all(bool(metric["passed"]) for metric in metrics.values()), metrics=metrics
    )
