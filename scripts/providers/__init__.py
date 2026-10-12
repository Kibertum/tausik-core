"""Provider registry — IDE/runtime abstraction (Decision #119, axis-1).

Axis-1 is the *runtime host* that TAUSIK runs inside (claude / cursor / kilo /
qwen). It owns: bootstrap target dir, settings format, transcript location, and
active-model detection. The *model* axis (Claude vs GLM/z.ai families) lives in
`model_profiles` config data, NOT here — z.ai is a model vendor, not a runtime,
so it is deliberately absent from this registry.

Each provider module registers itself at import time via `register(...)`.
Registration is lazy: the first `get()` / `available()` call imports every
sibling module once (`_registry.auto_register`). A malformed provider module is
skipped — one broken file never empties the registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Provider


_REGISTRY: dict[str, "Provider"] = {}
_registered = False


def register(provider: "Provider") -> None:
    """Register a provider instance under its ``name()`` slug (idempotent)."""
    _REGISTRY[provider.name()] = provider


def get(name: str) -> "Provider":
    """Return the provider for ``name``, or raise KeyError listing known slugs."""
    _ensure_registered()
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown provider {name!r}. Registered: {sorted(_REGISTRY)}. "
            "z.ai is a model vendor (see model_profiles), not a runtime provider."
        )
    return _REGISTRY[name]


def available() -> list[str]:
    """Sorted list of registered provider slugs."""
    _ensure_registered()
    return sorted(_REGISTRY)


def reset() -> None:
    """Clear the registry and force re-discovery on next access (test helper)."""
    global _registered
    _REGISTRY.clear()
    _registered = False


def _ensure_registered() -> None:
    """Import every provider module once so each self-registers."""
    global _registered
    if _registered:
        return
    _registered = True  # set first — guards against re-entrancy during imports
    from ._registry import auto_register

    auto_register()
