r"""Which paths a piece of PYTHON SOURCE literally opens for writing.

One question, two substrates. The source can arrive inline in the command
(`python -c "open('x','w')"`) or on disk in a script the command names
(`python helper.py`). Those were caught at different times and for different
reasons — the inline form from the start, the file form only in session #200,
after `cp x .claude/…` was refused with the ACL printed while `python helper.py`
writing that same path returned zero and made the edit. The documented residual
had named the wrong cut, "a computed path, not a literal open()", when the real
one was INLINE versus IN A FILE, and running a script from a file is the
ordinary way to run code rather than obfuscation.

Extracted from `bash_write_parse` for the filesize gate, the way
`python_invocation`, `bash_cmd_norm` and `write_confidence` already were — and
the split lands on a real seam: everything here reads PYTHON, while everything
left behind reads a SHELL command line.

PYTHON ONLY, and that is a competence boundary rather than a preference. The
expression below reads Python; a shell script's redirections and a Node
script's `fs.writeFileSync` are the same defect on substrates it cannot read,
and they stay in the residual (see `docs/ru/enforcement-coverage.md`).
"""

from __future__ import annotations

import ast
import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from python_invocation import is_python as _is_python  # noqa: E402
from python_invocation import python_inline_code as _python_inline_code  # noqa: E402
from python_invocation import python_script as _python_script  # noqa: E402

#: The TEXT reading of a literal `open(path, 'w'|'a'|'x')`. It does not know a
#: string from a call, so a literal sitting in a docstring or a comment is
#: reported as a write nothing performs. Measured in #207 over this repository's
#: own 878 Python files: it named a target in six, and all six were phantoms —
#: the last of them the example that used to sit in this very comment.
#:
#: It is kept for two readers that have nothing better. `writes_in_source`
#: falls back to it when the source does not parse, because a source this
#: parser cannot read might still run under another interpreter, and reporting
#: nothing there would turn "could not check" into "checked and clean". And
#: `writes_in_text` reads command text for interpreters that are NOT Python
#: (a Ruby `File.open("x", "w")`), where an approximation is the only reading
#: on offer and over-detecting is the declared direction.
OPEN_RE = re.compile(
    r"""open\(\s*['"]([^'"]+)['"]\s*,\s*['"][^'"]*[wax]""",
    re.IGNORECASE,
)

#: A script larger than this is not read. A PreToolUse hook pays this cost on
#: every Bash command, and no ordinary helper is this size. Parsing sits under
#: the same cap: measured at 1.9 ms per file over the repository, 10 ms for its
#: largest test module — so a file at the cap costs tens of milliseconds, once.
MAX_SCRIPT_BYTES = 256 * 1024

#: A mode string containing any of these opens the file for WRITING. `+` is
#: here on purpose: `r+` is an update mode and the text reading missed it.
_WRITE_MODE_CHARS = frozenset("wax+")


def _constant_str(node: ast.expr | None) -> str | None:
    """The value of a string (or bytes) literal node, else None.

    A raw string, an implicit concatenation (`"a" "b"`) and a parenthesised
    literal all arrive as one `Constant` — the parser has already done what the
    text reading could not. An f-string, a name, a concatenation with `+` are
    NOT constants, and a path built from them is the declared residual.
    """
    if not isinstance(node, ast.Constant):
        return None
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        return node.value.decode("utf-8", errors="replace")
    return None


def _open_call_target(call: ast.Call) -> str | None:
    """The literal path an `open(...)` CALL writes, else None.

    FORMS, not examples (the distinction this project keeps paying for):
    the callee is the bare name `open` or any attribute spelt `open`
    (`io.open`, `codecs.open`, `builtins.open`); the path is the first
    positional or the keyword `file=`; the mode is the second positional or
    the keyword `mode=`. A missing mode is a read. A mode that is not a
    literal is unknown, and unknown is not reported — the same silence the
    text reading kept, chosen here on purpose rather than inherited.
    `os.open` takes integer flags, never a mode string, so it is never a hit;
    `Path(...).open("w")` carries no path argument, so neither is that.
    """
    func = call.func
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    else:
        return None
    if name != "open":
        return None
    path = _constant_str(call.args[0]) if call.args else None
    mode = _constant_str(call.args[1]) if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "file":
            path = _constant_str(kw.value)
        elif kw.arg == "mode":
            mode = _constant_str(kw.value)
    if not path or not mode or not (_WRITE_MODE_CHARS & set(mode)):
        return None
    return path


def writes_in_text(text: str) -> list[str]:
    """The TEXT reading — see `OPEN_RE` for the two callers that still need it."""
    return list(OPEN_RE.findall(text))


def writes_in_source(text: str) -> list[str]:
    """Literal write targets in a piece of Python source.

    Reads CODE, not text: the source is parsed and only real `open(...)` call
    nodes are consulted, so a literal inside a string, a docstring, a comment
    or a commented-out line is not a target by construction — there is no such
    node. The gate used to refuse this module's own test harness on the
    strength of a comment; a comment is never executed, under any condition.

    A source the parser cannot read (a syntax error, a NUL byte, nesting past
    the recursion limit) degrades to the text reading, NOT to silence. Such a
    file executes nothing under this interpreter, but it may well run under a
    newer one whose grammar this parser lacks, and "could not check" must
    never be reported as "checked and clean". The phantom that the text
    reading can produce is therefore confined to sources this parser does not
    read, and named here rather than discovered by whoever it stops.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return writes_in_text(text)
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = _open_call_target(node)
            if target is not None:
                out.append(target)
    return out


def writes_in_inline_code(sub: list[str]) -> list[str]:
    """Literal write targets in the `-c CODE` the command `sub` hands Python.

    The code, and ONLY the code. Everything after it on the line is the
    program's `sys.argv` — data the interpreter never executes — and reading
    the whole line as source is what made `python -m pytest -k "open('x','w')"`
    name a file the command does not write. `python_invocation` says which
    token is the code; this module says what the code writes.
    """
    if not sub:
        return []
    base = os.path.basename(sub[0]).lower().removesuffix(".exe")
    if not _is_python(base):
        return []
    code = _python_inline_code(sub[1:])
    if code is None:
        return []
    return writes_in_source(code)


def writes_in_script_file(sub: list[str], base_dir: str | None = None) -> list[str]:
    """Literal write targets inside the script file the command `sub` runs.

    Recognises `python [options] script.py [args]` — an interpreter named by
    `python_invocation.is_python` in command position, the script as the first
    positional. Narrow on purpose: claiming to read a script means claiming to
    read a PYTHON script, and every widening past that is a chance to name a
    file the command never writes.

    FAIL-SOFT BY DESIGN: an absent, unreadable or oversized file yields nothing
    rather than raising or guessing. This runs in a PreToolUse hook on every
    Bash command, and the cost of being wrong is asymmetric — a miss leaves the
    gate exactly where it already stood, while a false block on an everyday
    command stops the work, and a gate that stops the work is one an agent
    learns to switch off.
    """
    if not sub:
        return []
    base = os.path.basename(sub[0]).lower().removesuffix(".exe")
    if not _is_python(base):
        return []
    script = _python_script(sub[1:])
    if script is None:
        return []
    # The script path comes from the COMMAND, so it is relative to the shell's
    # cwd — the caller passes it. Falling back to the project dir keeps the old
    # behaviour when no caller supplied one. This was the FOURTH site of that
    # identification, missed by an inventory that grepped for the variable
    # names the other three happened to use.
    root = base_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # `~` first, or the tilde is joined to the root as a literal directory name
    # and the lookup misses a file that plainly exists. Fail-soft then reads as
    # "this script writes nothing", so `python ~/helper.py` was invisible while
    # the same script named absolutely was seen. Three of the five sites that
    # resolve an externally supplied path already expanded it; this was one of
    # the two that did not.
    script = os.path.expanduser(script)
    path = script if os.path.isabs(script) else os.path.join(root, script)
    try:
        if os.path.getsize(path) > MAX_SCRIPT_BYTES:
            return []
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError:
        return []
    return writes_in_source(body)
