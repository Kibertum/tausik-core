"""Gate state: what is enabled, what it costs, and what a mutation must record.

The printer travels with the command, because a gate report that formats itself
somewhere else is how a drawer of leftovers starts.
"""

from __future__ import annotations

from typing import Any
from project_service import ProjectService


def _gate_lines(name: str, gate: dict, indent: str, verbose: bool) -> list[str]:
    """Lines for a single gate entry."""
    status = "ON" if gate.get("enabled", True) else "OFF"
    severity = gate.get("severity", "warn")
    triggers = ", ".join(gate.get("trigger", []))
    desc = gate.get("description", "")
    cmd = gate.get("command") or "(built-in)"
    lines = [
        f"{indent}[{status}] {name} ({severity}) -> {triggers}",
        f"{indent}       {desc}",
    ]
    if verbose and gate.get("enabled", True):
        lines.append(f"{indent}       cmd: {cmd}")
    return lines


def gates_status_lines(data: dict, verbose: bool = True) -> list[str]:
    """The gates-status render — ONE formula for the CLI print and the MCP tool.

    mcp-gates-status-skryvaet-kolonku-cmd-i-sektsiyu: the MCP handler kept its
    own flat one-line-per-gate render and lost the per-gate cmd column and the
    QG-0 section this render shows — caught live by the surface parity ratchet
    on its first run. The formula lives here; both surfaces render it.
    """
    gates = data["gates"]
    if not gates:
        return ["No gates configured."]
    stack_groups = data["stack_groups"]
    active_stacks = data["active_stacks"]
    out: list[str] = ["Quality Gates:"]
    shown: set[str] = set()
    for name in stack_groups.get("general", []):
        if name in shown or name not in gates:
            continue
        shown.add(name)
        out.extend(_gate_lines(name, gates[name], "  ", verbose))
    for stack in sorted(stack_groups):
        if stack == "general":
            continue
        stack_gates = [g for g in stack_groups[stack] if g in gates and g not in shown]
        if not stack_gates:
            continue
        active = stack in active_stacks
        out.append(f"  [{stack}]" + (" (detected)" if active else ""))
        for name in stack_gates:
            shown.add(name)
            out.extend(_gate_lines(name, gates[name], "    ", verbose))
    if verbose:
        qg0 = data.get("qg0", {})
        no_goal = qg0.get("no_goal", [])
        no_ac = qg0.get("no_ac", [])
        planning = qg0.get("planning_count", 0)
        if no_goal or no_ac:
            out.append("")
            out.append(f"  QG-0 Readiness ({planning} planning tasks):")
            if no_goal:
                out.append(f"    ⚠{len(no_goal)} without goal: {', '.join(no_goal)}")
            if no_ac:
                out.append(f"    ⚠{len(no_ac)} without acceptance_criteria: {', '.join(no_ac)}")
        elif planning:
            out.append("")
            out.append(f"  QG-0 Readiness: all {planning} planning tasks have goal + AC")
    return out


def cmd_gates(svc: ProjectService, args: Any) -> None:
    """Handle gates subcommands: status, list, enable, disable."""
    c = args.gates_cmd or "status"
    if c == "ratchets":
        from project_root import root_from_service
        from ratchet_lane import NoRatchetTests, run as run_ratchets

        try:
            raise SystemExit(run_ratchets(root_from_service(svc) or "."))
        except NoRatchetTests as exc:
            # Absence, not a green: there was nothing to run, and saying "ok" would be
            # the report of a check that never happened.
            print(str(exc))
            raise SystemExit(2) from exc
    if c in ("status", "list"):
        for line in gates_status_lines(svc.gates_status(), verbose=(c == "status")):
            print(line)

    elif c == "enable":
        print(svc.gate_enable(args.name))
    elif c == "disable":
        print(svc.gate_disable(args.name))


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
