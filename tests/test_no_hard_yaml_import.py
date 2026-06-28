"""Guard: renar modules must not hard-import PyYAML at module level.

PyYAML is an OPTIONAL RENAR dependency, not a core CLI dep. A module-level
`import yaml` in a CLI-reachable module breaks every `tausik` command on a clean
install (the v1.5.0 fresh-clone smoke caught exactly this). yaml must be imported
lazily inside the functions that need it. (v151-fix-yaml-hard-import)
"""

from __future__ import annotations

import ast
import os

import pytest

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")

# CLI-reachable modules (project.py imports cmd_renar unconditionally).
_RENAR_MODULES = [
    "project_cli_renar.py",
    "renar_conformance.py",
    "renar_export.py",
]


def _module_level_imports(path: str) -> set[str]:
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    names: set[str] = set()
    for node in tree.body:  # module-level only (not nested in functions)
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("mod", _RENAR_MODULES)
def test_no_module_level_yaml(mod):
    imports = _module_level_imports(os.path.join(_SCRIPTS, mod))
    assert "yaml" not in imports, (
        f"{mod} hard-imports yaml at module level — make it lazy (breaks the "
        f"core CLI on a clean install without PyYAML)."
    )
