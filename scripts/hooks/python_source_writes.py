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

import os
import re
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from python_invocation import is_python as _is_python  # noqa: E402
from python_invocation import python_script as _python_script  # noqa: E402

#: Best-effort catch for a literal `open(path, 'w'|'a'|'x')`. A computed path
#: (variable, concatenation) is the documented residual.
#:
#: It reads TEXT, not code, and that costs in the other direction too: a literal
#: sitting in a string, a docstring or a comment is reported as a write nothing
#: performs. Measured twice in #203, once on the write parser's own test
#: harness. Open as `write-gate-reads-open-literals-out-of-strings-and-comments`.
OPEN_RE = re.compile(
    r"""open\(\s*['"]([^'"]+)['"]\s*,\s*['"][^'"]*[wax]""",
    re.IGNORECASE,
)

#: A script larger than this is not read. A PreToolUse hook pays this cost on
#: every Bash command, and no ordinary helper is this size.
MAX_SCRIPT_BYTES = 256 * 1024


def writes_in_source(text: str) -> list[str]:
    """Literal write targets in a piece of Python source text."""
    return list(OPEN_RE.findall(text))


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
