"""Load tip ``scripts/`` modules for memory preflight without an MCP restart.

A long-lived MCP process imports ``memory_preflight_query`` once. Mid-release
edits then stay invisible until someone restarts the host — which is a product
bug, not an operator ritual. Prefer ``<project>/scripts`` when present, reload
the preflight stack, and rebind the caller's globals.
"""

from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from typing import Any


_TIP_MODULES = (
    "memory_preflight_query",
    "memory_preflight_classification",
    "memory_relevance",
)

# importlib.reload replaces exception classes in the module dict. Callers that
# bound the old class (pytest.raises, isinstance) then miss raises from the
# reloaded functions. Keep the first-seen class objects across reloads.
_PRESERVE_ATTRS = {
    "memory_preflight_classification": ("ProtectedActionClassificationError",),
}


def prefer_project_scripts(project_dir: str | None = None) -> str | None:
    """Put ``<project>/scripts`` first on ``sys.path`` when it exists.

    Returns the path inserted, or ``None`` when no project scripts tree is found.
    """
    root = project_dir or os.getcwd()
    scripts = os.path.normpath(os.path.join(root, "scripts"))
    if not os.path.isfile(os.path.join(scripts, "memory_preflight_query.py")):
        return None
    while scripts in sys.path:
        sys.path.remove(scripts)
    sys.path.insert(0, scripts)
    return scripts


def refresh_preflight_modules(namespace: dict[str, Any] | None = None) -> ModuleType:
    """Reload tip preflight modules and optionally rebind names into ``namespace``.

    ``namespace`` is typically ``globals()`` of ``memory_preflight`` so the
    already-imported ``preflight_terms`` / ``live_conflict_count`` names follow
    the reloaded tip, not the stale first import.
    """
    prefer_project_scripts()
    for name in _TIP_MODULES:
        mod = sys.modules.get(name)
        if mod is None:
            importlib.import_module(name)
            continue
        preserved = {
            attr: getattr(mod, attr) for attr in _PRESERVE_ATTRS.get(name, ()) if hasattr(mod, attr)
        }
        importlib.reload(mod)
        for attr, value in preserved.items():
            setattr(mod, attr, value)
    query = sys.modules["memory_preflight_query"]
    if namespace is not None:
        namespace["fts_or"] = query.fts_or
        namespace["has_quarantined_conflict"] = query.has_quarantined_conflict
        namespace["live_conflict_count"] = query.live_conflict_count
        namespace["preflight_terms"] = query.preflight_terms
        classification = sys.modules["memory_preflight_classification"]
        for attr in (
            "PROTECTED_KINDS",
            "binding_payload",
            "classify_action",
            "normalize_host_shell_tool",
            "within_reserve_grace",
        ):
            if attr in namespace:
                namespace[attr] = getattr(classification, attr)
        relevance = sys.modules["memory_relevance"]
        if "MAX_ENTRIES" in namespace:
            namespace["MAX_ENTRIES"] = relevance.MAX_ENTRIES
    return query
