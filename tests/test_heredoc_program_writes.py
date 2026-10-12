"""A heredoc fed to Python is a program, and its writes are seen
(heredoc, github#162).

Measured in session #267 over this project's own transcripts: 1,085 heredoc
bodies handed to an interpreter wrote a file, and the write gate saw no target
in 917 of them. The shapes that hid the write, each fixed and pinned here: a
path bound to a name, a path passed to a helper's parameter, a loop over a
literal list, `Path(...)` bound to a name, a header that starts with `cd x;` or
`VAR=1`, and a pipe after `<<EOF`. After the fix: 74 remain, all of them paths
built in shell variables or loops over names — the boundary the gate names.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts", "hooks"))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from bash_write_parse import write_targets  # noqa: E402

T = "scripts/target.py"


def _py(body: str, header: str = "python - <<'EOF'") -> str:
    return f"{header}\n{body}EOF"


@pytest.mark.parametrize(
    "body",
    [
        f'p = "{T}"\ns = open(p).read()\nopen(p, "w").write(s)\n',
        f'def rep(p, a, b):\n    s = open(p).read()\n    open(p, "w").write(s.replace(a, b))\nrep("{T}", "x", "y")\n',
        f'def ins(path, text):\n    open(path, "a").write(text)\nins(path="{T}", text="z")\n',
        f'for p in ("{T}",):\n    open(p, "w").write("x")\n',
        f'for p, old in [("{T}", "a")]:\n    open(p, "w").write(old)\n',
        f'import pathlib\np = pathlib.Path("{T}")\np.write_text("x")\n',
    ],
    ids=["bound-name", "helper-positional", "helper-keyword", "loop", "tuple-loop", "path-bound"],
)
def test_the_write_inside_the_program_is_a_target(body):
    assert T in write_targets(_py(body))


@pytest.mark.parametrize(
    "header",
    [
        "cd /d/x; python - <<'EOF'",
        "cd /d/x && PYTHONUTF8=1 python - <<'EOF'",
        ".tausik/venv/Scripts/python.exe - <<'EOF' 2>&1 | tail -5",
    ],
    ids=["after-cd", "env-prefix", "pipe-after"],
)
def test_the_header_is_read_at_the_statement_that_takes_the_heredoc(header):
    assert T in write_targets(_py(f'open("{T}", "w")\n', header))


@pytest.mark.parametrize(
    "cmd",
    [
        f'git commit -F - <<\'EOF\'\nfix: open("{T}", "w") no longer phantom\nEOF',
        f'cat > notes.md <<\'EOF\'\np = "{T}"\nopen(p, "w")\nEOF',
        f"sqlite3 app.db <<'EOF'\nSELECT 'open(\"{T}\", \"w\")';\nEOF",
    ],
    ids=["commit-message", "notes-file", "sql-script"],
)
def test_a_heredoc_not_fed_to_an_interpreter_is_not_read_as_a_program(cmd):
    assert T not in write_targets(cmd)


def test_a_helper_that_only_reads_its_parameter_names_nothing():
    body = f'def show(p):\n    print(open(p).read())\nshow("{T}")\n'
    assert T not in write_targets(_py(body))
