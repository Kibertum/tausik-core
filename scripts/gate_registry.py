"""The single place a built-in gate is declared (gate-registry-single-source).

Declaring a gate used to mean landing in four unconnected places: its metadata
in `default_gates.UNIVERSAL_GATES`, its implementation in a chain of `if
name == ...` in `gate_runner`, its "is this built-in?" answer inferred from
`command is None` in `gate_command_policy`, and — for the two gates that run
after the scoped pipeline — a hardcoded call in `service_gates`. The last of
those was invisible everywhere else: `gate_changelog` and `gate_verify_first`
were not listed by `gates status`, could not be toggled through `gates
enable/disable`, and wrote no `gate_runs` row, so the check could not prove
that the QG-2 gate it depends on had actually run.

One `GateSpec` per gate now carries all four answers. The precedent is
`gate_runner.gate_verdict`: the same fact spelled in five places had already
drifted in both directions before it was consolidated.

The record itself and the two phases live in `gate_spec` — this module is the
DATA (which gates exist), that one is the DECLARATION (what a gate record is).

IMPLEMENTATIONS ARE RESOLVED LAZILY, by dotted string. Importing them here
eagerly would make `default_gates` (which imports this module) pull in
`gate_bootstrap_drift` → `project_config` → `default_gates` — an import cycle.
The cost is one `importlib.import_module` call per dispatch, which is a
`sys.modules` hit after the first, plus a `getattr`.

Two impl address forms:

* ``"module:function"`` — a free function, imported on first use.
* ``"svc:method_name"`` — a method looked up on the *service instance* with
  `getattr` at call time. Post-scope gates use this form deliberately: the
  binding must stay late so that `GatesMixin` subclasses, and the pytest shim
  that neutralises Verify-First for the legacy suite
  (`tests/conftest.py::_verify_first_autouse_compat_shim`), keep working. An
  eagerly resolved function reference would silently bypass both.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable, cast

# The RECORD lives in gate_spec, the DATA lives here. Re-exported so every
# existing `from gate_registry import GateSpec, PHASE_SCOPED` keeps working.
from gate_spec import PHASE_POST_SCOPE, PHASE_SCOPED, GateSpec

__all__ = ["GateSpec", "PHASE_POST_SCOPE", "PHASE_SCOPED"]


# The scoped half of the data lives in `gate_registry_scoped` — it is the half
# that grows with every new gate, and it is what pushed this module past the
# line cap once each gate had to declare the effect it prevents.
from gate_registry_scoped import _SCOPED  # noqa: E402

# --- Post-scope gates: QG-2 report gates, previously hardcoded --------------
# `phase` is carried inside default_config too, so it survives the trip through
# `load_gates` into `gates status` and into `get_gates_for_trigger`'s filter
# without either of them needing to consult this module for every gate.

_POST_SCOPE: tuple[GateSpec, ...] = (
    GateSpec(
        name="verify_first",
        prevents=(
            "A task closes with no fresh signed verify green for it — the closure that "
            "certifies nothing, which is the whole subject of QG-2. "
        ),
        phase=PHASE_POST_SCOPE,
        impl="svc:_enforce_verify_first",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done"],
            "command": None,
            "phase": PHASE_POST_SCOPE,
            "description": "Verify-First Contract: a fresh signed verify green must exist",
        },
    ),
    GateSpec(
        name="changelog",
        prevents=(
            "Disabled by default, so today it stops nothing here. Where enabled it "
            "prevents a task closing without a CHANGELOG line — a change that shipped "
            "with no trace outside the commit message. "
        ),
        phase=PHASE_POST_SCOPE,
        impl="svc:_enforce_changelog",
        skip_on_fileless_close=True,
        enabled_resolver="gate_changelog:changelog_gate_enabled",
        default_config={
            "enabled": False,
            "severity": "block",
            "trigger": ["task-done"],
            "command": None,
            "phase": PHASE_POST_SCOPE,
            "description": "Continuous CHANGELOG: every task adds an entry (convention #275)",
        },
    ),
)


GATE_REGISTRY: dict[str, GateSpec] = {s.name: s for s in (*_SCOPED, *_POST_SCOPE)}


def specs_for_phase(phase: str) -> tuple[GateSpec, ...]:
    """Registry entries of one phase, in declaration order.

    Declaration order is the execution order for post-scope gates
    (Verify-First before changelog), so it is data, not incidental.
    """
    return tuple(s for s in GATE_REGISTRY.values() if s.phase == phase)


def defaults_for_phase(phase: str) -> dict[str, dict]:
    """`{name: default_config}` for one phase — the shape `default_gates` needs.

    Returns deep-enough copies (one level of dict plus list values) so a caller
    mutating a merged gate config cannot reach back into the registry and
    change what the next caller sees.
    """
    out: dict[str, dict] = {}
    for spec in specs_for_phase(phase):
        cfg = dict(spec.default_config)
        for k, v in cfg.items():
            if isinstance(v, list):
                cfg[k] = list(v)
        out[spec.name] = cfg
    return out


# The one impl that is not an implementation: gates pointing here are command
# gates, and their command is exactly what a user override may replace.
_COMMAND_IMPL = "gate_command_runner:run_command_gate"


def is_builtin(name: str, default_command: str | None = None) -> bool:
    """Does the framework run this gate in-process, with no command to extend?

    The question the command policy actually asks. It used to be answered by
    inference — ``command is None`` — which is true of today's built-ins by
    coincidence of their configs, not by declaration. Registry-first makes it a
    stated fact: `ruff` is declared here yet is a *command* gate, so a vendored
    path override stays legal, while `filesize` takes none.

    For gates the framework does not declare — stack-declared
    (`stacks/*/stack.json`) and user-defined — there is no in-process
    implementation to ship, so the legacy inference is kept for them alone.
    """
    spec = GATE_REGISTRY.get(name)
    if spec is not None:
        return spec.impl != _COMMAND_IMPL
    return not default_command


def _resolve_dotted(path: str) -> Callable[..., Any]:
    module_name, _, attr = path.partition(":")
    module = importlib.import_module(module_name)
    return cast("Callable[..., Any]", getattr(module, attr))


def impl_for(name: str) -> Callable[..., Any] | None:
    """The `(gate, files) -> (passed, output)` callable for a scoped gate.

    `None` for a gate the registry does not know (stack/custom gates — the
    caller falls back to `run_command_gate`) and for post-scope gates, whose
    implementations are bound to a service instance, not imported
    (`bound_impl_for`).
    """
    spec = GATE_REGISTRY.get(name)
    if spec is None or spec.impl.startswith("svc:"):
        return None
    return _resolve_dotted(spec.impl)


def bound_impl_for(spec: GateSpec, svc: Any) -> Callable[..., Any]:
    """The callable for a post-scope gate, bound to `svc` at call time.

    `getattr` on the instance, every time — see the module docstring on why the
    binding must stay late.
    """
    if spec.impl.startswith("svc:"):
        return cast("Callable[..., Any]", getattr(svc, spec.impl.split(":", 1)[1]))
    return _resolve_dotted(spec.impl)


def apply_post_scope_enabled(merged: dict[str, dict], cfg: dict[str, Any]) -> None:
    """Rewrite the `enabled` of every post-scope gate in a merged gate map.

    Called by `load_gates`, so one answer serves both readers of that map:
    `gates status`, which would otherwise report a gate as OFF while it blocks
    every close, and `gate_post_scope`, which decides from it whether to invoke
    the gate at all. Mutates in place — the caller owns the map.
    """
    for name, gate in merged.items():
        if gate.get("phase") == PHASE_POST_SCOPE:
            gate["enabled"] = resolve_enabled(name, cfg, bool(gate.get("enabled", True)))


def resolve_enabled(name: str, cfg: dict[str, Any], merged_enabled: bool) -> bool:
    """Effective on/off for a gate whose switch predates `gates.<name>.enabled`.

    Only post-scope gates carry a resolver. The merged value (registry default
    plus any `gates.<name>` override) wins when it is explicitly true; the
    resolver is what stops a project that enabled the gate through its original
    key from being told, truthfully-looking, that the gate is off.

    This answer is not only cosmetic — `gate_post_scope` decides from it whether
    to invoke the gate — so a resolver that raises resolves to ON. Treating the
    exception as "no opinion" would let one unreadable config key silently
    retire a QG-2 gate, the failure mode every other reader here fails closed
    against.
    """
    spec = GATE_REGISTRY.get(name)
    if spec is None or not spec.enabled_resolver:
        return merged_enabled
    if merged_enabled:
        return True
    try:
        return bool(_resolve_dotted(spec.enabled_resolver)(cfg))
    except Exception:  # noqa: BLE001 — unknown policy is not "off"
        return True
