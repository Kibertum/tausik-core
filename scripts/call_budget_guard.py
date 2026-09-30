"""In an unattended run the call budget stops being advice and becomes a ceiling.

WHY TWO TIERS AND NOT ONE. Interactively an overrun is information: the author sees the
warning at close and recalibrates the next estimate. Unattended it is a hazard — a driver
walking a release composition will spend a whole session on one task and stop by
exhaustion rather than by plan, and the owner finds out in the morning.

THE MULTIPLIER IS MEASURED, not borrowed. Over 651 closures that carry both a budget and
an actual: median ratio 0.58 — the usual task lands at under two thirds of its estimate —
p75 0.93, p90 1.60, p99 5.80, worst 47.5. Past 1.5x sits 11% of closures, past 2x 8%, past
2.5x 4%, past 3x 3%. So 1.5x is where calibration noise ends and 2x is where an overrun
stops being noise at all: the warning keeps its old threshold, the refusal takes 2x.

ARMED BY AN ENVIRONMENT FLAG rather than a config key, because the mode is a property of
THIS RUN and not of the project: the same repository is worked interactively and by a
driver, and a setting on disk would make one of them wrong. Absent flag, nothing here can
refuse anything.
"""

from __future__ import annotations

import os
from typing import Any

#: Where the advisory already sits (`service_recording.record_call_actual`). Kept here as
#: a name so the two thresholds are read side by side rather than found apart.
WARN_MULTIPLIER = 1.5

#: The refusal, at the point where an overrun stops being calibration noise: 8% of
#: closures, against 11% at the warning threshold.
BLOCK_MULTIPLIER = 2.0

#: Set to arm the ceiling for one run. Read from the environment, never from config.
ARM_ENV = "TAUSIK_AUTONOMOUS_BUDGET_BLOCK"


def is_armed(environ: dict[str, str] | None = None) -> bool:
    """Whether this run asked for a ceiling. Anything falsy-looking is unarmed.

    The values are spelled out rather than taken as truthy, so `=0` and `=false` mean what
    a reader expects: a flag that arms on "false" would be a trap in a shell script.
    """
    raw = (environ if environ is not None else os.environ).get(ARM_ENV, "")
    return str(raw).strip().lower() not in ("", "0", "false", "no", "off")


def overrun(task: dict[str, Any]) -> float | None:
    """`call_actual / call_budget`, or ``None`` when the question does not apply.

    ``None`` for a task with no declared budget, and that is a decision rather than a
    convenience: absence of a budget is not a budget of zero, and treating it as one would
    refuse every task nobody estimated.
    """
    budget, actual = task.get("call_budget"), task.get("call_actual")
    if not isinstance(budget, int) or budget <= 0:
        return None
    if not isinstance(actual, int) or actual < 0:
        return None
    return actual / budget


def breach(task: dict[str, Any], environ: dict[str, str] | None = None) -> str:
    """The refusal text when an ARMED run is past the ceiling, else ``""``.

    Empty for everything else: unarmed runs, tasks without a budget, tasks within the
    ceiling. The refusal names the three numbers and the two ways out, because a stop that
    does not say what to change gets worked around rather than obeyed.
    """
    try:
        if not is_armed(environ):
            return ""
        ratio = overrun(task)
        if ratio is None or ratio <= BLOCK_MULTIPLIER:
            return ""
    except Exception:  # noqa: BLE001 — a guard that raises is worse than one that misses
        return ""
    slug = task.get("slug", "?")
    return (
        f"ПОТОЛОК ВЫЗОВОВ: '{slug}' израсходовала {task['call_actual']} вызовов при бюджете "
        f"{task['call_budget']} — это {ratio:.1f}× при потолке {BLOCK_MULTIPLIER:g}×. "
        f"Автономный режим взведён ({ARM_ENV}), поэтому это ОТКАЗ, а не совет: неприсмотренный "
        "прогон иначе тратит смену на одну задачу и останавливается по исчерпанию, а не по "
        "плану. Пересчитайте бюджет по замеру или разбейте задачу — медиана по 651 закрытию "
        "0,58 бюджета, так что 2× это не тесно."
    )
