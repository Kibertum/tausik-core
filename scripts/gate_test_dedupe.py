"""Structurally indistinguishable tests are caught by a GATE, not by a report.

`audit_pytest_dedupe` has grouped tests by AST shape for a long time, and it has
a `--check` flag. Nothing ran it: it was documented as "static audit reports
(review-only)", so the check existed and blocked nothing — the same pattern as
`memory lint`, and the same outcome. The debt measured 294 groups / 683 tests in
session #178; it measures 322 / 753 today. A detector nobody runs does not stop
a number from growing, it only makes it possible to say afterwards how much it
grew.

WHAT IS MEASURED IS DISTINGUISHABILITY, NOT COUNT. This gate never looks at how
many tests the repo has and never reddens because that number rose. Two tests
whose bodies are the same shape modulo names, strings and numbers cover the same
path twice; removing one of them is the intended remedy, and the gate says so in
its own message. A gate on the raw total would pay for deletions, which is the
opposite discipline — the subject is evidence, and two copies of one argument are
still one argument.

THE BASELINE IS A RATCHET AND IT MAY ONLY TURN DOWN. Today's debt is recorded in
the committed `tausik/gates.json` beside the other gate baselines, so landing
this gate blocks nothing that already exists; only GROWTH is red. A baseline
found to be ABOVE the measurement is itself a failure — see the test that pins
it — because a line nobody lowers is a list, not a ratchet.

The detector is reused, not rewritten: the numbers come from
`audit_pytest_dedupe.collect_duplicates`, which is the same code the report
prints. Measured cost of the whole scan when this landed: 0.78 s over 403 test
files.
"""

from __future__ import annotations

import json
import os
from typing import Any

#: What the gate reports when the committed baseline is missing entirely. Zero
#: would make every existing duplicate a violation the day the file is lost —
#: a red gate on a repo nobody changed. `None` is the third state: the baseline
#: was not read, which is neither "no debt" nor a verdict about the tests.
_BASELINE_KEYS = ("groups", "tests")


def _repo_root() -> str:
    """The .git-anchored repo root, NOT this file's parent's parent.

    Gates execute from the DEPLOYED copy (`.claude/scripts/`), where a naive
    dirname-twice lands on `.claude/` — which has a `scripts/` mirror but no
    `tausik/gates.json` and no `tests/`. That would measure the mirror and lose
    the baseline, which is exactly how the class-surface gate learned this.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(12):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for candidate in (os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        if os.path.isdir(os.path.join(candidate, "tests")):
            return candidate
    return os.path.dirname(here)


def ratchet_file_exists(repo_root: str | None = None) -> bool:
    """Has this project a `tausik/gates.json` at all?

    THE DISTINCTION THIS EXISTS FOR, found by walking the consumer path (session
    #240): a project that has never recorded a ratchet is not a project whose
    ratchet is corrupt. A fresh install has no `tausik/gates.json`, and treating
    that as "unreadable" made this blocking gate refuse the FIRST close of every
    new project — the gate was green here only because our own tree has the file.
    """
    root = repo_root or _repo_root()
    return os.path.isfile(os.path.join(root, "tausik", "gates.json"))


def load_baseline(repo_root: str | None = None) -> dict[str, int] | None:
    """The committed ratchet, or None when it could not be read.

    None is not `{}` and neither is zero: an unreadable baseline must not be
    reported as "no debt recorded", which would turn every existing duplicate
    into a fresh violation on a repo nobody touched.

    None also does not distinguish "no file" from "bad node" — ask
    `ratchet_file_exists` for that. The two deserve different verdicts and only
    one of them is a violation.
    """
    root = repo_root or _repo_root()
    path = os.path.join(root, "tausik", "gates.json")
    try:
        with open(path, encoding="utf-8") as fh:
            node = json.load(fh).get("test_dedupe")
    except (OSError, ValueError):
        return None
    if not isinstance(node, dict):
        return None
    baseline = node.get("baseline")
    if not isinstance(baseline, dict):
        return None
    if not all(isinstance(baseline.get(k), int) for k in _BASELINE_KEYS):
        return None
    return {k: int(baseline[k]) for k in _BASELINE_KEYS}


def measure(repo_root: str | None = None) -> tuple[int, int, list[dict[str, Any]]]:
    """(groups, tests in those groups, the groups themselves)."""
    from pathlib import Path

    from audit_pytest_dedupe import collect_duplicates

    groups: list[dict[str, Any]] = collect_duplicates(Path(repo_root or _repo_root()))
    members = sum(len(list(g["members"])) for g in groups)
    return len(groups), members, groups


def _worst(groups: list[dict[str, Any]], limit: int = 3) -> list[str]:
    """The largest groups, named — a count with no address is not actionable."""
    ranked = sorted(groups, key=lambda g: -len(g["members"]))[:limit]
    lines = []
    for group in ranked:
        members = group["members"]
        where = ", ".join(f"{m['file']}:{m['lineno']}" for m in members[:3])
        more = f" (+{len(members) - 3} more)" if len(members) > 3 else ""
        lines.append(f"  {len(members)} tests share one shape: {where}{more}")
    return lines


def run_test_dedupe_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Repo-wide duplicate-shape check. `files` is IGNORED, by design.

    A per-file view cannot see a duplicate: the second copy of a shape is only
    a duplicate relative to the first, which usually lives in another file that
    this commit did not touch.
    """
    baseline = load_baseline()
    groups_n, tests_n, groups = measure()
    measured = f"{groups_n} group(s) covering {tests_n} test(s)"

    if baseline is None and not ratchet_file_exists():
        # NOT ADOPTED is not VIOLATED. A project with no `tausik/gates.json` has
        # never recorded a ratchet; refusing its first close teaches nothing and
        # blocks everything. The measurement is still reported, and it is exactly
        # what the project needs in order to adopt the ratchet — so the notice
        # carries the numbers rather than sending the reader to compute them.
        return True, (
            f"test-dedupe ratchet NOT ADOPTED by this project — measured {measured}. "
            "This is the absence of a baseline, not a violation of one. To start "
            "ratcheting, put this into `tausik/gates.json` — "
            f'"test_dedupe": {{"baseline": {{"groups": {groups_n}, "tests": {tests_n}}}}}'
        )

    if baseline is None:
        # The file EXISTS and its node could not be read. Unreadable is not
        # clean: saying "no duplicates recorded" here would turn a corrupted
        # ratchet into a green verdict about the tests.
        return False, (
            "The test-dedupe ratchet could not be read from tausik/gates.json "
            f"(node `test_dedupe.baseline` with integer {' and '.join(_BASELINE_KEYS)}). "
            f"Measured {measured} — but with no baseline this gate cannot tell "
            "existing debt from new, so it refuses rather than guess."
        )

    grew = [
        f"{key}: {value} > baseline {baseline[key]}"
        for key, value in (("groups", groups_n), ("tests", tests_n))
        if value > baseline[key]
    ]
    if grew:
        detail = "\n".join(_worst(groups))
        return False, (
            "Structurally indistinguishable tests GREW — "
            + "; ".join(grew)
            + ".\nThe subject is DISTINGUISHABILITY, not count: two tests with "
            "the same shape modulo names, strings and numbers cover one path "
            "twice. Merge them (parametrise) or make the new one actually "
            "differ. Largest groups:\n" + detail + "\nFull report: "
            "`python scripts/audit_pytest_dedupe.py`."
        )
    improved = groups_n < baseline["groups"] or tests_n < baseline["tests"]
    note = " Debt is BELOW the baseline — lower it in tausik/gates.json." if improved else ""
    return True, f"Duplicate-shape debt within the ratchet ({measured}).{note}"
