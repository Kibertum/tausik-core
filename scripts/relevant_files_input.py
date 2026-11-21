"""Read a declared `relevant_files` list the way the caller meant it — or refuse.

GitLab #13. `task update <slug> --relevant-files "a.py,b.py,c.py"` stored ONE
element carrying the whole comma-joined string, and nothing objected: not the
parser (`nargs='*'` takes whatever it is handed), not the write (no check that
a path exists), not the help text (which said "JSON-list", the shape of the
STORAGE, and so invited the comma). The refusal arrived later and elsewhere —
from `verify`, as "No tests mapped for ['a.py,b.py,c.py']" — sounding like a
project without tests rather than a corrupted declaration. The cost is not
cosmetic: `relevant_files` is the QG-2 scope, and with a broken list every
scoped gate ran over nothing while the closure leaned on it.

Two decisions, both deliberate:

* A comma-carrying element that does NOT exist on disk is REFUSED, with the
  form that was meant. It is not split silently — a comma is legal in a file
  name, and rewriting a path the caller typed would break the one honest case
  to rescue the common mistake. An element that exists is accepted as it is.
* An element that merely does not exist is a WARNING, not a refusal: the file
  may be about to be created by the very task that declares it.

Refuse-first for '.' and directories (1.15 / TauX dogfood): expanding a folder
or the project root would look like a file scope while git-diff honesty and
security under-declare compared the wrong shape. Concrete files only.

One implementation, called from every path that TAKES a declaration (the CLI
update, `verify --relevant-files`, and `task done` on both CLI and MCP), so the
three entry points cannot disagree on what a declaration is. `tausik state
import` also writes the column — from a task file the framework itself
exported out of a row that passed this check when it was declared — and is
deliberately not judged here: an existence check against a branch that may not
carry the file yet would refuse to import honest state (review, session #252).
"""

from __future__ import annotations

import json
import os

from tausik_utils import ServiceError

#: The one sentence that names the right form; every refusal carries it.
RIGHT_FORM = "paths are passed SPACE-separated: --relevant-files a.py b.py (stored as a JSON list)"

DOT_REFUSAL = (
    "declare concrete files, not '.' / the project root — a whole-tree scope "
    "cannot honestly certify QG-2 coverage"
)
DIR_REFUSAL = (
    "declare concrete files, not a directory — refuse-first (no silent expand) "
    "so under-declare and security scope stay honest"
)


def _normalize_declared(raw: object) -> str:
    """Forward-slash form used for comparison; trailing slashes stripped."""
    return str(raw).replace("\\", "/").rstrip("/")


def _is_dot_or_project_root(normalized: str) -> bool:
    """True for '.', './', '.\\', and empty-after-strip tokens."""
    return normalized in {"", "."}


def _abs_under_root(root: str, normalized: str) -> str:
    if os.path.isabs(normalized):
        return os.path.normpath(normalized)
    return os.path.normpath(os.path.join(root, normalized.replace("/", os.sep)))


def check_declared_paths(paths: list[str], project_dir: str | None) -> list[str]:
    """Validate a declared list; return warning lines (may be empty).

    Raises ServiceError for:
    * an element that carries a comma and resolves to nothing on disk — the
      comma-joined mistake;
    * '.' / project-root tokens — whole-tree is not a file scope;
    * an element that exists and is a directory — refuse-first (no expand).

    Existence is judged against `project_dir` when given (relative declarations
    are project-relative), else against the process cwd.
    """
    root = project_dir or os.getcwd()
    missing: list[str] = []
    for raw in paths:
        # Backslashes read as separators, as every other reader of this column
        # does (gate_test_resolver): a declaration typed on Windows must not
        # turn into "not on disk" on a POSIX runner.
        p = _normalize_declared(raw)
        if _is_dot_or_project_root(p):
            raise ServiceError(
                f"relevant_files element {str(raw)!r} names the project root: "
                f"{DOT_REFUSAL}. {RIGHT_FORM}"
            )
        abs_path = _abs_under_root(root, p)
        exists = os.path.exists(abs_path)
        if exists and os.path.isdir(abs_path):
            raise ServiceError(
                f"relevant_files element {p!r} is a directory: {DIR_REFUSAL}. {RIGHT_FORM}"
            )
        parts = [s.strip() for s in p.split(",") if s.strip()]
        # The corruption shape: two or more pieces that each LOOK like a path.
        # A single not-yet-created file whose name carries a comma has one
        # piece without a separator or an extension and stays a warning.
        if not exists and len(parts) >= 2 and all("/" in s or "." in s for s in parts):
            raise ServiceError(
                f"relevant_files element {p!r} carries a comma and no such file exists: "
                f"this is {len(parts)} path(s) joined by ',' and would be stored as ONE "
                f"path, leaving the QG-2 scope empty. {RIGHT_FORM}"
            )
        if not exists:
            missing.append(p)
    if not missing:
        return []
    return [
        f"NOTE: {len(missing)} declared path(s) not on disk yet: {', '.join(missing)} "
        "— accepted (the task may create them); verify will map no tests to them until they exist."
    ]


def early_refuse_message(paths: list[str] | None, project_dir: str | None = None) -> str | None:
    """Refusal text for verify-before-gates, or None when the list is acceptable."""
    try:
        check_declared_paths([str(p) for p in (paths or [])], project_dir)
    except ServiceError as exc:
        return str(exc)
    return None


def invalid_scope_gate_result(
    message: str,
) -> tuple[bool, list[dict[str, object]], str]:
    """Synthetic verify failure used before describe_declared_scope / gates."""
    return (
        False,
        [
            {
                "name": "scope-declaration",
                "passed": False,
                "skipped": False,
                "severity": "block",
                "output": message,
            }
        ],
        "invalid-relevant-files",
    )


def notice_for_json_list(raw: object, project_dir: str | None) -> str:
    """`check_declared_paths` over a JSON-encoded list; the warnings as one
    string to append to a command's reply (empty when nothing to say).

    Unparseable input is not this function's business — the list is stored as
    written and the scope reader treats malformed JSON as absence.
    """
    try:
        declared = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return ""
    if not isinstance(declared, list):
        return ""
    lines = check_declared_paths([str(p) for p in declared], project_dir)
    return "".join("\n" + line for line in lines)
