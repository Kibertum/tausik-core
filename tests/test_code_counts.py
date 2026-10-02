"""Repo-state counters for source that ships in this repository."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from code_counts import (
    code_counts_flat,
    count_core_skills,
    count_roles,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_the_bundle_counts_only_source_that_ships_here(tmp_path):
    counts = code_counts_flat(tmp_path)
    assert set(counts) == {
        "review_agents_count",
        "hooks_count",
        "skills_core_count",
        "stacks_count",
        "roles_count",
    }


def test_the_other_counters_answer_zero_for_a_missing_tree(tmp_path):
    """NEGATIVE CONTRAST: only the optional sibling repo gets the None treatment.

    `harness/roles/` and `harness/skills/` ship inside this repository, so their
    absence is a broken checkout rather than an unprovisioned optional one, and
    a 0 there is an honest answer that the drift check should act on.
    """
    assert count_roles(tmp_path) == 0
    assert count_core_skills(tmp_path) == 0


def test_the_live_tree_counts_what_it_ships():
    """A floor, not an exact pin: these grow, and the point is that they are read."""
    assert count_roles(_REPO_ROOT) >= 6
    assert count_core_skills(_REPO_ROOT) >= 13
