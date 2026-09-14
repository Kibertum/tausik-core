"""Guard: no module may hard-import PyYAML at module level.

PyYAML is an OPTIONAL RENAR dependency, not a core CLI dep. A module-level
`import yaml` in a CLI-reachable module breaks every `tausik` command on a clean
install (the v1.5.0 fresh-clone smoke caught exactly this). yaml must be
imported lazily inside the functions that need it. (v151-fix-yaml-hard-import)

THE SUBJECT IS DERIVED, NOT TYPED. This guard used to carry a hand-written list
of three module names, and a module could leave that list simply by being born:
`renar_conformance_yaml.py` was carved out of `renar_conformance.py` and took
`_require_yaml` -- the lazy import this guard exists for -- with it, while the
listed module kept its entry and the risky code moved to a file the list had
never heard of. A guard whose inventory is maintained by hand measures the
list's upkeep, not the invariant. So the invariant is stated over the trees
themselves: measured at the time of writing, 438 files across `scripts/`,
`harness/` and `bootstrap/`, none of them offending.

AND THE DETECTOR IS TESTED SEPARATELY FROM THE TREE. A tree walk over a clean
tree is green whether it works or not -- if the glob broke, or the AST parse
started swallowing everything, the assertion would pass by finding nothing. So
the detector is a pure function over source TEXT, exercised on a deliberately
broken sample and on the lazy form it must NOT flag, and the walk separately
asserts it actually visited files.
"""

from __future__ import annotations

import ast
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Declared for the crosscutting registry, and the declaration is the price of
# the rewrite: while this file named three modules it was an ordinary test the
# resolver could map from its imports; now it iterates trees, which the
# scoped-pytest gate cannot infer. Session #209 lost exactly that trade -- a
# test widened to walk a tree went invisible to the scoped run -- so the
# registry refuses to let it happen silently.
#
# IT MUST STAY A LITERAL. `gate_test_resolver.read_crosscutting_scope` reads it
# with `ast.literal_eval` and never imports the module, so a comprehension over
# the tuple below reads as NO DECLARATION AT ALL and the file goes right back to
# being invisible. Measured the hard way: written as `[f"{t}/" for t in _TREES]`
# first, and the registry flagged it exactly as if nothing were declared.
CROSSCUTTING_SCOPE = ["scripts/", "harness/", "bootstrap/"]

# The trees whose modules the CLI and the MCP harness import. Directories, not
# module names: adding a file to one of them puts it under the guard with no
# edit here, which is the whole point of the rewrite. Derived from the
# declaration above rather than typed beside it, so the guard cannot end up
# walking a tree it never declared.
_TREES = tuple(p.rstrip("/") for p in CROSSCUTTING_SCOPE)

_FORBIDDEN = "yaml"


def module_level_imports(source: str) -> set[str]:
    """Top-level module names imported at MODULE level, ignoring nested ones.

    Nested is the point: an `import yaml` inside a function is the SUPPORTED
    form, so `ast.walk` would be the wrong tool here even though the resolver
    in `gate_test_resolver.top_level_imports` uses it -- that one answers "what
    does this file depend on at all", this one answers "what does importing
    this file cost you". Unparseable source yields nothing rather than raising:
    a syntax error is another gate's finding, not this one's.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def _python_files(tree: str) -> list[str]:
    base = os.path.join(_ROOT, tree)
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".venv", "node_modules"}]
        found.extend(os.path.join(dirpath, f) for f in filenames if f.endswith(".py"))
    return sorted(found)


# --- the detector itself, on fixtures that CAN fail -------------------------


def test_the_detector_catches_a_module_level_import():
    """Deliberately broken sample: without this the tree walk proves nothing."""
    assert _FORBIDDEN in module_level_imports("import yaml\n")
    assert _FORBIDDEN in module_level_imports("from yaml import safe_dump\n")
    assert _FORBIDDEN in module_level_imports("import os\nimport yaml\n\nX = 1\n")


def test_the_detector_ignores_the_lazy_form_that_is_allowed():
    """The neighbouring bucket: flagging the supported form would be worse than
    missing the broken one, because it would push callers back to hard imports."""
    lazy = "def f():\n    import yaml\n    return yaml\n"
    assert _FORBIDDEN not in module_level_imports(lazy)
    deferred = "def f():\n    from yaml import safe_dump\n    return safe_dump\n"
    assert _FORBIDDEN not in module_level_imports(deferred)


def test_unparseable_source_is_not_a_finding_of_this_guard():
    assert module_level_imports("def (:\n") == set()


# --- the invariant over the trees -------------------------------------------


@pytest.mark.parametrize("tree", _TREES)
def test_the_walk_actually_visits_files(tree):
    """A broken glob would make the guard below green by scanning nothing."""
    assert _python_files(tree), f"{tree}/ yielded no Python files — the walk is broken"


@pytest.mark.parametrize("tree", _TREES)
def test_no_module_level_yaml(tree):
    offenders = []
    for path in _python_files(tree):
        with open(path, encoding="utf-8") as f:
            if _FORBIDDEN in module_level_imports(f.read()):
                offenders.append(os.path.relpath(path, _ROOT))
    assert not offenders, (
        f"{len(offenders)} file(s) hard-import yaml at module level — make it lazy "
        f"(breaks the core CLI on a clean install without PyYAML): "
        f"{', '.join(offenders)}"
    )
