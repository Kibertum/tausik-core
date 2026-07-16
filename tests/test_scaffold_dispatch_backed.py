"""Guard: every IDE in SCAFFOLD_IDES must have a real dispatch branch in bootstrap.

The failure this prevents is the quiet one. If an IDE is listed in SCAFFOLD_IDES but
`bootstrap_ide` has no `elif ide == "<name>"` branch, then `bootstrap.py --ide <name>`
copies the skills, prints "Done!", and produces NO host config at all. Exit code 0.
The user believes the IDE is set up; the agent that opens the project finds TAUSIK
"supported" but unconfigured — and closes the gap by inventing configuration. That is
the exact chain that broke a user's OpenCode host (gotcha #201).

Membership in SCAFFOLD_IDES is a promise. This test makes the promise load-bearing.

Run: pytest tests/test_scaffold_dispatch_backed.py -v
"""

from __future__ import annotations

import ast
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BOOTSTRAP = os.path.join(_ROOT, "bootstrap")
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

from bootstrap_config import IDE_DIRS, SCAFFOLD_IDES  # noqa: E402

_BOOTSTRAP_PY = os.path.join(_BOOTSTRAP, "bootstrap.py")


def _dispatched_ides(source: str, func: str = "bootstrap_ide") -> set[str]:
    """IDE names compared against `ide` in bootstrap_ide's if/elif chain.

    Parsed from the AST, not grepped: a comment or a docstring mentioning an IDE
    name must not be able to satisfy this guard.
    """
    tree = ast.parse(source)
    fn = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func),
        None,
    )
    assert fn is not None, f"{func}() not found in bootstrap.py"

    found: set[str] = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        if not (isinstance(left, ast.Name) and left.id == "ide"):
            continue
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, ast.Eq) and isinstance(comparator, ast.Constant):
                if isinstance(comparator.value, str):
                    found.add(comparator.value)
    return found


def test_every_scaffold_ide_has_a_dispatch_branch():
    source = open(_BOOTSTRAP_PY, encoding="utf-8").read()
    dispatched = _dispatched_ides(source)
    missing = [ide for ide in SCAFFOLD_IDES if ide not in dispatched]
    assert not missing, (
        f"IDEs claim to be scaffolded but bootstrap_ide has no branch for them: {missing}. "
        "`--ide <name>` would print 'Done!' and configure nothing — a silent no-op is "
        "worse than an unsupported IDE, because agents fill the gap by guessing."
    )


def test_no_dispatch_branch_for_an_unscaffolded_ide():
    """The converse: a generator branch that exists but is unreachable via --ide is
    dead code pretending to be support."""
    source = open(_BOOTSTRAP_PY, encoding="utf-8").read()
    orphans = [
        ide for ide in _dispatched_ides(source) if ide in IDE_DIRS and ide not in SCAFFOLD_IDES
    ]
    assert not orphans, (
        f"bootstrap_ide dispatches on {orphans}, but they are not in SCAFFOLD_IDES, "
        "so `--ide` will never select them."
    )


def test_opencode_is_fully_backed():
    """OpenCode specifically: the cautionary tale must stay honest."""
    assert "opencode" in IDE_DIRS
    assert "opencode" in SCAFFOLD_IDES
    assert "opencode" in _dispatched_ides(open(_BOOTSTRAP_PY, encoding="utf-8").read())
    assert os.path.isfile(os.path.join(_ROOT, "harness", "opencode", "plugins", "tausik-qg0.js")), (
        "OpenCode is declared scaffolded, but the QG-0 plugin that enforces it is gone"
    )


def test_guard_bites_on_a_planted_unbacked_ide():
    """Negative scenario: the guard must catch an IDE with no branch, not pass silently."""
    planted = '''
def bootstrap_ide(project_dir, ide, config):
    """Mentions windsurf in the docstring only — that must not count."""
    if ide == "claude":
        pass
    # elif ide == "windsurf":  <- commented out, also must not count
    elif ide == "cursor":
        pass
'''
    dispatched = _dispatched_ides(planted)
    assert dispatched == {"claude", "cursor"}
    assert "windsurf" not in dispatched, "a comment or docstring satisfied the guard"


def test_scaffold_ides_have_config_dirs():
    """Cheap invariant restated locally: you cannot scaffold into a dir that isn't declared."""
    with pytest.raises(StopIteration):
        next(iter(ide for ide in SCAFFOLD_IDES if ide not in IDE_DIRS))
