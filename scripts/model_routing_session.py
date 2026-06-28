"""Persist per-task model recommendation between TAUSIK invocations.

When `task start` runs, the recommendation banner names the cheapest model
that still fits the task's complexity. Claude Code itself does NOT accept a
programmatic mid-session model switch, so the banner text alone is easy to
miss. This module persists the recommendation in `.tausik/.task_recommendation.json`
so that:

  * a follow-up `tausik config show` / hint command can re-surface it,
  * skill auto-rebuild on next session start can choose model overlays,
  * any future wrapper that launches Claude Code can apply the suggested
    profile via `TAUSIK_MODEL_PROFILE`.

Storage is intentionally separate from `.session.json` (skill_profile_session):
that file's `model` key tracks the AGREED profile (env > config > auto), while
the recommendation here tracks the SUGGESTED profile for the active task. The
two answer different questions — keep them apart.

Schema (`.tausik/.task_recommendation.json`):
    {
        "schema_version": 1,
        "slug": "<task-slug>",
        "complexity": "simple" | "medium" | "complex" | null,
        "model": "claude-haiku-4-5" | ...,
        "display": "Haiku 4.5" | ...,
        "recorded_at": "<ISO-8601>"
    }

All operations are best-effort: malformed JSON, missing dir, OS errors —
degrade silently with a stderr WARN. Persisting a bogus recommendation is
worse than persisting none, so we whitelist the model id against the routing
table before writing.

Env knob: TAUSIK_DISABLE_TASK_RECOMMENDATION=1 makes record/clear no-ops
without raising. Useful in CI or hostile sandboxes.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Final

_FILENAME: Final[str] = ".task_recommendation.json"
_SCHEMA_VERSION: Final[int] = 1
_VALID_COMPLEXITIES: Final[set[str | None]] = {"simple", "medium", "complex", None}


def _path(tausik_dir: str) -> str:
    return os.path.join(tausik_dir, _FILENAME)


def _disabled() -> bool:
    return os.environ.get("TAUSIK_DISABLE_TASK_RECOMMENDATION", "").strip() == "1"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_active_task_recommendation(
    tausik_dir: str, slug: str, complexity: str | None
) -> dict[str, Any] | None:
    """Persist the recommendation for the currently-active task.

    Returns the written dict on success, None when skipped (env-disabled,
    invalid input, IO error). Never raises — never blocks task_start.
    """
    if _disabled():
        return None
    if not slug or not isinstance(slug, str):
        return None
    if complexity not in _VALID_COMPLEXITIES and complexity is not None:
        # Unknown complexity falls through to suggest_model's default — record
        # it as None so the consumer doesn't trust an arbitrary string.
        complexity = None
    try:
        from model_routing import suggest_model

        s = suggest_model(complexity)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "slug": slug.strip(),
            "complexity": complexity,
            "model": s["model"],
            "display": s["display"],
            "recorded_at": _utcnow_iso(),
        }
        os.makedirs(tausik_dir, exist_ok=True)
        path = _path(tausik_dir)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)
        return payload
    except OSError as e:
        print(
            f"WARN [model_routing_session]: write failed for {tausik_dir}: {e}",
            file=sys.stderr,
        )
        return None
    except Exception as e:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        # suggest_model itself never raises, but any future regression should
        # not propagate up into task_start. Surface on stderr, keep going.
        print(
            f"WARN [model_routing_session]: record failed: {e}",
            file=sys.stderr,
        )
        return None


def read_active_task_recommendation(tausik_dir: str) -> dict[str, Any] | None:
    """Return the persisted recommendation dict, or None if absent/invalid."""
    if _disabled():
        return None
    path = _path(tausik_dir)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(
            f"WARN [model_routing_session]: malformed {path}: {e} — ignoring",
            file=sys.stderr,
        )
        return None
    if not isinstance(data, dict):
        return None
    # Validate the minimal contract — partial writes / hand-edits should be
    # treated as missing rather than yielding a half-broken dict.
    required = ("slug", "model", "display", "recorded_at")
    if not all(isinstance(data.get(k), str) and data.get(k) for k in required):
        return None
    return data


def clear_active_task_recommendation(tausik_dir: str) -> bool:
    """Remove the recommendation file. Returns True if a file was deleted."""
    if _disabled():
        return False
    path = _path(tausik_dir)
    if not os.path.isfile(path):
        return False
    try:
        os.remove(path)
        return True
    except OSError as e:
        print(
            f"WARN [model_routing_session]: delete failed for {path}: {e}",
            file=sys.stderr,
        )
        return False
