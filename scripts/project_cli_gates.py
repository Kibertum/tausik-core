"""Gate state: what is enabled, what it costs, and what a mutation must record.

The printer travels with the command, because a gate report that formats itself
somewhere else is how a drawer of leftovers starts.
"""

from __future__ import annotations

from typing import Any
from project_service import ProjectService


def _print_gate(name: str, gate: dict, indent: str, verbose: bool) -> None:
    """Format and print a single gate entry."""
    status = "ON" if gate.get("enabled", True) else "OFF"
    severity = gate.get("severity", "warn")
    triggers = ", ".join(gate.get("trigger", []))
    desc = gate.get("description", "")
    cmd = gate.get("command") or "(built-in)"
    print(f"{indent}[{status}] {name} ({severity}) -> {triggers}")
    print(f"{indent}       {desc}")
    if verbose and gate.get("enabled", True):
        print(f"{indent}       cmd: {cmd}")


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
        data = svc.gates_status()
        gates = data["gates"]
        if not gates:
            print("No gates configured.")
            return
        stack_groups = data["stack_groups"]
        active_stacks = data["active_stacks"]
        verbose = c == "status"
        print("Quality Gates:")
        shown: set[str] = set()
        for name in stack_groups.get("general", []):
            if name in shown or name not in gates:
                continue
            shown.add(name)
            _print_gate(name, gates[name], "  ", verbose)
        for stack in sorted(stack_groups):
            if stack == "general":
                continue
            stack_gates = [g for g in stack_groups[stack] if g in gates and g not in shown]
            if not stack_gates:
                continue
            active = stack in active_stacks
            print(f"  [{stack}]" + (" (detected)" if active else ""))
            for name in stack_gates:
                shown.add(name)
                _print_gate(name, gates[name], "    ", verbose)
        if verbose:
            qg0 = data.get("qg0", {})
            no_goal = qg0.get("no_goal", [])
            no_ac = qg0.get("no_ac", [])
            planning = qg0.get("planning_count", 0)
            if no_goal or no_ac:
                print(f"\n  QG-0 Readiness ({planning} planning tasks):")
                if no_goal:
                    print(f"    ⚠{len(no_goal)} without goal: {', '.join(no_goal)}")
                if no_ac:
                    print(f"    ⚠{len(no_ac)} without acceptance_criteria: {', '.join(no_ac)}")
            elif planning:
                print(f"\n  QG-0 Readiness: all {planning} planning tasks have goal + AC")

    elif c == "enable":
        print(svc.gate_enable(args.name))
    elif c == "disable":
        print(svc.gate_disable(args.name))


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
