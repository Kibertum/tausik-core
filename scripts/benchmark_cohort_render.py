"""Compact human rendering for natural benchmark cohort inventory."""

from collections.abc import Mapping
from typing import Any


def render_inventory(inventory: Mapping[str, Any]) -> str:
    """Render a pre-comparison inventory without inventing missing values."""
    cohorts = inventory.get("cohorts") or []
    lines = [
        "TAUSIK | host/provider/model | reasoning/speed | dates | tasks | attribution | quality"
    ]
    for cohort in cohorts:
        identity = cohort["identity"]
        version = identity.get("tausik_version") or "legacy/unclassified"
        model = "/".join(
            str(identity.get(key) or "unknown") for key in ("host", "provider", "model")
        )
        mode = "/".join(
            str(identity.get(key) or "unknown") for key in ("reasoning_effort", "speed_mode")
        )
        dates = (
            f"{cohort.get('first_observed_at') or 'unknown'}.."
            f"{cohort.get('last_observed_at') or 'unknown'}"
        )
        quality = cohort.get("quality") or {}
        lines.append(
            f"{version} | {model} | {mode} | {dates} | {cohort['sample_size']} | "
            f"{cohort['response_rounds']} exact response(s) | "
            f"verified {quality.get('verified_tasks', 0)}, "
            f"reviewed {quality.get('reviewed_tasks', 0)}"
        )
    coverage = inventory.get("coverage") or {}
    lines.append(
        "Coverage: "
        f"{coverage.get('accepted_observations', 0)}/{coverage.get('observations', 0)} "
        f"observation(s) belong to {coverage.get('accepted_tasks', 0)} accepted task(s)."
    )
    lines.append(
        f"Unattributed: {(inventory.get('unattributed') or {}).get('observations', 0)} "
        "observation(s)."
    )
    lines.append(
        f"Unaccepted: {(inventory.get('unaccepted') or {}).get('observations', 0)} observation(s)."
    )
    lines.append(str(inventory.get("privacy") or ""))
    return "\n".join(lines)
