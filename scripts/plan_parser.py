"""Parser for batch-run markdown plans.

Extracts context, validation commands, and tasks from a markdown plan file.
Format: see agents/skills/run/SKILL.md for specification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PlanTask:
    """A single task extracted from a plan."""

    number: int
    title: str
    goal: str
    files: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    completed: list[bool] = field(default_factory=list)


@dataclass
class Plan:
    """Parsed markdown plan."""

    title: str
    context: str = ""
    validation_commands: list[str] = field(default_factory=list)
    tasks: list[PlanTask] = field(default_factory=list)


def parse_plan(text: str) -> Plan:
    """Parse a markdown plan into structured data.

    Raises ValueError if plan is invalid.
    """
    lines = text.split("\n")
    plan = Plan(title="")

    # Extract title from first # heading
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            plan.title = line[2:].strip()
            break

    if not plan.title:
        plan.title = "Untitled Plan"

    # Split into sections by ## headings
    sections: dict[str, list[str]] = {}
    current_section = ""
    for line in lines:
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            sections[current_section] = []
        elif current_section:
            sections.setdefault(current_section, []).append(line)

    # Parse context
    if "context" in sections:
        plan.context = "\n".join(sections["context"]).strip()

    # Parse validation commands
    if "validation" in sections:
        for line in sections["validation"]:
            m = re.match(r"^-\s+`(.+)`", line.strip())
            if m:
                plan.validation_commands.append(m.group(1))

    # Parse tasks from ## Tasks section
    task_lines = sections.get("tasks", [])
    current_task: PlanTask | None = None
    task_num = 0

    for line in task_lines:
        # ### Task N: Title
        m = re.match(r"^###\s+Task\s+\d+:\s*(.+)", line)
        if m:
            if current_task:
                plan.tasks.append(current_task)
            task_num += 1
            current_task = PlanTask(number=task_num, title=m.group(1).strip(), goal="")
            continue

        if not current_task:
            continue

        stripped = line.strip()

        # **Goal:** text
        m = re.match(r"\*\*Goal:\*\*\s*(.+)", stripped)
        if m:
            current_task.goal = m.group(1).strip()
            continue

        # **Files:** file1, file2
        m = re.match(r"\*\*Files:\*\*\s*(.+)", stripped)
        if m:
            current_task.files = [f.strip() for f in m.group(1).split(",")]
            continue

        # - [ ] or - [x] checklist items
        m = re.match(r"^-\s+\[([ xX])\]\s+(.+)", stripped)
        if m:
            current_task.steps.append(m.group(2).strip())
            current_task.completed.append(m.group(1).lower() == "x")

    if current_task:
        plan.tasks.append(current_task)

    # Validate
    if not plan.tasks:
        raise ValueError("Plan has no tasks. Add ### Task N: sections under ## Tasks.")

    for task in plan.tasks:
        if not task.goal:
            raise ValueError(
                f"Task {task.number} '{task.title}' has no goal. Add **Goal:** line."
            )

    return plan
