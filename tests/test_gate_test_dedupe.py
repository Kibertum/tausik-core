"""The duplicate-shape detector is a gate now, and the ratchet only turns down.

`audit_pytest_dedupe` had a `--check` flag and was documented as review-only, so
nothing ran it and the number grew unwatched — 294 groups / 683 tests in session
#178, 322 / 753 when the gate landed. This module holds the gate to the two
properties that make it worth having: it reddens on GROWTH, and it can never be
satisfied by deleting tests, because it does not measure how many there are.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import gate_test_dedupe  # noqa: E402
from gate_test_dedupe import (  # noqa: E402
    load_baseline,
    measure,
    run_test_dedupe_gate,
)

# Reads the committed baseline and every test file — no import edge selects it.
CROSSCUTTING_SCOPE = ["tests/", "tausik/gates.json", "scripts/gate_test_dedupe.py"]


def _committed_baseline() -> dict:
    with open(os.path.join(_ROOT, "tausik", "gates.json"), encoding="utf-8") as fh:
        return json.load(fh)["test_dedupe"]["baseline"]


def test_the_gate_is_green_on_the_repo_it_landed_on():
    """A gate that reddens on everything the day it lands gets switched off."""
    ok, message = run_test_dedupe_gate({}, [])
    assert ok, message


def test_the_baseline_only_ratchets_down():
    """A line nobody lowers is a list, not a ratchet.

    Measured BELOW the baseline is not a pass to enjoy quietly — it is the
    moment the baseline is meant to move, and this is what makes it move.
    """
    groups_n, tests_n, _ = measure(_ROOT)
    baseline = _committed_baseline()
    assert baseline["groups"] <= groups_n and baseline["tests"] <= tests_n, (
        "duplicate-shape debt is below the committed baseline "
        f"(measured {groups_n} groups / {tests_n} tests, baseline "
        f"{baseline['groups']} / {baseline['tests']}) — lower it in "
        "tausik/gates.json to what was achieved"
    )


def test_growth_is_red_and_says_where(monkeypatch):
    """Negative: the whole point. One more copy of an existing shape blocks."""
    import gate_test_dedupe

    groups_n, tests_n, groups = measure(_ROOT)
    monkeypatch.setattr(
        gate_test_dedupe,
        "measure",
        lambda *a, **k: (groups_n + 1, tests_n + 2, groups),
    )
    ok, message = run_test_dedupe_gate({}, [])
    assert not ok
    assert "GREW" in message
    assert f"{groups_n + 1} > baseline {groups_n}" in message
    assert ".py:" in message, "a count with no address is not actionable"


def test_deleting_tests_can_never_satisfy_the_gate(monkeypatch):
    """Negative: the subject is distinguishability, not volume.

    Fewer tests than the baseline is a PASS, and the message asks for the
    baseline to come down — nothing here rewards removing tests that are
    already distinguishable, because their number is never measured.
    """
    import gate_test_dedupe

    _, _, groups = measure(_ROOT)
    monkeypatch.setattr(gate_test_dedupe, "measure", lambda *a, **k: (1, 2, groups))
    ok, message = run_test_dedupe_gate({}, [])
    assert ok
    assert "BELOW the baseline" in message


def test_an_unreadable_baseline_refuses_instead_of_passing(monkeypatch):
    """Negative: missing is not clean.

    Reporting "no duplicates recorded" for an unreadable file would turn the
    loss of the baseline into a green verdict about the tests.
    """
    import gate_test_dedupe

    monkeypatch.setattr(gate_test_dedupe, "load_baseline", lambda *a, **k: None)
    ok, message = run_test_dedupe_gate({}, [])
    assert not ok
    assert "could not be read" in message


def test_the_baseline_is_committed_and_typed():
    """The ratchet lives in git, next to the other gate baselines.

    `copies` joined `groups` and `tests` when the shape count was measured and found
    not to mean duplication: 284 of 286 groups differ in the parts the signature
    erases. The shape numbers stayed as a declared remainder about similarity; the
    number that reddens is the one that survives reading the code.
    """
    baseline = load_baseline(_ROOT)
    assert baseline is not None, "tausik/gates.json carries no test_dedupe baseline"
    assert set(baseline) == {"groups", "tests", "copies"}
    assert all(isinstance(v, int) for v in baseline.values())


def test_a_baseline_without_copies_reads_as_zero(tmp_path):
    """A project that adopted the ratchet before `copies` existed keeps working.

    Zero is the safe reading rather than a convenience: growth above zero still
    reddens, so an older baseline GAINS the check instead of losing one.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "tausik").mkdir()
    (tmp_path / "tausik" / "gates.json").write_text(
        json.dumps({"test_dedupe": {"baseline": {"groups": 5, "tests": 11}}}),
        encoding="utf-8",
    )
    baseline = load_baseline(str(tmp_path))
    assert baseline == {"groups": 5, "tests": 11, "copies": 0}


def test_the_gate_is_registered_on_the_blocking_triggers():
    """A detector nobody runs is what this task existed to end."""
    from gate_registry import PHASE_SCOPED, specs_for_phase

    spec = next(s for s in specs_for_phase(PHASE_SCOPED) if s.name == "test_dedupe")
    assert spec.default_config["enabled"] is True
    assert spec.default_config["severity"] == "block"
    assert set(spec.default_config["trigger"]) == {"task-done", "commit"}


class TestTheVerdictIsWhatReddens:
    """The threshold moved from shape to literal identity, and the reason is a number.

    MEASURED over 286 groups: 284 (99.3%) differ in the very parts the signature
    erases -- names, strings, numbers -- so the shape count was reporting "same
    contract, different input", which is what a suite is supposed to look like. Two
    groups held literally the same code. The category the audit could not decide was
    therefore the only one worth a gate, and the shape numbers became a declared
    remainder about similarity rather than a claim about duplication.

    A third category was measured and found EMPTY: of 7829 test functions none is
    unable to fail, so no check is needed for tests that assert nothing.
    """

    @staticmethod
    def _repo(tmp_path, body_a: str, body_b: str, baseline: dict) -> str:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tausik").mkdir()
        (tmp_path / "tests" / "test_sample.py").write_text(
            f"def test_one():\n{body_a}\n\n\ndef test_two():\n{body_b}\n",
            encoding="utf-8",
        )
        (tmp_path / "tausik" / "gates.json").write_text(
            json.dumps({"test_dedupe": {"baseline": baseline}}), encoding="utf-8"
        )
        return str(tmp_path)

    def test_a_literal_copy_above_the_baseline_is_red(self, tmp_path, monkeypatch):
        root = self._repo(
            tmp_path,
            "    assert compute(1) == 2",
            "    assert compute(1) == 2",
            {"groups": 9, "tests": 99, "copies": 0},
        )
        monkeypatch.setattr(gate_test_dedupe, "_repo_root", lambda: root)
        ok, message = run_test_dedupe_gate({}, [])
        assert not ok
        assert "copies: 1 > baseline 0" in message

    def test_the_same_shape_on_a_different_input_is_green(self, tmp_path, monkeypatch):
        """The 99.3% case. A parallel must not redden, or the gate is unusable.

        Same shape, different literal — exactly what `parametrize` would express and
        exactly what the old threshold called debt.
        """
        root = self._repo(
            tmp_path,
            "    assert compute(1) == 2",
            "    assert compute(7) == 14",
            {"groups": 9, "tests": 99, "copies": 0},
        )
        monkeypatch.setattr(gate_test_dedupe, "_repo_root", lambda: root)
        ok, message = run_test_dedupe_gate({}, [])
        assert ok, message

    def test_an_unreadable_file_is_not_called_a_copy(self, tmp_path, monkeypatch):
        """A file the classifier cannot parse says nothing about the tests inside it.

        Fail-open on the VERDICT, not on the gate: an unreadable member makes the
        group a parallel, because calling it a copy would turn a broken read into an
        accusation and a red close.
        """
        root = self._repo(
            tmp_path,
            "    assert compute(1) == 2",
            "    assert compute(1) == 2",
            {"groups": 9, "tests": 99, "copies": 0},
        )
        (tmp_path / "tests" / "test_sample.py").write_text(
            "def test_one():\n    assert compute(1) == 2\n\n\ndef test_two():\n"
            "    assert compute(1) == 2\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(gate_test_dedupe, "_repo_root", lambda: root)
        import audit_pytest_dedupe

        monkeypatch.setattr(
            audit_pytest_dedupe, "_qualified_bodies", lambda path: (_ for _ in ()).throw(OSError())
        )
        ok, message = run_test_dedupe_gate({}, [])
        assert ok, message


class TestNoTestInThisSuiteIsUnableToFail:
    """The third category the dedupe task named, measured and held at zero.

    A test that is always green is worse than a missing one: it reports coverage
    that does not exist, and the count in the README badge stops meaning anything.
    Unlike "copy" and "parallel" this one is decidable without reading intent --
    "cannot fail" is a property of the code.

    MEASURED across 7829 test functions: zero. The check is here rather than in the
    audit report because a number in a document is not a guard; this reddens if the
    first hollow test arrives.
    """

    @staticmethod
    def _hollow_reason(node: ast.AST) -> str | None:
        body = list(getattr(node, "body", []))
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        if not body or all(isinstance(s, ast.Pass) for s in body):
            return "body is empty"
        asserts = [n for n in ast.walk(node) if isinstance(n, ast.Assert)]
        raising = [n for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr == "raises"]
        calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
        if not asserts and not raising and not calls:
            return "no assert and no call"
        if (
            asserts
            and not raising
            and all(isinstance(a.test, ast.Constant) and bool(a.test.value) for a in asserts)
        ):
            return "every assert is on a truthy constant"
        return None

    def test_the_suite_holds_no_test_that_cannot_fail(self):
        hollow = []
        counted = 0
        for path in sorted(Path(_ROOT, "tests").rglob("test_*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and node.name.startswith("test"):
                    counted += 1
                    reason = self._hollow_reason(node)
                    if reason:
                        hollow.append(f"{path.name}:{node.lineno} {node.name} — {reason}")
        assert counted > 5000, f"only {counted} test functions found — the walk is broken"
        assert hollow == [], hollow[:10]

    @pytest.mark.parametrize(
        ("source", "reason"),
        [
            pytest.param("def test_x():\n    pass\n", "body is empty", id="pass_only"),
            pytest.param('def test_x():\n    """doc"""\n', "body is empty", id="docstring_only"),
            pytest.param(
                "def test_x():\n    assert True\n",
                "every assert is on a truthy constant",
                id="assert_true",
            ),
            pytest.param(
                "def test_x():\n    assert 1\n",
                "every assert is on a truthy constant",
                id="assert_one",
            ),
        ],
    )
    def test_the_detector_recognises_a_hollow_test(self, source, reason):
        """POSITIVE half: the check above is only worth its zero if it can see one.

        A scanner that returns "none found" because it recognises nothing is the same
        bug it was written to catch, one level up.
        """
        node = ast.parse(source).body[0]
        assert self._hollow_reason(node) == reason

    def test_a_real_test_is_not_called_hollow(self):
        """NEGATIVE half: an ordinary assertion must not trip the scanner."""
        node = ast.parse("def test_x():\n    assert compute(2) == 4\n").body[0]
        assert self._hollow_reason(node) is None
