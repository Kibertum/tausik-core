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
    """v1.4 Verify-First Contract — transport over the ONE report builder.

    The report itself lives in `render_verify`, which `cmd_verify` also calls.
    This handler used to build its own, and the two drifted in both directions:
    the CLI alone reported duration, the recording line and the receipt; this
    one alone reported skipped gates. A cache hit reached only the CLI, so a
    cached green arrived here as a header over an empty gate list.

    What stays is what belongs to a handler: the error envelope. An MCP handler
    must not crash the server on a tool call.
    """
    from tausik_utils import ServiceError

    try:
        report = svc.run_verify_for_task(task_slug=task_slug, scope=scope, trigger=trigger)
    except ServiceError as e:
        return f"Error: {e}"
    except Exception as e:  # noqa: BLE001 — best-effort: a tool call must not kill the server
        return f"Error: {e}"
    from render_verify import verify_lines

    return "\n".join(verify_lines(svc, report, task_slug, scope))


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


def _handle_graph(svc, args: dict) -> str:
    """`tausik graph`, through the service, with the CLI's own renderer.

    ONE tool for three subcommands rather than three tools. The MCP surface is a
    ratchet standing at exactly its cap, and every tool's schema is a per-turn
    tax; three names for one capability would triple that tax for no extra
    reach. Raising the ratchet by one is argued in its own decision — by three
    it would not be arguable.
    """
    import io
    from contextlib import redirect_stdout

    try:
        from project_cli_graph import cmd_graph
    except Exception as e:  # noqa: BLE001 — a missing module must not kill the server
        return f"Error: graph command unavailable ({e})"

    class _Args:
        graph_cmd = str(args.get("command") or "status")
        path = args.get("path") or ""
        rebuild = bool(args.get("rebuild"))
        layer = "all"
        window = None
        json = False

    if _Args.graph_cmd == "show" and not _Args.path:
        return "Error: command=show needs a path, e.g. scripts/symbol_index.py"

    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            cmd_graph(svc, _Args())
    except SystemExit:
        # The CLI exits on a bad subcommand; a tool call must answer, not die.
        pass
    except Exception as e:  # noqa: BLE001 — MCP handler must not crash the server
        return f"Error: {e}\n{buffer.getvalue()}"
    return buffer.getvalue() or "(no output)"


VERIFICATION_HANDLERS = {
    "tausik_graph": _handle_graph,
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
