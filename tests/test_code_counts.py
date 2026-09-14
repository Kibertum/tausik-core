"""Repo-state counters, and the difference between "zero" and "not here".

`skills_official_count` is read from `skills-official/registry.json`, and that
directory is a SEPARATE, gitignored repository. The first cut of the counter
answered 0 when it was absent, which is a different claim from "there is no
answer" and cost two things at once, both measured in session #224:

* `gen_doc_constants.py --check` compares committed against computed by exact
  equality, so every clean checkout — every CI runner — went red. Reproduced by
  unpacking `git archive HEAD` into an empty directory and running the literal
  CI command.
* `write_cross_file_fixes` rewrites documents FROM the constants, so a merely
  corrupted registry would have written "0 official skills" into three files.

So the counter answers None when it cannot count, and the caller decides. The
cases below pin each way that can happen, because "the source is missing" is
exactly the branch nobody exercises until it is running on somebody else's
machine.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from code_counts import (  # noqa: E402
    code_counts_flat,
    count_core_skills,
    count_official_skills,
    count_roles,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _registry(tmp_path: Path, body: str) -> Path:
    directory = tmp_path / "skills-official"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "registry.json").write_text(body, encoding="utf-8")
    return tmp_path


def test_a_registry_that_is_there_is_counted(tmp_path):
    _registry(tmp_path, json.dumps({"version": 1, "skills": {"audit": {}, "jira": {}}}))
    assert count_official_skills(tmp_path) == 2


def test_a_list_of_skills_counts_the_same_as_a_mapping(tmp_path):
    """Both shapes are accepted on purpose — the registry has used each."""
    _registry(tmp_path, json.dumps({"skills": ["audit", "jira", "pdf"]}))
    assert count_official_skills(tmp_path) == 3


@pytest.mark.parametrize(
    ("body", "why"),
    [
        ("{ not json at all", "a corrupted file"),
        ("[1, 2, 3]", "a root that is not an object"),
        (json.dumps({"skills": "twenty"}), "a skills value that cannot be counted"),
        (json.dumps({"version": 1}), "no skills key"),
    ],
)
def test_an_uncountable_registry_answers_none_and_never_zero(tmp_path, body, why):
    """Zero is a claim about the catalogue; None is a claim about the reading.

    Returning 0 here is what would let the auto-fixer write "0 official skills"
    into the READMEs from a file somebody merely broke.
    """
    _registry(tmp_path, body)
    assert count_official_skills(tmp_path) is None, why


def test_a_missing_directory_answers_none(tmp_path):
    """The state of every clean clone — `skills-official/` is gitignored."""
    assert count_official_skills(tmp_path) is None


def test_the_bundle_omits_what_it_could_not_count(tmp_path):
    """Absence must reach the payload as absence, not as a zero.

    `build_constants_doc` restores the previously recorded value for a key that
    is missing here; it cannot do that for a key that arrived confidently wrong.
    """
    counts = code_counts_flat(tmp_path)
    assert "skills_official_count" not in counts
    assert set(counts) == {
        "review_agents_count",
        "hooks_count",
        "skills_core_count",
        "stacks_count",
        "roles_count",
    }
    _registry(tmp_path, json.dumps({"skills": ["a"]}))
    assert code_counts_flat(tmp_path)["skills_official_count"] == 1


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


def test_the_official_registry_counts_when_it_is_here():
    """`skills-official/` is a separate, gitignored repository: absent on every
    clean clone, every CI runner included. The counter says None there, and
    None means "the source is not here" — the module docstring above spells
    that out. The first version of this floor read `(None or 0) >= 20` and
    turned that answer into a failure on the GitLab lane for a week (session
    #251). Absent is a skip with the reason; present is the floor."""
    official = count_official_skills(_REPO_ROOT)
    if official is None:
        pytest.skip("skills-official/ is not checked out here — nothing to count")
    assert official >= 20
