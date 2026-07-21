"""Gate enable/disable — the single formula for flipping a gate on or off.

Split out of `project_config` at the 400-line cap, the same way
`gate_command_policy` was. The unit is coherent on its own terms, not merely
convenient: everything here answers "may this gate be named that, and did the
flip actually take effect", which is a different question from "how is config
loaded and merged".

Why one module and not one per caller: this logic previously existed TWICE —
here and again inside the MCP handler — and the copy had drifted in three
independent ways (it round-tripped the effective config into the project file,
it reported success regardless of the trust verdict, and its name pattern
refused three registered gates). A formula written in two places diverges in
both directions, silently, and the copy nobody re-reads is the one that rots.
"""

from __future__ import annotations

import re

# What a gate key may be called. Authority is the registry (`DEFAULT_GATES`),
# not this line: `test_validator_accepts_every_registered_gate_name` fails if
# the two ever disagree again.
GATE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def set_gate_enabled(name: str, enable: bool, tausik_dir: str | None = None) -> str:
    """Toggle a gate in the project tier and report what actually took effect.

    ``tausik_dir`` names the project to write to; omitted → the ambient one.

    The write always lands in the project file, but it does not always take
    effect: the trust policy refuses a project-scope disable of a guarded gate,
    and a trusted tier can hold the opposite value outright. Reporting success
    in either case would be the silent lie this whole mechanism exists to
    remove, so the answer is derived from the EFFECTIVE config rather than from
    the write — in both directions. Shared by the CLI and the MCP handler.

    The name check lives here rather than at either call site: it used to guard
    the MCP path alone, which meant the CLI accepted names the MCP refused, and
    a gate key is a path-ish token written into a JSON file.

    The pattern admits ``_`` because the gate registry uses it — `tdd_order`,
    `renar_drift_schema`, `renar_drift_provenance`. The MCP-only copy of this
    check spelled it without ``_`` and so refused to toggle three REGISTERED
    gates, answering "Invalid gate name" for a gate the same server had just
    listed. Hoisting the check unchanged would have spread that refusal to the
    CLI; `test_validator_accepts_every_registered_gate_name` now makes the
    registry, not this regex, the authority on what a gate may be called.
    """
    # Imported inside the function: `project_config` re-exports this module's
    # names, so a module-level import here would close a cycle.
    from config_trust import resolve
    from default_gates import DEFAULT_GATES
    from project_config import get_config_path, load_project_config, save_config

    if not GATE_NAME_RE.match(name):
        return (
            f"Invalid gate name '{name}': must be lowercase alphanumeric "
            f"with hyphens or underscores."
        )

    cfg = load_project_config(tausik_dir)
    cfg.setdefault("gates", {}).setdefault(name, {})["enabled"] = enable
    save_config(cfg, tausik_dir)

    effective, rejections = resolve(cfg)
    gate = effective.get("gates", {})
    gate = gate.get(name, {}) if isinstance(gate, dict) else {}
    actual = gate.get("enabled") if isinstance(gate, dict) else None
    if actual is None:
        actual = DEFAULT_GATES.get(name, {}).get("enabled", True)

    if bool(actual) == bool(enable):
        return f"Gate '{name}' {'enabled' if enable else 'disabled'}."

    verb = "enabled" if enable else "disabled"
    for r in rejections:
        if r.key == f"gates.{name}.enabled":
            return (
                f"Gate '{name}' NOT {verb} — {r.reason}. The key was written to "
                f"{get_config_path(tausik_dir)} but the effective config keeps {r.applied!r}. "
                f"To change it for real, set it in the user tier "
                f"(~/.tausik/config.json) or in $TAUSIK_MANAGED_CONFIG."
            )
    # Backstop. With the present guard set this is unreachable: a project
    # DISABLE that a trusted tier contradicts produces a rejection above, and a
    # project ENABLE always wins because tightening wins. It stays because the
    # answer is derived from the effective config rather than from the guard
    # table — so if the table grows a case this function has not anticipated,
    # it reports the truth instead of asserting its own assumptions.
    return (
        f"Gate '{name}' NOT {verb} — a trusted config tier sets it to {actual!r} "
        f"and outranks {get_config_path(tausik_dir)}. Change it in ~/.tausik/config.json "
        f"or in $TAUSIK_MANAGED_CONFIG."
    )
