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


# --- Scoped gates: the former `default_gates.UNIVERSAL_GATES` ---------------
# Values are byte-identical to the literal they replace; tests/test_gate_registry
# asserts that, because a "refactor" that quietly changes a severity or a
# trigger is a behaviour change wearing a refactor's clothes.

_SCOPED: tuple[GateSpec, ...] = (
    GateSpec(
        name="ruff",
        phase=PHASE_SCOPED,
        impl="gate_command_runner:run_command_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            # lint-error-shipped-because-ruff-is-not-a-closing-gate: `verify`
            # was ADDED here deliberately (release 1.9), and this is a
            # behaviour change, not a refactor. The gate was already enabled
            # and already `block`, but it only ran on `commit` — so a task
            # could be verified, closed and its receipt signed over a tree the
            # linter had never looked at. Measured, not supposed: an F541
            # introduced in session #183 survived the full suite (7386
            # passed), `verify --task`, `task done` with six gates, and a
            # signed receipt, because no closing gate runs a linter and the
            # defect changes no behaviour a test could observe.
            #
            # It runs at `verify` rather than `task-done` because that is where
            # evidence is produced, and it is scoped by `{files}` like the
            # pytest gate, so it costs a lint of the declared scope, not of the
            # tree.
            "trigger": ["commit", "verify"],
            "command": "ruff check {files}",
            "description": "Lint with ruff before commit and at verify",
            "file_extensions": [".py"],
        },
    ),
    GateSpec(
        name="mypy",
        phase=PHASE_SCOPED,
        impl="gate_command_runner:run_command_gate",
        default_config={
            "enabled": False,
            "severity": "warn",
            "trigger": ["commit"],
            # NO {files} — DELIBERATE. `mypy {files}` handed mypy the CHANGED
            # files, while pyproject.toml declares its own source set
            # (files = ["scripts", "harness/claude/mcp/project"], exclude =
            # ["scripts/hooks/"]). Two sources of truth about WHAT is checked —
            # the same defect class this release fixed in CLAUDE.md (decision
            # #277: address from one source, content from another).
            #
            # A file passed explicitly is checked OUTSIDE the source set, so
            # imports that resolve in the normal run stop resolving: measured on
            # tests/conftest.py — three errors as an argument, zero in the
            # project run, because tests/ is not in the set at all. `exclude`
            # does not apply to explicit arguments either, so scripts/hooks/,
            # excluded on purpose, would be checked too.
            #
            # The project run also catches MORE: a change in one module that
            # breaks the types of another is invisible to a per-file run.
            # Measured cost of the whole project: 0.93 s.
            #
            # `file_extensions` still scopes WHEN the gate applies — a commit
            # touching no .py does not run it. That works without {files} since
            # mypy-gate-measures-differently-than-mypy-itself.
            "command": "mypy",
            "description": "Type-check the project's configured source set before commit",
            "file_extensions": [".py"],
        },
    ),
    GateSpec(
        name="filesize",
        phase=PHASE_SCOPED,
        impl="gate_filesize:run_filesize_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Warn if files exceed max_lines threshold",
            # Interim cap raised 400→500 (task l26-filesize-gate-revisit,
            # decision #190): the 400 cap deformed architecture (~30 wrapper
            # modules split only to pass; 5 core files written to exactly 400).
            # 500 absorbs every documented wrapper-merge with margin while a
            # genuinely 2× file still blocks. The real fix (measure post-MRO
            # public class surface, not raw lines) is a deferred follow-up.
            "max_lines": 500,
        },
    ),
    GateSpec(
        name="test_dedupe",
        phase=PHASE_SCOPED,
        impl="gate_test_dedupe:run_test_dedupe_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Block GROWTH in structurally indistinguishable tests",
            # The detector (`audit_pytest_dedupe`) shipped with a --check flag
            # and was documented as review-only, so nothing ran it and the
            # number grew unwatched: 294 groups / 683 tests in session #178,
            # 322 / 753 when this gate landed. Existing debt is baselined in the
            # committed tausik/gates.json and blocks nobody; only growth is red.
            # The subject is DISTINGUISHABILITY, not count — this gate never
            # measures how many tests exist, so it cannot be satisfied by
            # deleting them.
        },
    ),
    GateSpec(
        name="class_surface",
        phase=PHASE_SCOPED,
        impl="gate_class_surface:run_class_surface_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Cap a class's composed public surface after inheritance",
            # Complements `filesize`, never replaces it (task filesize-mro-exempt-mcp).
            # The line gate counts raw lines per FILE, so a god-object assembled from
            # mixins is structurally invisible to it: every mixin sits under the cap
            # while the composed class exposes 129 public members. Worse, the line cap
            # CAUSED the split — module sizes pile up just under the old 400 boundary
            # (26 modules at 350-399 vs 22 at 300-349, then 6 above 400), so files were
            # cut to fit and the composed surface grew as each file looked healthier.
            # Cap + ratchet baseline live in the committed tausik/gates.json.
            "max_public_members": 60,
        },
    ),
    GateSpec(
        name="bandit",
        phase=PHASE_SCOPED,
        impl="gate_command_runner:run_command_gate",
        default_config={
            "enabled": False,
            "severity": "warn",
            "trigger": ["review"],
            "command": "bandit -r {files} -q",
            "description": "Security scan with bandit",
        },
    ),
    GateSpec(
        name="tdd_order",
        phase=PHASE_SCOPED,
        impl="gate_tdd_order:run_tdd_order_gate",
        default_config={
            "enabled": False,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "Verify test files were modified (TDD enforcement)",
        },
    ),
    # Blocks task-done when a source edit did not reach the deployed profile that
    # actually runs (hooks/MCP load from .claude/ etc., tests import from
    # scripts/). BLOCK, not warn: an edit that did not take effect is not done.
    # Inert when no profile is installed (fresh clone / CI). See
    # gate_bootstrap_drift.py and memory #229.
    GateSpec(
        name="bootstrap_drift",
        phase=PHASE_SCOPED,
        impl="gate_bootstrap_drift:run_bootstrap_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done"],
            "command": None,
            "description": "Fail if deployed IDE profiles drift from scripts/ source",
        },
    ),
    # Refuses a close/commit that routes project knowledge into another agent's
    # memory (~/.claude memory, .cursor/rules, copilot instructions, aider, …).
    # BLOCK: knowledge that lands there is not "somewhere else", it is gone for
    # every agent but one. Inert outside a git repository. See memory_sinks.py
    # for the deny-list and the three enforcement layers.
    GateSpec(
        name="memory_route",
        phase=PHASE_SCOPED,
        impl="gate_memory_route:run_memory_route_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Block writes that route project knowledge into a foreign agent's memory",
        },
    ),
    # RENAR §3.11 drift detectors (warning-mode). Read-only scans of the RENAR
    # artifact store; ignore `files`. Warn-only by design — see renar_drift.py.
    GateSpec(
        name="renar_drift_schema",
        phase=PHASE_SCOPED,
        impl="gate_renar_drift:run_renar_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR drift-1: schema validation of SPEC/ADAPT artifacts",
        },
    ),
    GateSpec(
        name="renar_drift_provenance",
        phase=PHASE_SCOPED,
        impl="gate_renar_drift:run_renar_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR drift-7: stale TC↔requirement (task↔SPEC) provenance",
        },
    ),
    # §10.11.1 (p.485) control point, under the name ADR-007 promised for it.
    # Read-only, warn-only, ignores `files` — same shape as the two above.
    GateSpec(
        name="check_adapt_supersession",
        phase=PHASE_SCOPED,
        impl="gate_renar_drift:run_renar_drift_gate_for",
        default_config={
            "enabled": True,
            "severity": "warn",
            "trigger": ["task-done"],
            "command": None,
            "description": "RENAR §10.11.1: delta-ADAPT hanging off a superseded parent",
        },
    ),
    # Fails a commit when the durable `tausik/` projection drifts from a fresh DB
    # export — the git-native state must equal its source of truth before it
    # enters a commit. COMMIT trigger, not task-done: a close mutates the DB (and
    # can auto-close its parent), so a task-done check would flag its own write.
    # Read-only; SKIPS (passes) when no `tausik/` tree exists (opt-in). See
    # gate_state_roundtrip.py and state-git-roundtrip-gate.
    GateSpec(
        name="state_roundtrip",
        phase=PHASE_SCOPED,
        impl="gate_state_roundtrip:run_state_roundtrip_gate_for",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["commit"],
            "command": None,
            "description": "Fail if the tausik/ git-native state drifts from the DB export",
        },
    ),
    # Refuses a close/commit whose CLAUDE.md DYNAMIC block was NOT rendered from
    # this database — the block with its memory tail wiped, i.e. the shape of an
    # empty/foreign project. BLOCK: the wipe reached twenty commits between v1.0.0
    # and 2026-08 while every suite stayed green, and a fresh agent reads that file
    # first and believes it. Unlike state_roundtrip this runs at task-done TOO: the
    # check is immune to staleness (it asks whether a tail exists, not whether the
    # counters are current), so a close cannot flag its own write. Read-only, and
    # inert without a DB / CLAUDE.md / markers — those are NOT_APPLICABLE and pass.
    # NOT fail-open: a fault that stops the check from running is COULD_NOT_RUN and
    # BLOCKS (claudemd-state-gate-reports-passed-when-it-could-not-run — it used to
    # be signed as PASSED). See gate_claudemd_state.py.
    GateSpec(
        name="claudemd_state_drift",
        phase=PHASE_SCOPED,
        impl="gate_claudemd_state:run_claudemd_state_gate_for",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Fail if the CLAUDE.md dynamic block was not rendered from the live DB",
        },
    ),
    # Fails a close/commit when a changed SKILL.md breaks the agentskills.io canon
    # (name/dir + sizes). INERT unless a SKILL.md changed; hygiene, not trust.
    GateSpec(
        name="skill_spec_conformance",
        phase=PHASE_SCOPED,
        impl="skill_spec_conformance:run_skill_conformance_gate",
        default_config={
            "enabled": True,
            "severity": "block",
            "trigger": ["task-done", "commit"],
            "command": None,
            "description": "Fail if a changed SKILL.md violates the agentskills.io name/size canon",
            "file_extensions": [".md"],
        },
    ),
)


# --- Post-scope gates: QG-2 report gates, previously hardcoded --------------
# `phase` is carried inside default_config too, so it survives the trip through
# `load_gates` into `gates status` and into `get_gates_for_trigger`'s filter
# without either of them needing to consult this module for every gate.

_POST_SCOPE: tuple[GateSpec, ...] = (
    GateSpec(
        name="verify_first",
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
