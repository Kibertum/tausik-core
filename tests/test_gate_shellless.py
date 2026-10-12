"""v15p-shell-true-hardening: gate commands run without a shell.

The runner used to fall back to `shell=True` for any command containing a
pipe / `&&` / redirect. Custom-stack command templates are attacker-
controllable, so that was a command-injection vector. These tests pin the
shell-less behaviour: `&&` and `|` still work, but `;`, `$(...)`, backticks
and other shell metacharacters are refused and never executed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gate_command_runner import (  # noqa: E402
    _run_shellless,
    _tokenize_command,
    run_command_gate,
)

PY = sys.executable.replace("\\", "/")


class TestTokenizeSurfacesOperators:
    def test_double_amp_is_token(self):
        assert "&&" in _tokenize_command("a -x && b")

    def test_pipe_is_token(self):
        assert "|" in _tokenize_command("a | b")

    def test_semicolon_is_token(self):
        assert ";" in _tokenize_command("ruff x ; rm -rf ~")

    def test_quoted_operator_stays_literal(self):
        # A pipe inside quotes is an arg, not an operator.
        assert _tokenize_command("grep 'a|b' file") == ["grep", "a|b", "file"]


class TestRejectsInjection:
    def _gate(self, sentinel: Path) -> dict:
        s = str(sentinel).replace("\\", "/")
        return {
            "command": f'"{PY}" -c "print(1)" ; "{PY}" -c "open(\'{s}\',\'w\')"',
            "timeout": 30,
        }

    def test_semicolon_chain_fails_safely(self, tmp_path):
        sentinel = tmp_path / "pwned.txt"
        passed, output = run_command_gate(self._gate(sentinel), [])
        assert not passed
        assert "unsupported shell operator" in output
        assert not sentinel.exists(), "injected tail must not execute"

    def test_command_substitution_rejected(self, tmp_path):
        sentinel = tmp_path / "subst.txt"
        s = str(sentinel).replace("\\", "/")
        gate = {
            "command": f"\"{PY}\" -c \"open('{s}','w')\" $(whoami)",
            "timeout": 30,
        }
        passed, output = run_command_gate(gate, [])
        # `(` / `)` surface as operators and are refused before anything runs.
        assert not passed
        assert "unsupported shell operator" in output
        assert not sentinel.exists()

    def test_redirect_append_rejected(self):
        passed, output = run_command_gate(
            {"command": f'"{PY}" -c "print(1)" >> out.txt', "timeout": 30}, []
        )
        assert not passed
        assert "unsupported shell operator" in output


class TestSupportedOperatorsStillWork:
    def test_single_command_runs(self):
        rc, out = _run_shellless(f'"{PY}" -c "print(42)"', 30)
        assert rc == 0
        assert "42" in out

    def test_sequential_and_runs_both(self):
        rc, out = _run_shellless(
            f'"{PY}" -c "print(\'first\')" && "{PY}" -c "print(\'second\')"', 30
        )
        assert rc == 0
        assert "first" in out and "second" in out

    def test_sequential_and_short_circuits(self):
        # First fails -> second must not run.
        rc, out = _run_shellless(
            f'"{PY}" -c "import sys; sys.exit(3)" && "{PY}" -c "print(\'NOPE\')"', 30
        )
        assert rc == 3
        assert "NOPE" not in out

    def test_stderr_is_merged(self):
        rc, out = _run_shellless(f'"{PY}" -c "import sys; sys.stderr.write(\'errline\')"', 30)
        assert rc == 0
        assert "errline" in out

    def test_real_pipe_chains(self):
        rc, out = _run_shellless(
            f'"{PY}" -c "print(\'hello\')" | "{PY}" -c "import sys; print(sys.stdin.read().upper())"',
            30,
        )
        assert rc == 0
        assert "HELLO" in out

    def test_terraform_shape_compound(self):
        # The one real stack command that survives truncation-strip with `&&`.
        rc, out = _run_shellless(
            f'"{PY}" -c "print(\'fmt-ok\')" && "{PY}" -c "print(\'validate-ok\')"', 30
        )
        assert rc == 0
        assert "fmt-ok" in out and "validate-ok" in out
