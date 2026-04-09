"""Tests for batch-run plan parser."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from plan_parser import Plan, PlanTask, parse_plan


VALID_PLAN = """\
# Deploy Auth System

## Context
We need auth before launching v2.

## Validation
- `pytest tests/ -x -q`
- `ruff check scripts/`

## Tasks

### Task 1: Create auth module
**Goal:** Users can log in with email/password
**Files:** src/auth.py, src/routes.py
- [ ] Create auth module
- [ ] Add JWT tokens
- [x] Write tests

### Task 2: Add rate limiting
**Goal:** Prevent brute force attacks
- [ ] Add middleware
- [ ] Configure limits
"""


class TestParsePlan:
    def test_title(self):
        plan = parse_plan(VALID_PLAN)
        assert plan.title == "Deploy Auth System"

    def test_context(self):
        plan = parse_plan(VALID_PLAN)
        assert "auth before launching v2" in plan.context

    def test_validation_commands(self):
        plan = parse_plan(VALID_PLAN)
        assert plan.validation_commands == ["pytest tests/ -x -q", "ruff check scripts/"]

    def test_task_count(self):
        plan = parse_plan(VALID_PLAN)
        assert len(plan.tasks) == 2

    def test_task_fields(self):
        plan = parse_plan(VALID_PLAN)
        t1 = plan.tasks[0]
        assert t1.number == 1
        assert t1.title == "Create auth module"
        assert t1.goal == "Users can log in with email/password"
        assert t1.files == ["src/auth.py", "src/routes.py"]
        assert len(t1.steps) == 3
        assert t1.completed == [False, False, True]

    def test_task_without_files(self):
        plan = parse_plan(VALID_PLAN)
        t2 = plan.tasks[1]
        assert t2.files == []
        assert t2.goal == "Prevent brute force attacks"

    def test_no_tasks_raises(self):
        with pytest.raises(ValueError, match="no tasks"):
            parse_plan("# Empty Plan\n## Tasks\n")

    def test_task_without_goal_raises(self):
        text = "# Plan\n## Tasks\n### Task 1: No goal here\n- [ ] Do stuff\n"
        with pytest.raises(ValueError, match="no goal"):
            parse_plan(text)

    def test_untitled_plan(self):
        text = "## Tasks\n### Task 1: Foo\n**Goal:** Bar\n"
        plan = parse_plan(text)
        assert plan.title == "Untitled Plan"

    def test_no_validation(self):
        text = "# Plan\n## Tasks\n### Task 1: Foo\n**Goal:** Bar\n"
        plan = parse_plan(text)
        assert plan.validation_commands == []

    def test_no_context(self):
        text = "# Plan\n## Tasks\n### Task 1: Foo\n**Goal:** Bar\n"
        plan = parse_plan(text)
        assert plan.context == ""
