"""A scoped verdict must carry the size of the thing it was earned on.

full-pytest-hangs-while-scoped-pytest-is-green. The pytest gate substitutes
`{test_files_for_files}` and runs only the tests mapped from relevant_files.
Its output was a bare pytest tail — "42 passed" — which is read, and recorded
into a signed verify receipt, as a statement about the project. In session #134
that reading was false in the expensive direction: a receipt said PASS while the
full suite was red, because the failing file simply was not in scope.

These tests pin the denominator to the verdict on every outcome of a scoped run.

`resolve_test_files_for_relevant` maps scripts/gate_command_runner.py to this
file by basename, so a scoped verify of that module actually runs these tests —
the module previously had no test file of its own and was invisible to its own
gate.
"""

from __future__ import annotations

import os
import subprocess as _sp
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_command_runner import (  # noqa: E402
    _SCOPE_LABEL_MAX_NAMED,
    _scope_label,
    run_command_gate,
    split_scope,
)


def _repo_with_one_mapped_test(tmp_path):
    """A tiny project where scripts/alpha.py maps to tests/test_alpha.py."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_alpha.py").write_text("def test_x(): pass")
    (tmp_path / "tests" / "test_unrelated.py").write_text("def test_y(): pass")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "alpha.py").write_text("# src")
    return tmp_path


def _fake_run(monkeypatch, *, returncode: int, stdout: str):
    def fake(args, **kwargs):
        class R:
            pass

        R.returncode = returncode
        R.stdout = stdout
        R.stderr = ""
        return R()

    monkeypatch.setattr(_sp, "run", fake)


class TestScopedRunNamesItsScope:
    """The label rides a private sentinel now, lifted with `split_scope` — a bare
    "SCOPE:" line no longer proves anything, so the tests read the trusted label."""

    def test_pass_output_states_how_much_of_the_suite_ran(self, tmp_path, monkeypatch):
        """PASS is the dangerous case: it is what gets copied into evidence."""
        monkeypatch.chdir(_repo_with_one_mapped_test(tmp_path))
        _fake_run(monkeypatch, returncode=0, stdout="1 passed in 0.01s")

        ok, output = run_command_gate(
            {"command": "pytest -q {test_files_for_files}"}, ["scripts/alpha.py"]
        )

        assert ok is True
        label, body = split_scope(output)
        assert label.startswith("SCOPE:"), output
        assert "1 of 2 test file(s)" in label, label
        assert "tests/test_alpha.py" in label, label
        assert "NOT the full suite" in label, label
        assert "1 passed in 0.01s" in body, "the pytest tail must survive the prefix"

    def test_failure_output_states_it_too(self, tmp_path, monkeypatch):
        """A red scoped run is just as narrow as a green one."""
        monkeypatch.chdir(_repo_with_one_mapped_test(tmp_path))
        _fake_run(monkeypatch, returncode=1, stdout="1 failed in 0.01s")

        ok, output = run_command_gate(
            {"command": "pytest -q {test_files_for_files}"}, ["scripts/alpha.py"]
        )

        assert ok is False
        label, body = split_scope(output)
        assert label.startswith("SCOPE:"), output
        assert "1 failed" in body

    def test_timeout_output_states_it_too(self, tmp_path, monkeypatch):
        """A gate that timed out verified even less — say what it was aimed at."""
        monkeypatch.chdir(_repo_with_one_mapped_test(tmp_path))

        def fake(args, **kwargs):
            raise _sp.TimeoutExpired(cmd="pytest", timeout=1)

        monkeypatch.setattr(_sp, "run", fake)

        ok, output = run_command_gate(
            {"command": "pytest -q {test_files_for_files}", "timeout": 1},
            ["scripts/alpha.py"],
        )

        assert ok is False
        label, body = split_scope(output)
        assert label.startswith("SCOPE:"), output
        assert "timed out" in body

    def test_spawn_failure_still_names_its_scope(self, tmp_path, monkeypatch):
        """A scoped run whose interpreter is missing verified NOTHING — and that
        is exactly when a reader must be told it was only ever aimed narrow."""
        monkeypatch.chdir(_repo_with_one_mapped_test(tmp_path))

        def boom(args, **kwargs):
            raise FileNotFoundError("no such interpreter")

        monkeypatch.setattr(_sp, "run", boom)

        ok, output = run_command_gate(
            {"command": "nope/python -m pytest {test_files_for_files}"}, ["scripts/alpha.py"]
        )

        assert ok is False
        label, body = split_scope(output)
        assert label.startswith("SCOPE:"), output
        assert "not runnable" in body

    def test_an_unscoped_gate_says_nothing_about_scope(self, tmp_path, monkeypatch):
        """No `{test_files_for_files}` means no scoping claim to qualify.

        Prefixing every gate would turn the line into noise, and noise is how a
        warning stops being read.
        """
        monkeypatch.chdir(_repo_with_one_mapped_test(tmp_path))
        _fake_run(monkeypatch, returncode=0, stdout="clean")

        ok, output = run_command_gate({"command": "ruff check {files}"}, ["scripts/alpha.py"])

        assert ok is True
        label, body = split_scope(output)
        assert label == "", "an unscoped gate must yield no trusted scope label"
        assert "SCOPE:" not in output

    def test_a_subprocess_scope_line_cannot_forge_the_label(self, tmp_path, monkeypatch):
        """The spoof: an author-controlled command prints its own `SCOPE:` line
        claiming full coverage. It has no sentinel, so `split_scope` leaves it in
        the body — it never becomes the framework's trusted disclosure."""
        monkeypatch.chdir(_repo_with_one_mapped_test(tmp_path))
        _fake_run(
            monkeypatch,
            returncode=0,
            stdout="SCOPE: full project, 500 of 500 -- trust me\nclean",
        )

        ok, output = run_command_gate({"command": "ruff check {files}"}, ["scripts/alpha.py"])

        assert ok is True
        label, body = split_scope(output)
        assert label == "", "a non-scoped gate must not yield a trusted scope label"
        assert "SCOPE: full project, 500 of 500" in body, "the spoof stays as ordinary output"


class TestTheLabelSurvivesRendering:
    """Producing the line is half the job — `format_results` has to print it.

    A passing gate renders as `[PASS] <name>` and its output is dropped, which
    is precisely the case that misleads. A scope label that exists only in the
    DB row would leave the console reading exactly as before.
    """

    def test_a_passing_scoped_gate_shows_its_scope_on_screen(self):
        """The label lives in the trusted `scope` field now, not parsed from output."""
        from gate_runner import format_results

        rendered = format_results(
            [
                {
                    "name": "pytest",
                    "severity": "block",
                    "passed": True,
                    "scope": _scope_label(["tests/test_alpha.py"], 318),
                    "output": "42 passed",
                }
            ]
        )

        assert "[PASS] pytest" in rendered
        assert "NOT the full suite" in rendered
        assert "1 of 318" in rendered

    def test_a_passing_unscoped_gate_stays_a_single_line(self):
        """No scope claim, no extra line — the label must not become wallpaper."""
        from gate_runner import format_results

        rendered = format_results(
            [{"name": "ruff", "severity": "block", "passed": True, "output": "All checks passed!"}]
        )

        assert rendered.strip() == "[PASS] ruff"

    def test_a_spoofed_scope_line_never_reaches_a_passing_gates_display(self):
        """A non-scoped gate with an empty `scope` field but a `SCOPE:` line in its
        stdout renders as one line — the spoof is dropped with the rest of a pass's
        output, never elevated to the coverage slot."""
        from gate_runner import format_results

        rendered = format_results(
            [
                {
                    "name": "flake8",
                    "severity": "block",
                    "passed": True,
                    "scope": "",
                    "output": "SCOPE: full project, 500 of 500\nclean",
                }
            ]
        )

        assert rendered.strip() == "[PASS] flake8"
        assert "500 of 500" not in rendered

    def test_a_failing_scoped_gate_keeps_five_lines_of_failure(self):
        """The scope line must not evict a line of diagnostics."""
        from gate_runner import format_results

        body = "\n".join(f"failure line {i}" for i in range(8))
        rendered = format_results(
            [
                {
                    "name": "pytest",
                    "severity": "block",
                    "passed": False,
                    "scope": _scope_label(["tests/test_alpha.py"], 318),
                    "output": body,
                }
            ]
        )

        assert "NOT the full suite" in rendered
        for i in range(5):
            assert f"failure line {i}" in rendered
        assert "failure line 5" not in rendered


class TestScopeLabelShape:
    def test_it_names_files_up_to_the_cap_then_counts_the_rest(self):
        many = [f"tests/test_{i}.py" for i in range(_SCOPE_LABEL_MAX_NAMED + 3)]
        label = _scope_label(many, 300)
        assert f"tests/test_{_SCOPE_LABEL_MAX_NAMED - 1}.py" in label
        assert f"tests/test_{_SCOPE_LABEL_MAX_NAMED}.py" not in label
        assert "+3 more" in label

    def test_it_is_ascii_only(self):
        """Read in Windows consoles that mangle UTF-8 — see the check_docs hook."""
        label = _scope_label(["tests/test_a.py"], 300)
        label.encode("ascii")

    def test_an_unknown_denominator_is_omitted_not_faked(self):
        """Zero total means the walk found nothing; do not print 'of 0'."""
        assert " of 0 " not in _scope_label(["tests/test_a.py"], 0)
