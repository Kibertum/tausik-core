"""Running a declared command through the project rather than around it."""

from __future__ import annotations

import os
import sys
from typing import Any
from project_service import ProjectService


def cmd_run(svc: ProjectService, args: Any) -> None:
    """Parse and display a batch-run plan summary."""
    from plan_parser import parse_plan

    plan_file = args.plan_file
    if not os.path.isfile(plan_file):
        print(f"Error: Plan file not found: {plan_file}", file=sys.stderr)
        sys.exit(1)

    with open(plan_file, encoding="utf-8") as f:
        text = f.read()

    plan = parse_plan(text)

    print(f"Plan: {plan.title}")
    if plan.context:
        print(f"Context: {plan.context[:200]}")
    if plan.validation_commands:
        print(f"Validation: {', '.join(plan.validation_commands)}")
    print(f"Tasks: {len(plan.tasks)}")
    for task in plan.tasks:
        done = sum(task.completed)
        total = len(task.steps)
        status = f" ({done}/{total} done)" if total else ""
        print(f"  {task.number}. {task.title}{status}")
        print(f"     Goal: {task.goal}")
        if task.files:
            print(f"     Files: {', '.join(task.files)}")
    print("\nTo execute this plan, use /run in an interactive session.")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
