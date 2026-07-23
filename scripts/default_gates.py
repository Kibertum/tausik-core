"""Default quality gate configurations.

`DEFAULT_GATES` is the union of:
  * `UNIVERSAL_GATES` — built-in scoped gates with no `stacks` filter
    (filesize, tdd_order, ruff, mypy, bandit, the drift detectors). Their
    single declaration is `gate_registry.GATE_REGISTRY`; this module only
    projects the registry into the `{name: config}` shape config expects.
  * `POST_SCOPE_GATES` — QG-2 report gates (Verify-First, changelog). They
    used to be invisible here, which is why `gates status` could not list
    them and `gates enable/disable` could not reach them.
  * Stack-scoped gates pulled from `stack_registry` — pytest, tsc, eslint,
    cargo-*, phpstan, terraform-validate, etc. The canonical source is
    each stack's `stacks/<name>/stack.json` gates section.

If the registry can't load (early bootstrap, missing dir), we fall back
to a full hardcoded set so the framework still boots — keeping the
contract `from default_gates import DEFAULT_GATES` exception-free.
"""

from __future__ import annotations

from gate_registry import PHASE_POST_SCOPE, PHASE_SCOPED, defaults_for_phase

# --- Universal gates (no stacks filter) -------------------------------------
# Derived, not written: gate-registry-single-source moved the literal into
# `gate_registry`. Kept as a module-level name because stacks docs and
# `test_external_flags_are_real` refer to it as the shape a stack gate follows.

UNIVERSAL_GATES: dict[str, dict] = defaults_for_phase(PHASE_SCOPED)

# QG-2 gates that run after the scoped pipeline. Present in DEFAULT_GATES for
# visibility and toggling only — `get_gates_for_trigger` filters them out of
# `run_gates`, which could not call them (different signature) and must not try.
POST_SCOPE_GATES: dict[str, dict] = defaults_for_phase(PHASE_POST_SCOPE)


# Stack-scoped gates come EXCLUSIVELY from the plugin registry
# (`stacks/<name>/stack.json`). v1.3 blind-review pass dropped the 190-line hardcoded fallback
# because it silently drifted from the source-of-truth files — adding a new
# gate to a stack.json would not appear if the registry import failed; a
# removed gate would still appear. Now: registry failure logs WARNING and
# returns empty dict, surfacing the issue rather than masking it.


def _build_stack_scoped_gates() -> dict[str, dict]:
    """Read stack-scoped gates from the plugin registry. Empty + log on error."""
    try:
        from stack_registry import default_registry

        reg = default_registry()
        out: dict[str, dict] = {}
        for name in sorted(reg.all_stacks()):
            for gname, gcfg in reg.gates_for(name).items():
                if gname not in out:
                    out[gname] = dict(gcfg)
        return out
    except Exception:  # noqa: BLE001 — must not crash module import
        import logging

        logging.getLogger("tausik.default_gates").warning(
            "Stack registry unavailable — stack-scoped gates DISABLED. "
            "Run `tausik doctor` to diagnose. Universal gates (filesize, "
            "ruff, mypy, bandit, tdd_order) remain active.",
            exc_info=True,
        )
        return {}


def _build_default_gates() -> dict[str, dict]:
    """DEFAULT_GATES = UNIVERSAL ∪ stack-scoped ∪ post-scope.

    Post-scope goes last on purpose: a `stacks/*/stack.json` that happened to
    declare a gate named `changelog` would otherwise shadow the QG-2 gate of
    the same name with a command gate, and the framework's own close contract
    would be redefinable by a stack plugin.
    """
    merged: dict[str, dict] = dict(UNIVERSAL_GATES)
    merged.update(_build_stack_scoped_gates())
    merged.update(POST_SCOPE_GATES)
    return merged


DEFAULT_GATES: dict[str, dict] = _build_default_gates()
