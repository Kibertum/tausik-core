"""The development gate must build the branch development actually happens on.

THE INCIDENT. ``.gitlab-ci.yml`` opens by calling itself "the development gate:
one Linux, every push". Its rules said something much narrower — a branch push
started a pipeline only when the branch *was* the default branch:

    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_COMMIT_TAG

Release 1.9 is written on ``v1-9-wave``. That branch is not ``main``, carried no
tag after v1.8.0, and had no merge request open, so none of the three rules could
fire. Measured against the GitLab API rather than inferred from the file: 0
pipelines for 79 pushed commits, and no pipeline of any kind in the project for
20 days. The gate was declared, wired and unreachable.

WHY A RATCHET AND NOT JUST A FIX. The damage was never the missing rule; it was
that nothing said the rule had gone missing. Two defect classes grew in the gap
and had to be found by hand — eleven ratchets that never executed in a clean
checkout, and a blocking gate switched off for everyone who cloned the repo.
Both live only in an environment that is not the maintainer's working copy, and
that environment is precisely what the unreachable rules declined to build.

WHY THIS FILE AND NOT ``test_ci_lanes_are_honest.py``, WHERE THE OTHER WORKFLOW
RATCHETS LIVE. That module is ``pytest.mark.slow`` at module scope, because its
lane-size checks each spawn a ``pytest --collect-only`` subprocess. GitLab runs
the fast lane, which is ``-m 'not slow'``. A guard on the GitLab trigger that
GitLab itself never executes would repeat the mistake it exists to prevent, so
these assertions — plain file reads, no subprocess — are kept unmarked and land
in the lane they guard.

The parsing is stdlib-only for the same reason the neighbouring ratchets are: no
lane may skip this check because an optional package was not provisioned.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT  # noqa: E402

pytestmark = pytest.mark.skipif(IS_PUBLIC_SNAPSHOT, reason=DORMANT_ON_PUBLIC_SNAPSHOT)

# Cross-cutting: the subject is a CI configuration file, not a Python module, so
# no import edge and no basename match can ever select this test. Without the
# declaration a scoped run skips it in silence — which is the very failure mode
# this file exists to catch, one level down.
CROSSCUTTING_SCOPE = [".gitlab-ci.yml"]

_ROOT = Path(__file__).resolve().parents[1]
_GITLAB_CI = _ROOT / ".gitlab-ci.yml"

#: A push of an ordinary commit, by a developer, to the branch named.
_PUSH = {"CI_PIPELINE_SOURCE": "push", "CI_DEFAULT_BRANCH": "main"}


class UnknownRuleGrammar(ValueError):
    """A rule condition uses a form this evaluator does not implement.

    Raised rather than treated as false. A condition nobody can evaluate is the
    exact shape of the bug this file guards: silently unreachable. If the
    workflow grows a new operator, these tests must go red and be taught it, not
    quietly start guarding less than they claim.
    """


def _rules() -> list[tuple[str, str | None]]:
    """The ``workflow.rules`` list as ordered ``(condition, when)`` pairs.

    Hand-parsed from the known shape of this one block rather than with a YAML
    library, so the check cannot be skipped on a runner without PyYAML.
    """
    assert _GITLAB_CI.exists(), f"{_GITLAB_CI} is missing — the development gate cannot be checked"
    lines = _GITLAB_CI.read_text(encoding="utf-8").splitlines()

    if "workflow:" not in lines:
        return []
    start = lines.index("workflow:")

    out: list[tuple[str, str | None]] = []
    in_rules = False
    for raw in lines[start + 1 :]:
        stripped = raw.strip()
        if raw and not raw[0].isspace():
            break  # dedented to column 0 — the workflow block has ended
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "rules:":
            in_rules = True
            continue
        if not in_rules:
            continue
        if stripped.startswith("- if:"):
            out.append((stripped[len("- if:") :].strip(), None))
        elif stripped.startswith("when:") and out:
            condition, _ = out[-1]
            out[-1] = (condition, stripped[len("when:") :].strip())
    return out


def _value(token: str, variables: dict[str, str]) -> str:
    """Resolve one operand: ``$VAR`` against the environment, or a quoted literal."""
    token = token.strip()
    if token.startswith("$"):
        return variables.get(token[1:], "")
    return token.strip('"').strip("'")


def _condition_holds(condition: str, variables: dict[str, str]) -> bool:
    """Evaluate a GitLab ``if:`` expression in the forms this workflow uses.

    Supported, and deliberately no more: ``A && B``, ``$VAR == operand``, and a
    bare ``$VAR`` meaning "set and non-empty". Anything else raises.
    """
    if "&&" in condition:
        return all(_condition_holds(part, variables) for part in condition.split("&&"))
    if "==" in condition:
        left, right = condition.split("==", 1)
        return _value(left, variables) == _value(right, variables)
    condition = condition.strip()
    if condition.startswith("$") and " " not in condition:
        return bool(_value(condition, variables))
    raise UnknownRuleGrammar(condition)


def _pipeline_runs(variables: dict[str, str]) -> bool:
    """Whether GitLab would start a pipeline for this set of predefined variables.

    First matching rule decides, which is GitLab's own semantics; ``when: never``
    on that rule suppresses the pipeline. No match at all means no pipeline.
    """
    for condition, when in _rules():
        if _condition_holds(condition, variables):
            return when != "never"
    return False


def test_the_workflow_block_was_found():
    """Self-check. If the block moves or is renamed, every assertion below would
    pass vacuously against an empty rule list — green because unparsed."""
    rules = _rules()
    assert len(rules) >= 3, (
        f"parsed only {len(rules)} workflow rule(s) from {_GITLAB_CI.name}: {rules}. "
        "The block moved or changed shape and this ratchet is guarding nothing."
    )


def test_every_rule_uses_a_grammar_this_check_understands():
    """A condition the evaluator cannot read would be silently skipped, and the
    defect being guarded here is precisely a rule nobody noticed was unreachable."""
    for condition, _ in _rules():
        _condition_holds(condition, {**_PUSH, "CI_COMMIT_BRANCH": "main"})


@pytest.mark.parametrize(
    "branch",
    [
        "v1-9-wave",  # the branch release 1.9 is actually written on
        "main",  # the default branch, which used to be the only one built
        "release/1.8-batch-s126",  # the naming a previous release wave used
        "fix/windows-gates-and-consumer-drift",  # an ordinary working branch
    ],
)
def test_a_push_to_any_branch_starts_a_pipeline(branch):
    """The header of .gitlab-ci.yml promises "every push". Every push means every
    branch — naming the buildable ones is how v1-9-wave went 79 commits unbuilt."""
    assert _pipeline_runs({**_PUSH, "CI_COMMIT_BRANCH": branch}), (
        f"a push to {branch!r} starts no pipeline. The development gate does not build "
        "the branch development happens on — the condition that let 1.9 grow two classes "
        "of defect unseen for 20 days."
    )


def test_a_tag_still_starts_a_pipeline():
    """Release verification predates this change and must survive it."""
    assert _pipeline_runs({"CI_PIPELINE_SOURCE": "push", "CI_COMMIT_TAG": "v1.9.0"})


def test_a_merge_request_still_starts_a_pipeline():
    assert _pipeline_runs({"CI_PIPELINE_SOURCE": "merge_request_event"})


def test_an_open_merge_request_does_not_also_build_the_branch():
    """With an MR open a push matches both the merge_request_event rule and the
    branch rule. Every runner on this instance is a shell executor sharing one
    workspace per project, so a duplicate pipeline is not just waste — the two
    runs clean and rebuild the same directory underneath each other."""
    assert not _pipeline_runs(
        {**_PUSH, "CI_COMMIT_BRANCH": "v1-9-wave", "CI_OPEN_MERGE_REQUESTS": "kibertum/core!7"}
    ), "a branch push with an open merge request starts a second, duplicate pipeline"


def test_the_file_still_promises_what_it_now_delivers():
    """The gap this task closed was between a sentence and a rule list. If the
    promise is ever edited away, the rules above are no longer anchored to
    anything a reader was told, and the drift can start again from the other end.
    """
    header = _GITLAB_CI.read_text(encoding="utf-8")
    assert "every push" in header, (
        f"{_GITLAB_CI.name} no longer states the promise its rules implement. Either "
        "restore the wording or change the rules deliberately — do not let the two drift."
    )
