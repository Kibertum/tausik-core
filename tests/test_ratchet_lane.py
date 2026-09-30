"""The ratchets answerable in seconds, and a set that cannot quietly shrink.

THE MEASUREMENT. Fifteen ratchets live in `tausik/gates.json`, each guarded by its own test,
and the only way to learn you moved one was the full lane — 12 441 tests, five minutes, plus
a call to work out which failure was yours. Ratchets went red on the author's own work about
ten times in the session that filed this. The same guards run in 23 seconds.

WHAT THESE TESTS GUARD IS THE SET. A fast lane is worth having only while it still contains
every ratchet test; one that silently lost a file would report green over a ratchet nobody
checked, which is worse than the five minutes it replaced. So the tests below are about
membership: derived rather than listed, found through an import as well as directly, and
refusing outright when the set comes out empty.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import ratchet_lane as lane  # noqa: E402


def _tree(tmp_path: Path, tests: dict[str, str], scripts: dict[str, str] | None = None) -> Path:
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts").mkdir()
    for name, text in tests.items():
        (tmp_path / "tests" / name).write_text(text, encoding="utf-8")
    for name, text in (scripts or {}).items():
        (tmp_path / "scripts" / name).write_text(text, encoding="utf-8")
    return tmp_path


class TestTheSetIsDerivedFromTheTree:
    def test_a_test_naming_the_baseline_is_in(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": 'p = "tausik/gates.json"\n'})
        assert lane.ratchet_tests(root) == ["tests/test_a.py"]

    def test_a_new_ratchet_test_needs_no_registration(self, tmp_path):
        """AC-2. A hand-kept list goes blind the first time someone forgets it — which is
        how a guard in this project once stayed green while seven labels left its view."""
        root = _tree(tmp_path, {"test_a.py": 'x = "gates.json"\n', "test_b.py": "x = 1\n"})
        (root / "tests" / "test_new_ratchet.py").write_text('y = "gates.json"', encoding="utf-8")
        assert lane.ratchet_tests(root) == ["tests/test_a.py", "tests/test_new_ratchet.py"]

    def test_a_test_reaching_the_baseline_through_an_import_is_in(self, tmp_path):
        """The half the first version missed: `test_gate_ruff_format.py` reads the baseline
        through `gate_ruff_format.legacy_unformatted()` and was left out — of the very
        ratchet that had gone red that morning."""
        root = _tree(
            tmp_path,
            {"test_a.py": "import gate_thing\n\n\ndef test_x():\n    pass\n"},
            {"gate_thing.py": 'BASE = "tausik/gates.json"\n'},
        )
        assert lane.ratchet_tests(root) == ["tests/test_a.py"]

    @pytest.mark.parametrize(
        "form", ["import gate_thing", "from gate_thing import x", "import gate_thing as g"]
    )
    def test_the_import_is_recognised_however_it_is_written(self, form, tmp_path):
        root = _tree(tmp_path, {"test_a.py": form + "\n"}, {"gate_thing.py": 'p = "gates.json"'})
        assert lane.ratchet_tests(root) == ["tests/test_a.py"]


class TestWhatStaysOut:
    def test_a_file_that_only_talks_about_the_baseline_is_out(self, tmp_path):
        """NEGATIVE, AC-4. Prose about the design is not a read of it, and a set that grew
        on every mention would drift back into the five minutes it replaced."""
        root = _tree(tmp_path, {"test_a.py": "# this test is unrelated to gates.json\nx = 1\n"})
        assert lane.ratchet_tests(root) == []

    def test_a_module_that_does_not_reach_the_baseline_does_not_pull_its_importers_in(
        self, tmp_path
    ):
        root = _tree(tmp_path, {"test_a.py": "import helper\n"}, {"helper.py": "x = 1\n"})
        assert lane.ratchet_tests(root) == []

    @pytest.mark.parametrize("name", ["helper.py", "conftest.py", "a_test.py"])
    def test_a_file_that_is_not_a_test_module_is_out(self, name, tmp_path):
        root = _tree(tmp_path, {name: 'p = "gates.json"\n'})
        assert lane.ratchet_tests(root) == []


class TestAnEmptySetIsRefusedNotReportedGreen:
    def test_a_tree_with_no_ratchet_test_refuses(self, tmp_path):
        """NEGATIVE, AC-3. Nothing ran, so there is nothing to say about the ratchets;
        printing a green there would be the report of a check that never happened."""
        _tree(tmp_path, {"test_a.py": "x = 1\n"})
        with pytest.raises(lane.NoRatchetTests) as exc:
            lane.run(tmp_path, runner=lambda *a, **k: None)
        assert "nothing to run" in str(exc.value)
        assert "neither is a green" in str(exc.value)

    def test_a_tree_without_a_tests_directory_refuses_too(self, tmp_path):
        with pytest.raises(lane.NoRatchetTests):
            lane.run(tmp_path, runner=lambda *a, **k: None)


class TestTheRunSaysWhatItIsAndIsNot:
    def test_it_passes_pytest_the_derived_files_and_returns_its_code(self, tmp_path, capsys):
        root = _tree(tmp_path, {"test_a.py": 'p = "gates.json"\n'})
        seen: list = []

        def runner(argv, **kw):
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 3)

        assert lane.run(root, runner=runner) == 3, "pytest's verdict is passed through"
        assert seen[0][-1] == "tests/test_a.py"
        assert "-m" in seen[0] and "pytest" in seen[0]

    def test_it_says_out_loud_that_it_is_not_the_full_lane(self, tmp_path, capsys):
        """AC-5. A fast green that reads like a complete one is worse than no fast green:
        it is the sentence someone quotes when the release turns out untested."""
        root = _tree(tmp_path, {"test_a.py": 'p = "gates.json"\n'})
        lane.run(root, runner=lambda *a, **k: subprocess.CompletedProcess(a, 0))
        out = capsys.readouterr().out
        assert "NOT the full lane" in out
        assert "1 file(s)" in out, "it names how many it took"


class TestTheLiveTreeIsCovered:
    def test_every_ratchet_in_the_baseline_has_a_test_in_the_set(self):
        """The set is only worth running while it reaches every ratchet. This compares the
        two directly rather than trusting that the derivation happened to be enough."""
        import json

        node = json.loads((_REPO / "tausik" / "gates.json").read_text(encoding="utf-8"))
        keys = {k for k in node if not k.startswith("_")}
        text = "".join(
            (_REPO / rel).read_text(encoding="utf-8", errors="replace")
            for rel in lane.ratchet_tests(_REPO)
        )
        missing = sorted(k for k in keys if k not in text)
        assert not missing, (
            f"no test in the fast set names these ratchets: {missing}. The set would report "
            "green over a ratchet nobody checked."
        )
