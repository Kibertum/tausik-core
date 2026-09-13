"""The settings profile handed to the child process.

The prompt asks the agent not to commit; this makes the request enforceable.
An unattended agent that is merely *told* not to touch git will eventually
touch git — a mode that removes the commands from the allow-list cannot.

Git mode is the profile's main axis but no longer its only content: the
session guard is wired in here too, for every mode, because it must reach the
child without touching `.claude/settings.json` — that file is the human's
interactive configuration and an autonomous run has no business editing it.

Derived from the base profile rather than kept as hand-maintained copies:
copies drift, and the copy that drifts is the restrictive one nobody exercises.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from autoloop.state import profiles_dir  # noqa: E402

GIT_FULL = "full"  # commit + push
GIT_COMMIT = "commit"  # commit, never push
GIT_OFF = "off"  # do not touch the repository at all

GIT_MODES = (GIT_FULL, GIT_COMMIT, GIT_OFF)

_PUSH_RULES = ("Bash(git push:*)",)
_WRITE_RULES = (
    "Bash(git add:*)",
    "Bash(git commit:*)",
    "Bash(git branch:*)",
    "Bash(git checkout -b:*)",
)


def base_profile_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".claude", "settings.autonomy.json")


def profile_path(project_dir: str, git_mode: str) -> str:
    """Generated profiles live under `profiles/`, away from the readings.

    They were siblings of `.tausik/autoloop/<session>.json` once, and the
    dashboard — which takes the freshest JSON in that directory as the current
    measurement — read a profile as one. See `state.state_dir`.
    """
    return os.path.join(profiles_dir(project_dir), f"settings.git-{git_mode}.json")


def build_profile(project_dir: str, git_mode: str) -> str:
    """Return the settings file to hand the child. Generates it every run.

    Generated for `full` too, unlike before: that mode used to hand over the
    base profile as-is, and there is now content every mode needs — the session
    guard — that the base profile cannot carry, because it is also the file a
    human reads to see what a run is allowed to do.

    Falls back to the base profile if it cannot be read — the caller still gets
    a usable path, and the base profile is the conservative-but-working one.
    """
    try:
        with open(base_profile_path(project_dir), encoding="utf-8") as f:
            profile = json.load(f)
    except (OSError, ValueError):
        return base_profile_path(project_dir)

    permissions = profile.setdefault("permissions", {})
    allow = [rule for rule in permissions.get("allow", []) if _allowed(rule, git_mode)]
    permissions["allow"] = allow
    deny = list(permissions.get("deny", []))
    deny.extend(rule for rule in _denied_rules(git_mode) if rule not in deny)
    permissions["deny"] = deny
    add_session_guard(profile)
    profile["$comment"] = [
        f"Generated for git-mode={git_mode}. Do not edit — rebuilt on every run.",
        "Source of truth is .claude/settings.autonomy.json.",
    ]

    target = profile_path(project_dir, git_mode)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
    except OSError:
        return base_profile_path(project_dir)
    return target


SESSION_GUARD_MATCHER = (
    "^(?:Bash|PowerShell|mcp__windows-mcp__PowerShell"
    "|mcp__tausik-project__tausik_session_end)$"
)
SESSION_GUARD_COMMAND = (
    'python -X utf8 "${CLAUDE_PROJECT_DIR}/.claude/scripts/autoloop/session_guard.py"'
)


def add_session_guard(profile: dict) -> dict:
    """Wire the session guard into the child's PreToolUse hooks, in place.

    Added to the generated profile rather than to `.claude/settings.json`
    because the guard is only right under autonomy: an interactive session
    closing itself is the human doing their job. Appended, never assigned —
    a base profile that grows its own hooks must keep them.
    """
    hooks = profile.setdefault("hooks", {})
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list):
        pre = []
        hooks["PreToolUse"] = pre
    # Compared on the command field, not on a JSON dump: the dump escapes the
    # quotes around the script path, so a substring test never matched and the
    # guard was appended on every run.
    already = any(
        isinstance(entry, dict)
        and any(
            isinstance(h, dict) and h.get("command") == SESSION_GUARD_COMMAND
            for h in entry.get("hooks") or []
        )
        for entry in pre
    )
    if not already:
        pre.append(
            {
                "matcher": SESSION_GUARD_MATCHER,
                "hooks": [
                    {"type": "command", "command": SESSION_GUARD_COMMAND, "timeout": 5}
                ],
            }
        )
    return profile


def _allowed(rule: str, git_mode: str) -> bool:
    if git_mode == GIT_COMMIT:
        return rule not in _PUSH_RULES
    if git_mode == GIT_OFF:
        return rule not in _PUSH_RULES + _WRITE_RULES
    return True


def _denied_rules(git_mode: str) -> tuple[str, ...]:
    if git_mode == GIT_COMMIT:
        return _PUSH_RULES
    if git_mode == GIT_OFF:
        return _PUSH_RULES + _WRITE_RULES
    return ()


PROMPT_NOTE = {
    GIT_FULL: "Коммить и пушить закрытые задачи можно без подтверждения.",
    GIT_COMMIT: (
        "Коммитить закрытые задачи можно, пушить — НЕТ: команда push в этом прогоне "
        "недоступна, изменения останутся локальными."
    ),
    GIT_OFF: (
        "Git в этом прогоне не трогай вовсе: команды add/commit/push недоступны. "
        "Просто оставь изменения в рабочем дереве."
    ),
}


def prompt_note(git_mode: str) -> str:
    return PROMPT_NOTE.get(git_mode, PROMPT_NOTE[GIT_FULL])
