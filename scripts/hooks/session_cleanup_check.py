#!/usr/bin/env python3
"""Stop hook — session hygiene reminder.

Sibling to keyword_detector.py. Checks at each turn end whether the agent is
leaving loose ends: open exploration (SENAR 5.1), tasks sitting in review
status, or session nearing the 180-minute limit (Rule 9.2). Emits a stderr
reminder so the user sees it but the turn still completes.

Always exits 0. Non-blocking. Suppressed via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import tausik_path as _tausik_path  # noqa: E402


def _session_warn_min(project_dir: str) -> int:
    import json

    cfg_path = os.path.join(project_dir, ".tausik", "config.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            data = json.load(f)
        v = data.get("session_warn_threshold_minutes", 150)
        n = int(v) if isinstance(v, (int, float)) else 150
        return max(1, n)
    except (OSError, ValueError, TypeError):
        return 150


SESSION_WARN_MIN = 150  # legacy fallback when project_dir unknown


def _run(cmd: str, args: list[str], project_dir: str, timeout: int = 4) -> str:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        result = subprocess.run(
            [cmd, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=project_dir,
            env=env,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _has_open_exploration(out: str) -> bool:
    if not out:
        return False
    lowered = out.lower()
    if "no active exploration" in lowered or "нет активной" in lowered:
        return False
    return "exploration" in lowered or "title" in lowered or "#" in out


def _review_task_count(out: str) -> int:
    """Count rows in task list output that look like data lines."""
    if not out or "No tasks" in out or "(none)" in out:
        return 0
    count = 0
    for line in out.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("slug", "---")):
            continue
        count += 1
    return count


def _session_overrun_minutes(status_out: str, warn_min: int = SESSION_WARN_MIN) -> int:
    if not status_out:
        return 0
    match = re.search(r"(\d+)\s*min active", status_out, re.IGNORECASE)
    if not match:
        match = re.search(r"running for\s+(\d+)\s*min", status_out, re.IGNORECASE)
    if not match:
        return 0
    minutes = int(match.group(1))
    return minutes if minutes >= warn_min else 0


def build_warnings(project_dir: str) -> list[str]:
    tausik_cmd = _tausik_path(project_dir)
    if not tausik_cmd:
        return []

    warnings: list[str] = []

    explore_out = _run(tausik_cmd, ["explore", "current"], project_dir)
    if _has_open_exploration(explore_out):
        warnings.append(
            "- **Open exploration detected.** End it (`tausik_explore_end`) "
            "or keep momentum — don't stop a turn mid-investigation without recording findings."
        )

    review_out = _run(tausik_cmd, ["task", "list", "--status", "review"], project_dir)
    review_count = _review_task_count(review_out)
    if review_count:
        warnings.append(
            f"- **{review_count} task(s) in review.** "
            "Close them with `tausik_task_done --ac-verified` "
            "or mark as blocked if waiting on someone."
        )

    status_out = _run(tausik_cmd, ["status"], project_dir)
    minutes = _session_overrun_minutes(status_out, _session_warn_min(project_dir))
    if minutes:
        warnings.append(
            f"- **Session running {minutes} min** (limit 180). "
            "Run `/checkpoint` now to save state, or `/end` to close cleanly."
        )

    return warnings


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0

    # Don't fire when keyword_detector has already blocked the same turn
    if payload.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(tausik_db):
        return 0

    warnings = build_warnings(project_dir)
    if not warnings:
        return 0

    header = "[TAUSIK session hygiene] Loose ends before stopping:"
    print("\n".join([header, *warnings]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
