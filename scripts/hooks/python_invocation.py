#!/usr/bin/env python3
"""What a `python …` command line actually RUNS — names and argument positions.

Split out of `bash_write_parse` for the filesize gate, following the cut that
module already made twice (`bash_cmd_norm`, `write_confidence`). The unit is
cohesive on its own terms: everything here answers "is this the Python
interpreter, and which file is it about to execute", with no knowledge of write
targets, ACLs or hooks.

Both answers were measured wrong once, in the same way — a form was closed
because it had been measured, and the neighbouring spellings of the same command
were left open. Session #203 drove 17 ordinary spellings through the real hook:
10 walked past BOTH of the write gate's rules, and 2 produced a false block. The
constants below are therefore rules about the SHAPE of a name or a flag, not
enumerations of the spellings someone happened to think of.
"""

from __future__ import annotations

import re

#: Suffixes that make a positional argument a Python script we are willing to
#: read. Python only, and that is a competence boundary rather than a taste:
#: the caller's `open()` matcher reads Python, so claiming to read a script
#: means claiming to read a PYTHON one.
SCRIPT_SUFFIXES = (".py",)

# Every ordinary spelling of "the Python interpreter", DERIVED from a rule
# rather than listed. A literal set is what brought this code back for a second
# visit: it held python/python2/python3/py, and `python3.11` — the standard way
# to name a specific interpreter on most systems — walked straight past it, as
# did `pythonw` and `py -3`. An enumeration silently stops being true the day
# someone types the next name; a rule about the shape of the name does not.
_PYTHON_NAME_RE = re.compile(r"^(?:python|pythonw)\d*(?:\.\d+)?$|^pyw?$")

# Short interpreter options whose value is a SEPARATE token when it is not
# glued on (`-W ignore`, `-Wignore`). Skipping the value matters for finding the
# right file: without it `python -W ignore helper.py` stops at `ignore`.
_PY_VALUE_OPTS = frozenset("QWX")

# Short options after which there is NO script file: the rest of the line
# belongs to a module or to inline code. Held as LETTERS, not as the exact
# tokens `-m`/`-c`, because the interpreter accepts the glued (`-mpytest`) and
# clustered (`-um`) spellings too — and an exact-token set false-BLOCKED both,
# reading a test file the command never writes. Refusing a script here is what
# keeps `python -m pytest tests/test_x.py` allowed, whose target file is full of
# literal open(..., "w") calls that THIS command does not perform.
_PY_NO_SCRIPT_OPTS = frozenset("cm")


def is_python(base: str) -> bool:
    """True when `base` names the Python interpreter.

    `base` is expected already lowercased with any `.exe` stripped — the same
    normalisation the caller does to identify any other program.
    """
    return bool(_PYTHON_NAME_RE.match(base))


def python_script(args: list[str]) -> str | None:
    """The script file that `python [options] script.py [args]` runs, or None.

    POSITION IS THE WHOLE POINT, and it is what the first version of this rule
    missed. Python stops reading its own options at the first non-option, so
    `-m` BEFORE the script means "there is no script file", while the same `-m`
    AFTER it is an argument to the SCRIPT and says nothing about the
    interpreter. Scanning the entire argument list for `-m`/`-c` therefore let
    `python helper.py -m foo` disarm the write gate — measured through the real
    hook — and `-c` is an everyday flag of an ordinary program, so this took no
    obfuscation and no ill intent to happen.

    The script is the FIRST positional, not the first argument that happens to
    end in `.py`: an extensionless entry point is ordinary (this repository's
    own CLI is one), and reading the `.py` file passed to it as an argument
    names writes the command never makes.
    """
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":  # end of options — the next token is the script
            i += 1
            break
        if a.startswith("--"):
            if a == "--check-hash-based-pycs":
                i += 1  # its value is a separate token
            i += 1
            continue
        if a.startswith("-") and len(a) > 1:
            # A short-option token may be a CLUSTER (`-um` is `-u -m`), and the
            # launcher's version selector (`py -3.11`) arrives in this shape
            # too. Walk the letters rather than matching the whole token.
            for pos, ch in enumerate(a[1:], start=1):
                if ch in _PY_NO_SCRIPT_OPTS:
                    return None
                if ch in _PY_VALUE_OPTS:
                    if pos == len(a) - 1:
                        i += 1  # the value is the next token, not glued on
                    break
            i += 1
            continue
        break  # first positional: this is the script, if it is one at all
    if i >= len(args):
        return None
    script = args[i]
    return script if script.lower().endswith(SCRIPT_SUFFIXES) else None
