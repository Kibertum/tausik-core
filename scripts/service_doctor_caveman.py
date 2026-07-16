"""Interop check for a user-installed caveman (github.com/JuliusBrussee/caveman).

TAUSIK ships its OWN output-economy mode (`output_mode: caveman` → the caveman-style
directive baked into the generated rules). A user may ALSO have installed the real
caveman skill, which on Claude Code writes hook files into the config dir and merges
`settings.json`. Both can coexist, but the overlap is worth surfacing rather than
leaving the user to discover it:

  * If real caveman is installed, say so — its compression stacks on top of ours, and
    running both directives is redundant (mild token waste, not a fault).
  * If caveman wired a hook into the SAME `.claude/settings.json` TAUSIK owns, name it:
    both TAUSIK's SessionStart hook and caveman's fire, and a user debugging hook order
    should know both are there. A silent overlap is exactly what TAUSIK refuses to hide.

Detection only — never mutates, never raises (a broken check must not crash doctor).
Silent when no caveman artifact is present.
"""

from __future__ import annotations

import json
import os

# caveman's per-agent artifacts, relative to the project root. From its installer layout:
# rule files for Cursor/Windsurf/Cline, and a session flag for Claude Code.
_CAVEMAN_MARKERS = (
    os.path.join(".cursor", "rules", "caveman.mdc"),
    os.path.join(".windsurf", "rules", "caveman.md"),
    os.path.join(".clinerules", "caveman.md"),
    ".caveman-active",
)

_CLAUDE_SETTINGS = os.path.join(".claude", "settings.json")


def _installed_markers(project_dir: str) -> list[str]:
    return [rel for rel in _CAVEMAN_MARKERS if os.path.exists(os.path.join(project_dir, rel))]


def _hook_commands(settings: dict) -> list[str]:
    """Every hook `command` string in a settings.json, regardless of event/matcher shape."""
    out: list[str] = []
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return out
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            inner = entry.get("hooks")
            candidates = inner if isinstance(inner, list) else [entry]
            for h in candidates:
                if isinstance(h, dict) and isinstance(h.get("command"), str):
                    out.append(h["command"])
    return out


def _caveman_in_claude_settings(project_dir: str) -> bool:
    """True if a caveman hook is wired into the .claude/settings.json TAUSIK also owns.

    Parsed as JSON and matched only inside hook COMMANDS. A bare substring search over the
    raw file cried wolf on anything that merely contained the word: a project named
    `caveman-widgets`, a `scripts/caveman_lint.py` hook, a comment. A false warning in
    doctor is not harmless — it trains people to ignore doctor.
    """
    path = os.path.join(project_dir, _CLAUDE_SETTINGS)
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(settings, dict):
        return False
    return any("caveman" in cmd.lower() for cmd in _hook_commands(settings))


def check_caveman_interop(project_dir: str) -> list[tuple[str, str, str]]:
    """Doctor findings for caveman coexistence, or [] when caveman is not present.

    Each finding is (severity, label, detail), severity in {ok, warn}. Never a `fail`:
    a co-installed caveman is not an error, and this check has no authority to block.
    """
    markers = _installed_markers(project_dir)
    in_settings = _caveman_in_claude_settings(project_dir)
    if not markers and not in_settings:
        return []

    label = "caveman interop"
    out: list[tuple[str, str, str]] = []

    where = ", ".join(markers) if markers else _CLAUDE_SETTINGS
    out.append(
        (
            "ok",
            label,
            f"external caveman detected ({where}). It stacks on top of TAUSIK's own "
            "`output_mode: caveman`; running both is redundant, not harmful — set "
            "`output_mode: off` in .tausik/config.json if you prefer caveman to own compression.",
        )
    )

    if in_settings:
        out.append(
            (
                "warn",
                label,
                "caveman is wired into `.claude/settings.json`, which TAUSIK also manages. "
                "Both its hook and TAUSIK's SessionStart hook will fire — expected, but if you "
                "debug hook order or re-bootstrap, know both are present.",
            )
        )
    return out
