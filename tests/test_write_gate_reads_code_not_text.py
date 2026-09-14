"""The write gate reads Python as CODE, not as text.

`write-gate-reads-open-literals-out-of-strings-and-comments`. Found in #203
when the gate refused its own measurement harness on the strength of string
literals it wrote nowhere, and again on a file whose only `open(` stood in a
comment. Measured in #207 over the repository's 878 Python files: the text
reading named a target in six, and all six were phantoms — there is not one
executed literal `open(..., "w")` in the tree, and the gate was blocking on
the six that are quoted, documented or commented out.

The table below is a table of FORMS, not of examples (memory #535): for each
place a literal can stand and each way a call can be spelt, one row, each row
driven through BOTH substrates — the script file and the `-c` payload — by
the real parser entry `write_targets`, not only through the detector.
"""

from __future__ import annotations

import os
import shlex
import sys

import pytest

_HOOKS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "hooks"
)
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

import python_invocation as PI  # noqa: E402
import python_source_writes as PSW  # noqa: E402
from bash_write_parse import write_targets  # noqa: E402

T = "harness/target.py"

# (label, source, expected targets). Every row is a FORM.
FORMS: list[tuple[str, str, list[str]]] = [
    # --- text that is not code: never a target -----------------------------
    ("comment", f'# fixture: open("{T}", "w")\n', []),
    ("commented-out code", f'x = 1\n# open("{T}", "w")\n', []),
    ("docstring", f'"""open("{T}", "w") is what this tests."""\n', []),
    ("string literal", f'PAYLOAD = \'open("{T}", "w")\'\n', []),
    ("f-string body", f'msg = f"""open("{T}", "w")"""\n', []),
    # --- calls that do not write: never a target ----------------------------
    ("read mode", f'open("{T}")\n', []),
    ("explicit read mode", f'open("{T}", "rb")\n', []),
    ("computed path (name)", f'p = "{T}"\nopen(p, "w")\n', []),
    ("computed path (f-string)", 'd = "harness"\nopen(f"{d}/target.py", "w")\n', []),
    ("computed path (concat)", 'open("harness/" + "target.py", "w")\n', []),
    ("mode is not a literal", f'm = "w"\nopen("{T}", m)\n', []),
    ("os.open takes flags", f'import os\nos.open("{T}", os.O_WRONLY)\n', []),
    ("Path read", f'from pathlib import Path\nPath("{T}").read_text()\n', []),
    ("Path open read", f'from pathlib import Path\nPath("{T}").open()\n', []),
    # --- calls that write: always a target ----------------------------------
    ("bare open", f'open("{T}", "w")\n', [T]),
    ("append mode", f'open("{T}", "a")\n', [T]),
    ("exclusive-create mode", f'open("{T}", "x")\n', [T]),
    ("update mode r+", f'open("{T}", "r+")\n', [T]),
    ("binary write", f'open("{T}", "wb")\n', [T]),
    ("keyword mode", f'open("{T}", mode="w")\n', [T]),
    ("keyword file and mode", f'open(file="{T}", mode="w")\n', [T]),
    ("raw string path", f'open(r"{T}", "w")\n', [T]),
    ("implicit concatenation", 'open("harness/" "target.py", "w")\n', [T]),
    ("attribute io.open", f'import io\nio.open("{T}", "w")\n', [T]),
    ("attribute codecs.open", f'import codecs\ncodecs.open("{T}", "w", "utf-8")\n', [T]),
    ("inside def", f'def f():\n    open("{T}", "w")\n', [T]),
    ("inside with", f'with open("{T}", "w") as fh:\n    fh.write("x")\n', [T]),
    ("inside class body", f'class C:\n    fh = open("{T}", "w")\n', [T]),
    ("as an argument", f'print("x", file=open("{T}", "w"))\n', [T]),
    ("Path write_text", f'from pathlib import Path\nPath("{T}").write_text("x")\n', [T]),
    ("pathlib Path write_bytes", f'import pathlib\npathlib.Path("{T}").write_bytes(b"x")\n', [T]),
    ("Path open write", f'from pathlib import Path\nPath("{T}").open("w")\n', [T]),
    ("Path bound literal", f'from pathlib import Path\np = "{T}"\nPath(p).write_text("x")\n', [T]),
    ("Path unlink", f'from pathlib import Path\nPath("{T}").unlink()\n', [T]),
    ("Path mkdir", f'from pathlib import Path\nPath("{T}").mkdir()\n', [T]),
    ("Path rename both paths", f'from pathlib import Path\nPath("old.py").rename("{T}")\n', ["old.py", T]),
    ("shutil copy destination", f'import shutil\nshutil.copy("source.py", "{T}")\n', [T]),
    ("shutil move destination", f'import shutil\nshutil.move("source.py", dst="{T}")\n', [T]),
    ("os replace both paths", f'import os\nos.replace("old.py", "{T}")\n', ["old.py", T]),
    (
        "real write next to a quoted one",
        f'note = \'open("other.py", "w")\'\nopen("{T}", "w")\n',
        [T],
    ),
]


@pytest.mark.parametrize("label,source,expected", FORMS, ids=[f[0] for f in FORMS])
def test_detector_reads_code_not_text(label, source, expected):
    assert PSW.writes_in_source(source) == expected


@pytest.mark.parametrize("label,source,expected", FORMS, ids=[f[0] for f in FORMS])
def test_script_file_substrate_through_the_real_parser(label, source, expected, tmp_path):
    script = tmp_path / "helper.py"
    script.write_text(source, encoding="utf-8")
    assert write_targets(f"python {shlex.quote(str(script))}", str(tmp_path)) == expected


@pytest.mark.parametrize("label,source,expected", FORMS, ids=[f[0] for f in FORMS])
def test_inline_c_substrate_through_the_real_parser(label, source, expected):
    assert write_targets(f"python -c {shlex.quote(source)}") == expected


class TestInlineCodeIsTheCodeAndOnlyTheCode:
    """`-c CODE`: the code is read, the arguments after it are not."""

    @pytest.mark.parametrize(
        "cmd",
        [
            'python -c \'open("harness/x.py", "w")\'',
            'python -c\'open("harness/x.py", "w")\'',  # glued to the flag
            'python -uc \'open("harness/x.py", "w")\'',  # end of a cluster
            'python -X utf8 -c \'open("harness/x.py", "w")\'',  # after a valued option
            'python -W ignore -c \'open("harness/x.py", "w")\'',
            'python -Wignore -c \'open("harness/x.py", "w")\'',
            'python3.11 -I -c \'open("harness/x.py", "w")\'',
            'python -c \'open("harness/x.py", "w")\' data.txt',  # argv after the code
        ],
    )
    def test_every_spelling_of_c_is_read(self, cmd):
        assert write_targets(cmd) == ["harness/x.py"]

    @pytest.mark.parametrize(
        "cmd",
        [
            # Data arguments carrying a literal are DATA: the gate used to name
            # every one of these as a write the command does not perform.
            "python -m pytest -k \"open('harness/x.py','w')\"",
            "python script.py \"open('harness/x.py','w')\"",
            "python -c 'print(1)' \"open('harness/x.py','w')\"",
            'python -c \'# open("harness/x.py", "w")\'',  # a comment, inline
            "python -m foo -c \"open('harness/x.py','w')\"",  # -m first: no inline code
        ],
    )
    def test_data_arguments_are_not_read_as_code(self, cmd):
        assert write_targets(cmd) == []

    def test_a_non_python_interpreter_keeps_the_text_reading(self):
        """The one reader left on text: a substrate this parser cannot read,
        where over-detecting is the declared direction."""
        assert write_targets('ruby -e \'File.open("harness/x.py", "w")\'') == ["harness/x.py"]
        assert write_targets('xargs python -c \'open("harness/x.py", "w")\'') == ["harness/x.py"]

    def test_python_inline_code_positions(self):
        assert PI.python_inline_code(["-c", "print(1)"]) == "print(1)"
        assert PI.python_inline_code(["-cprint(1)"]) == "print(1)"
        assert PI.python_inline_code(["-uc", "print(1)"]) == "print(1)"
        assert PI.python_inline_code(["-W", "ignore", "-c", "print(1)"]) == "print(1)"
        assert PI.python_inline_code(["-m", "mod", "-c", "print(1)"]) is None
        assert PI.python_inline_code(["script.py", "-c", "print(1)"]) is None
        assert PI.python_inline_code(["-c"]) is None
        assert PI.python_inline_code([]) is None
        # The two walks agree about where the options stop.
        assert PI.python_script(["-c", "x.py"]) is None
        assert PI.python_script(["-W", "ignore", "x.py"]) == "x.py"


class TestDegradationIsDeclaredNotSilent:
    """A source the parser cannot read falls back to the text reading."""

    def test_syntax_error_falls_back_to_the_text_reading(self):
        # Python-2 print statement: does not parse, but a literal write stands
        # in it and another interpreter might run it.
        src = 'print "x"\nopen("harness/x.py", "w")\n'
        assert PSW.writes_in_source(src) == ["harness/x.py"]

    def test_syntax_error_fallback_keeps_the_text_readings_phantom_and_says_so(self):
        # The confinement is real: the phantom exists ONLY here, and this row
        # is what makes the docstring's sentence checkable.
        src = 'print "x"\n# open("harness/x.py", "w")\n'
        assert PSW.writes_in_source(src) == ["harness/x.py"]
        assert PSW.writes_in_text(src) == ["harness/x.py"]

    def test_nul_byte_falls_back_to_the_text_reading(self):
        src = 'open("harness/x.py", "w")\x00\n'
        assert PSW.writes_in_source(src) == ["harness/x.py"]

    def test_deep_nesting_falls_back_rather_than_raising(self):
        src = "x = " + "(" * 5000 + "1" + ")" * 5000 + '\nopen("harness/x.py", "w")\n'
        assert PSW.writes_in_source(src) == ["harness/x.py"]

    def test_oversized_script_is_still_not_read(self, tmp_path, monkeypatch):
        big = tmp_path / "big.py"
        big.write_text(
            'open("harness/x.py", "w")\n' + ("# pad\n" * (PSW.MAX_SCRIPT_BYTES // 6 + 1)),
            encoding="utf-8",
        )
        assert big.stat().st_size > PSW.MAX_SCRIPT_BYTES
        assert PSW.writes_in_script_file(["python", str(big)], str(tmp_path)) == []


def test_the_repository_itself_yields_no_phantom():
    """The #207 measurement, kept as a test: the text reading names targets in
    this tree, the code reading names none — every one of them is a phantom.
    Reads the tree, so the visibility ratchet is told (CROSSCUTTING_SCOPE)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    phantom_files = 0
    text_hit_files = 0
    for dirpath, _dirs, files in os.walk(os.path.join(root, "tests")):
        if "__pycache__" in dirpath:
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            if PSW.writes_in_text(body):
                text_hit_files += 1
                if not PSW.writes_in_source(body):
                    phantom_files += 1
    assert text_hit_files >= 1, (
        "the measurement lost its subject: no test file quotes a literal open"
    )
    assert phantom_files == text_hit_files


CROSSCUTTING_SCOPE = ["tests/"]
