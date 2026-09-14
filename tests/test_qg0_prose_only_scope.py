"""QG-0 asks a negative scenario only from work that changes behaviour.

The rule shipped in HARD_CONSTRAINTS (decision #371) said so; the gate kept
refusing a logo/README task for lacking one. A scope of prose and assets has
no behaviour a negative case could exercise; an undeclared scope, or any code
in it, keeps the refusal exactly as before.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
)

from gate_qg0_check import check_qg0_start  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

_AC_WITHOUT_NEGATIVE = (
    "AC-1: the page shows the new logo. AC-2: the assets README names both files."
)


def _task(scope_paths: list[str] | None) -> dict:
    return {
        "goal": "Swap the logo",
        "acceptance_criteria": _AC_WITHOUT_NEGATIVE,
        "complexity": "simple",
        "rollback_plan": "git revert",
        "scope_paths": json.dumps(scope_paths) if scope_paths is not None else None,
    }


def test_a_prose_and_assets_scope_passes_without_a_negative_scenario():
    check_qg0_start("logo", _task(["docs/assets/x.png", "README.md", "tests/test_x.py"]))


@pytest.mark.parametrize(
    "scope",
    [None, ["scripts/x.py"], ["README.md", "scripts/x.py"], ["tests/test_x.py"]],
    ids=["undeclared", "code", "prose-plus-code", "tests-only"],
)
def test_any_other_scope_is_still_refused(scope):
    with pytest.raises(ServiceError, match="AC has no negative scenario"):
        check_qg0_start("logo", _task(scope))
