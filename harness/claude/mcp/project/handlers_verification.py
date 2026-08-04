"""MCP handlers for the verification domain — doctor, verify, gate toggles.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.

Health-check, gate run and gate configuration sit together because they are the
one surface an agent uses to answer "is this green, and what was actually
allowed to run" — the question these handlers have historically answered
misleadingly, hence the density of comments below.
"""

from __future__ import annotations

from typing import Any


def _handle_doctor(svc: Any) -> str:
    import io as _io
    import sys as _sys

    from project_cli_doctor import _capture_db_state, cmd_doctor

    _capture_db_state()
    buf = _io.StringIO()
    saved_out, saved_err = _sys.stdout, _sys.stderr
    _sys.stdout = _sys.stderr = buf

    class _Ns:
        pass

    try:
        cmd_doctor(svc, _Ns())
    except SystemExit:
        pass
    finally:
        _sys.stdout, _sys.stderr = saved_out, saved_err
    return buf.getvalue()


def _handle_verify(
    svc: Any,
    task_slug: str | None,
    *,
    scope: str = "standard",
    trigger: str = "verify",
) -> str:
    """v1.4 Verify-First Contract — delegate to public service method.

    Layering rule: handlers call the service; the service owns the SQLite
    connection. Behavior parity with the CLI:
      - task_slug optional (full-suite when omitted)
      - scope/trigger optional with sensible defaults
    """
    from tausik_utils import ServiceError

    try:
        result = svc.run_verify_for_task(task_slug=task_slug, scope=scope, trigger=trigger)
    except ServiceError as e:
        return f"Error: {e}"
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"
    from gate_runner import format_results

    results = result.get("results", [])
    lines = [
        f"verify task='{task_slug or '-'}' "
        f"passed={result['passed']} "
        f"status={result['status']} "
        f"trigger={result['trigger']}",
        format_results(results),
    ]

    # A skipped gate used to be indistinguishable from a passed one here: this
    # returned `gates=['hadolint', 'pytest']`, a list of NAMES, so an agent read
    # "pytest" and concluded the tests had run. On a task with no declared
    # scope, pytest is skipped and the only thing that actually executed was a
    # Dockerfile linter — and the run was still recorded green and signed. The
    # same confusion is what `gate_verdict` was extracted to end; this handler
    # was the copy that extraction did not reach, and it is the copy the agent
    # reads, because CLAUDE.md tells it to prefer MCP over the CLI.
    if any(r.get("skipped") for r in results):
        skipped = ", ".join(r.get("name", "?") for r in results if r.get("skipped"))
        lines.append(
            f"NOTE: {skipped} did NOT execute. A SKIP is not a verification — "
            f"this run says nothing about what those gates cover."
        )
    # The "declare relevant_files" scolding only makes sense for a SCOPED run.
    # In full-suite mode (task_slug omitted — documented CLI parity) the service
    # returns files=[] by design, not because a task under-declared, so the old
    # unconditional NOTE fired the widest verification the tool offers with an
    # unactionable "`tausik task update <slug>`" that names no real task.
    if task_slug and not result.get("relevant_files"):
        lines.append(
            f"NOTE: no relevant_files declared for '{task_slug}', so every scoped "
            f"gate skipped. Declare them (`tausik task update {task_slug} "
            "--relevant-files <paths>`) and re-run, or this green rests on nothing."
        )
    elif task_slug is None:
        lines.append(
            "NOTE: full-suite run (no task scope). Not recorded to the verify "
            "cache — pass a task_slug to cache a scoped green for task_done."
        )
    lines.extend(_handle_lines(result, task_slug))
    return "\n".join(lines)


def _handle_lines(result: dict, task_slug: str | None) -> list[str]:
    """The explicit state handle, surfaced to the AGENT (SEP-2567).

    This handler used to return neither run_id nor receipt — the MCP caller got
    strictly less than the CLI caller, which is part of why the only link
    between a verify and a close was a server-side search. Returning the handle
    is what makes `verify_handle` presentable from MCP at all; without these
    lines the argument added to the tausik_task_done schema would have nothing
    to carry.

    The durability policy travels WITH the handle rather than living only in
    the tool description: the description is read once at connect time, this
    line is read at the moment the decision is made.
    """
    if not task_slug:
        return []
    handle = result.get("verify_handle")
    if not handle:
        return [
            "HANDLE: none — this run is not presentable (no declared files, all "
            "gates skipped, or a security-sensitive scope). tausik_task_done "
            "will fall back to the freshness lookup."
        ]
    return [
        f"HANDLE: {handle} (valid until {result.get('handle_expires_at')}, single use).",
        f"  Pass it to tausik_task_done as verify_handle when closing '{task_slug}'.",
    ]


def _handle_gates_status(svc: Any = None) -> str:
    """Gates status via project_config (no DB needed).

    mcp-config-read-paths-ignore-project-handle: read the gates of the project
    THIS service speaks for. Resolving from the cwd instead described whichever
    project the MCP process stood in — invisible today (server cwd = project
    root), a wrong answer the moment `svc` carries project identity (epic
    v2-global-mcp). `svc is None` keeps the ambient-project fallback so nothing
    that calls this without a service changes.
    """
    try:
        from project_config import load_config, load_gates

        td = svc.tausik_dir() if svc is not None and hasattr(svc, "tausik_dir") else None
        gates = load_gates(tausik_dir=td)
        cfg = load_config(td)
        stacks = cfg.get("bootstrap", {}).get("stacks", [])
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error loading gates: {e}"
    lines = []
    for name, gate in sorted(gates.items()):
        status = "ON" if gate.get("enabled", True) else "OFF"
        sev = gate.get("severity", "warn")
        gate_stacks = gate.get("stacks", [])
        stack_info = f" [{','.join(gate_stacks)}]" if gate_stacks else ""
        lines.append(f"[{status}] {name} ({sev}){stack_info}: {gate.get('description', '')}")
    if stacks:
        lines.append(f"\nDetected stacks: {', '.join(stacks)}")
    return "\n".join(lines) if lines else "No gates configured."


def _handle_gate_toggle(svc, name: str, enable: bool) -> str:
    """Delegate to the service; hold no toggle logic of its own.

    This used to be a second implementation of `project_config.set_gate_enabled`,
    and the copy had drifted in all three ways a copy drifts: it round-tripped
    the EFFECTIVE config back into the project file (copying user- and
    operator-tier settings into the repository), it reported success regardless
    of what the trust policy actually applied, and — because it took `svc` and
    dropped it — it resolved the config from the cwd, so a call declared
    project-scoped wrote into whatever project the process stood in. Delegation
    is the fix for all three at once: there is one formula again.
    """
    try:
        return svc.gate_enable(name) if enable else svc.gate_disable(name)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


VERIFICATION_HANDLERS = {
    "tausik_doctor": lambda svc, args: _handle_doctor(svc),
    "tausik_verify": lambda svc, args: _handle_verify(
        svc,
        args.get("task_slug"),
        scope=args.get("scope", "standard"),
        trigger=args.get("trigger", "verify"),
    ),
    "tausik_gates_status": lambda svc, args: _handle_gates_status(svc),
    "tausik_gates_enable": lambda svc, args: _handle_gate_toggle(svc, args["name"], True),
    "tausik_gates_disable": lambda svc, args: _handle_gate_toggle(svc, args["name"], False),
}
