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

#: One declared catalogue of the Python file-system mutations this reader
#: recognises.  It deliberately names AST shapes, not imported runtime objects:
#: resolving arbitrary aliases would require executing the source.  Every form
#: here is covered through both `python -c` and `python script.py` substrates.
RECOGNISED_PYTHON_WRITE_FORMS = (
    "open(path, write-mode)",
    "Path(path).write_text/write_bytes/open(write-mode)",
    "Path(path).unlink/mkdir/rename",
    "shutil.copy/move(..., destination)",
    "os.replace(source, destination)",
)
_PATH_MUTATING_METHODS = frozenset({"write_text", "write_bytes", "unlink", "mkdir"})
_PATH_OPEN_METHOD = "open"
_PATH_RENAME_METHOD = "rename"
_SHUTIL_DESTINATION_METHODS = frozenset({"copy", "move"})
_OS_REPLACE_METHOD = "replace"


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


def _literal_path(node: ast.expr | None, bindings: dict[str, str]) -> str | None:
    """A literal path, including one simple string binding, else None.

    Bindings are intentionally local and straight-line only (see
    `_WriteVisitor`).  This covers `target = "x"; Path(target).write_text(...)`
    without pretending to evaluate expressions, imports or control flow.
    """
    value = _constant_str(node)
    if value is not None:
        return value
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    return None


def _is_path_constructor(node: ast.expr) -> bool:
    """Whether *node* spells `Path`, directly or as `pathlib.Path`."""
    return (
        isinstance(node, ast.Name)
        and node.id == "Path"
        or (isinstance(node, ast.Attribute) and node.attr == "Path")
    )


def _path_constructor_target(node: ast.expr | None, bindings: dict[str, str]) -> str | None:
    """The literal target in `Path(target)`, else None."""
    if not isinstance(node, ast.Call) or not _is_path_constructor(node.func):
        return None
    if len(node.args) != 1 or node.keywords:
        return None
    return _literal_path(node.args[0], bindings)


def _path_value_target(node: ast.expr | None, bindings: dict[str, str]) -> str | None:
    """A path argument written as a literal or a literal `Path(...)`."""
    return _path_constructor_target(node, bindings) or _literal_path(node, bindings)


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


def _mode_is_writing(call: ast.Call) -> bool:
    """Whether a `Path.open` call has a literal write-capable mode."""
    mode = _constant_str(call.args[0]) if call.args else None
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = _constant_str(kw.value)
    return bool(mode and _WRITE_MODE_CHARS & set(mode))


def _module_call_name(node: ast.expr, module: str) -> str | None:
    """Method name for a direct `module.method(...)` spelling, else None."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == module
    ):
        return node.attr
    return None


def _write_call_targets(call: ast.Call, bindings: dict[str, str]) -> list[str]:
    """Targets written or mutated by one recognised Python call.

    This is the sole catalogue consumer.  `open` stays separate because it
    predates the pathname family and has a distinct `file=` grammar.
    """
    open_target = _open_call_target(call)
    if open_target is not None:
        return [open_target]

    func = call.func
    if isinstance(func, ast.Attribute):
        receiver = _path_constructor_target(func.value, bindings)
        if receiver is not None:
            if func.attr in _PATH_MUTATING_METHODS:
                return [receiver]
            if func.attr == _PATH_OPEN_METHOD and _mode_is_writing(call):
                return [receiver]
            if func.attr == _PATH_RENAME_METHOD:
                destination = _path_value_target(call.args[0], bindings) if call.args else None
                return [target for target in (receiver, destination) if target is not None]

    shutil_method = _module_call_name(func, "shutil")
    if shutil_method in _SHUTIL_DESTINATION_METHODS:
        destination = _path_value_target(call.args[1], bindings) if len(call.args) > 1 else None
        for kw in call.keywords:
            if kw.arg == "dst":
                destination = _path_value_target(kw.value, bindings)
        return [destination] if destination is not None else []

    if _module_call_name(func, "os") == _OS_REPLACE_METHOD:
        source = _path_value_target(call.args[0], bindings) if call.args else None
        destination = _path_value_target(call.args[1], bindings) if len(call.args) > 1 else None
        return [target for target in (source, destination) if target is not None]
    return []


class _WriteVisitor(ast.NodeVisitor):
    """Read calls with just enough local binding to retain literal paths."""

    def __init__(self) -> None:
        self.targets: list[str] = []
        self.bindings: dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        value = _constant_str(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                if value is None:
                    self.bindings.pop(target.id, None)
                else:
                    self.bindings[target.id] = value

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.visit(node.value)
        if isinstance(node.target, ast.Name):
            value = _constant_str(node.value)
            if value is None:
                self.bindings.pop(node.target.id, None)
            else:
                self.bindings[node.target.id] = value

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self.bindings.pop(node.target.id, None)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_isolated(node.body)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_isolated(node.body)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        self._visit_isolated(node.body)
        self._visit_isolated(node.orelse)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._visit_isolated(node.body)
        self._visit_isolated(node.orelse)

    visit_AsyncFor = visit_For

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        self._visit_isolated(node.body)
        self._visit_isolated(node.orelse)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_isolated(node.body)
        for handler in node.handlers:
            self._visit_isolated(handler.body)
        self._visit_isolated(node.orelse)
        self._visit_isolated(node.finalbody)

    def visit_Call(self, node: ast.Call) -> None:
        self.targets.extend(_write_call_targets(node, self.bindings))
        self.generic_visit(node)

    def _visit_isolated(self, body: list[ast.stmt]) -> None:
        outer = self.bindings
        self.bindings = outer.copy()
        for statement in body:
            self.visit(statement)
        self.bindings = outer


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
    visitor = _WriteVisitor()
    visitor.visit(tree)
    return visitor.targets


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
