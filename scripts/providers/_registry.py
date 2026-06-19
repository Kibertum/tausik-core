"""Auto-discovery: import every provider module so it self-registers.

Pure function, NO side effect at import — `__init__._ensure_registered` calls
``auto_register`` exactly once, lazily, on first registry access. This avoids
the double/circular auto-register that the original scaffold suffered from.
"""

from __future__ import annotations

import importlib
import os

_SKIP = {"__init__", "_registry", "base"}


def auto_register() -> None:
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    for fname in sorted(os.listdir(pkg_dir)):
        if not fname.endswith(".py"):
            continue
        mod_name = fname[:-3]
        if mod_name in _SKIP:
            continue
        try:
            mod = importlib.import_module(f".{mod_name}", __package__)
            register_self = getattr(mod, "_register_self", None)
            if callable(register_self):
                register_self()
        except Exception:  # noqa: BLE001
            # A malformed provider module must not empty the registry — skip it;
            # the well-formed providers still register (Decision #119 NEGATIVE AC).
            # Calling _register_self each pass (not just at import) makes reset()
            # re-populate, since importlib returns the cached module body-less.
            continue
