"""Reporting a figure, SENAR 1.5 §9.4 (1.10, story F).

(a) The method is disclosed with the figure: population, record, formula,
    period — `METHODS` below, printed by `tausik metrics`.
(b) A figure computed from self-made records measures what was recorded, not
    what occurred — stated once for the class, naming the record each such
    metric depends on.
(c) A self-set target carries its basis — `metric_targets` in the config;
    a target without a basis is not used, and `metrics target` refuses to set
    one without `--basis`.
(d) A crossed target is escalated, not quietly moved — the first observation
    of a crossing records a `metric_target_crossed` event; recovery clears it.

Until 1.10 the report printed "FPSR 91.2%" and "DER 9.5%" with no population
or period, and the end skill carried "FPSR > 85%", "DER < 5%" with no basis —
while DER sat above its target and nothing said so.
"""

from __future__ import annotations

import json
from typing import Any

METHODS: dict[str, dict[str, Any]] = {
    "throughput": {
        "population": "tasks with status done; all sessions",
        "record": "tasks.status, sessions",
        "formula": "done tasks / sessions",
        "self_made": False,
    },
    "lead_time": {
        "population": "done tasks with created_at and completed_at",
        "record": "tasks.created_at, tasks.completed_at",
        "formula": "mean(completed_at - created_at), hours",
        "self_made": False,
    },
    "fpsr": {
        "population": "done tasks",
        "record": "tasks.attempts (a start or an unblock adds one; a red verify does not)",
        "formula": "done tasks with attempts = 1 / done tasks",
        "self_made": True,
    },
    "der": {
        "population": "done tasks that are not defects",
        "record": "tasks.defect_of (a defect task names its origin)",
        "formula": "distinct tasks named as defect_of by any task / done non-defect tasks",
        "self_made": True,
    },
    "dead_end_rate": {
        "population": "all tasks, any status",
        "record": "memory rows of type dead_end",
        "formula": "dead-end records / tasks",
        "self_made": True,
    },
    "manual_intervention": {
        "population": "supervision events of category bypass (a subset, never summed with them)",
        "record": "events whose action names a manual intervention (§8.6(j))",
        "formula": "count of manual-intervention events",
        "self_made": True,
    },
}
PERIOD = "all time (the whole task table)"

#: Defaults with their basis (§9.4(c)). A project may override in
#: `.tausik/config.json` → `metric_targets`; an override without `basis` is
#: ignored and says so.
DEFAULT_TARGETS: dict[str, dict[str, Any]] = {
    "fpsr": {
        "min": 85.0,
        "basis": "carried by the end skill since before 1.9; this project measured 91.2% "
        "over 1517 done tasks",
        "measured_on": "2026-09-23",
        "measured_by": "tausik metrics",
    },
    "der": {
        "max": 5.0,
        "basis": "carried by the end skill since before 1.9; this project measured 9.5%, "
        "above the target — kept, not moved, and escalated (§9.4(d))",
        "measured_on": "2026-09-23",
        "measured_by": "tausik metrics",
    },
}


def targets(cfg: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Effective targets and notes about overrides that lack a basis."""
    out = {k: dict(v) for k, v in DEFAULT_TARGETS.items()}
    notes: list[str] = []
    for name, spec in ((cfg or {}).get("metric_targets") or {}).items():
        if not isinstance(spec, dict) or not str(spec.get("basis") or "").strip():
            notes.append(f"target for {name} has no basis — not used (SENAR 1.5 §9.4(c))")
            continue
        if "min" not in spec and "max" not in spec:
            notes.append(f"target for {name} has neither min nor max — not used")
            continue
        out[name] = dict(spec)
    return out, notes


def figure(m: dict[str, Any], name: str, unit: str = "%") -> str:
    """The figure, or "no population" when its denominator is empty (§9.4(a))."""
    pops = m.get("populations") or {}
    if name in pops and not pops[name]:
        return "no population (0 in the denominator)"
    return f"{m.get(name)}{unit}"


def crossed(value: float | None, spec: dict[str, Any]) -> bool:
    if value is None:
        return False
    if "min" in spec and value < float(spec["min"]):
        return True
    return "max" in spec and value > float(spec["max"])


def escalate(be: Any, name: str, value: float | None, spec: dict[str, Any]) -> bool:
    """Record the first observation of a crossing; clear it on recovery. True if recorded now."""
    key = f"metric_crossed:{name}"
    if not crossed(value, spec):
        if be.meta_get(key):
            be.meta_delete(key)
        return False
    if be.meta_get(key):
        return False
    be.meta_set(key, str(value))
    be.event_add(
        "metric",
        name,
        "metric_target_crossed",
        json.dumps({"value": value, "target": {k: spec[k] for k in ("min", "max") if k in spec}}),
    )
    return True


def method_lines(m: dict[str, Any], cfg: dict[str, Any] | None, be: Any = None) -> list[str]:
    """The §9.4 block of the metrics report."""
    lines = ["\n--- How these figures are computed (SENAR 1.5 §9.4) ---", f"Period: {PERIOD}"]
    for name, meth in METHODS.items():
        lines.append(f"  {name}: {meth['formula']} — population: {meth['population']}")
    self_made = [f"{n} ({METHODS[n]['record']})" for n in METHODS if METHODS[n]["self_made"]]
    lines.append(
        "  Self-made records: "
        + "; ".join(self_made)
        + " — these figures measure what was recorded, not what occurred (§9.4(b))."
    )
    tg, notes = targets(cfg)
    pops = m.get("populations") or {}
    for name, spec in tg.items():
        value = None if (name in pops and not pops[name]) else m.get(name)
        bound = f">= {spec['min']}%" if "min" in spec else f"<= {spec['max']}%"
        state = (
            "no population" if value is None else ("CROSSED" if crossed(value, spec) else "within")
        )
        when = (
            f"; measured {spec['measured_on']} by `{spec['measured_by']}`"
            if spec.get("measured_on")
            else ""
        )
        lines.append(f"  target {name} {bound}: {state} (basis: {spec['basis']}{when})")
        if be is not None:
            try:
                escalate(be, name, value, spec)
            except Exception as e:  # noqa: BLE001 — recording must never cost the report
                import sys

                print(f"metric escalation for {name} failed: {e}", file=sys.stderr)
    lines += [f"  {n}" for n in notes]
    return lines


def open_crossings(be: Any) -> list[str]:
    """Targets whose crossing is recorded and not yet recovered — for `status`."""
    out = []
    for name in METHODS:
        try:
            value = be.meta_get(f"metric_crossed:{name}")
        except Exception:  # noqa: BLE001 — status must never die on this
            return []
        if value:
            out.append(f"{name}={value}")
    return out


def set_target(cfg: dict[str, Any], name: str, bound: str, value: float, basis: str) -> str:
    """`metrics target` — refuses a target without a basis (§9.4(c)). Mutates cfg."""
    if name not in METHODS:
        raise ValueError(f"unknown metric {name!r}; known: {', '.join(METHODS)}")
    if bound not in ("min", "max"):
        raise ValueError("bound must be 'min' or 'max'")
    if not basis.strip():
        raise ValueError("a target needs --basis: what the number rests on (SENAR 1.5 §9.4(c))")
    from datetime import date

    cfg.setdefault("metric_targets", {})[name] = {
        bound: float(value),
        "basis": basis.strip(),
        "measured_on": date.today().isoformat(),
        "measured_by": "tausik metrics target",
    }
    return f"target {name} {bound} {float(value)} set (basis: {basis.strip()})"
