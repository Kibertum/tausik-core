"""Exploration sessions: opening one, ending it, and asking what is open.

An exploration is the project's record of looking before deciding, which is why
it is its own home and not a line in a drawer of leftovers.
"""

from __future__ import annotations

from typing import Any
from project_service import ProjectService


def cmd_explore(svc: ProjectService, args: Any) -> None:
    c = args.explore_cmd
    if c == "start":
        print(svc.exploration_start(args.title, args.time_limit))
    elif c == "end":
        print(svc.exploration_end(args.summary, args.create_task))
    elif c == "current":
        exp = svc.exploration_current()
        if exp:
            elapsed = exp.get("elapsed_min", "?")
            limit = exp.get("time_limit_min", 30)
            over = " [OVER LIMIT]" if exp.get("over_limit") else ""
            print(f"Exploration #{exp['id']}: {exp['title']}")
            print(f"  Elapsed: {elapsed} min / {limit} min{over}")
        else:
            print("No active exploration.")
    else:
        print("Usage: tausik explore [start|end|current]")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
