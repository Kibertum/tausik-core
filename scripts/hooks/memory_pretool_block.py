#!/usr/bin/env python3
"""PreToolUse hook: refuse writes that route project knowledge off-project.

Layer 2 of the memory-route enforcement (`scripts/memory_sinks.py` holds the
deny-list and describes all three layers). This is the fast, per-harness layer:
it refuses the write BEFORE it happens, where the universal gate can only refuse
the close afterwards.

Two vectors, one rule. `Write` / `Edit` / `MultiEdit` carry the path in
`tool_input.file_path`; a `Bash` command carries it in shell syntax and is
parsed with `bash_write_parse.write_targets` — the same parser
`bash_write_gate` uses for QG-0. Covering only the first would leave `cat >>
~/.claude/projects/x/memory/notes.md <<EOF` as a one-line bypass of the rule the
Write path enforces, which is exactly the hole l26-hook-contract-review found
for QG-0 and closed (Decision #162).

Reach: home-scope sinks (`~/.claude/**/memory/`) AND in-tree sinks
(`.cursor/rules/`, `.github/copilot-instructions.md`, `.aider*`, …). The gate
sees only the in-tree half — this hook is the only layer that reaches the
former, which is why it exists per-harness at all.

Bypass: if the last user turn in the transcript contains the marker
`confirm: cross-project`, the hook allows the write (escape hatch for truly
cross-project preferences). For an in-tree path that is a permanent, per-project
exemption instead: `.tausik/config.json` -> `gates.memory_route.allow`.

Exit codes: 0 = allow, 2 = block.

Skip flags (both honored when set to any non-empty value, matching the rest
of the hook suite; each leaves a supervision-bypass trace):
  - TAUSIK_SKIP_HOOKS        umbrella flag, disables every hook in the suite
  - TAUSIK_SKIP_MEMORY_HOOK  disables just this memory guard
Weakening a supervision guard is never silent (release-1.8 thesis): each skip
path emits a distinct `bypass_*` event via `emit_supervision_bypass` so the
count of switch-offs stays falsifiable.
"""

from __future__ import annotations

import json
import os
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HOOKS_DIR)
sys.path.insert(1, os.path.dirname(_HOOKS_DIR))  # scripts/ — for memory_sinks

from _common import (  # noqa: E402
    is_tausik_project,
    last_user_prompt_text,
    marker_present_anchored,
)
from memory_sinks import (  # noqa: E402
    DEFAULT_SINKS,
    SinkRule,
    find_foreign_sinks,
    is_foreign_sink,
    redirect_message,
)

_BYPASS_MARKER = "confirm: cross-project"
_PATH_TOOLS = ("Write", "Edit", "MultiEdit")


def _read_stdin_json() -> dict:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def is_in_claude_memory(file_path: str) -> bool:
    """True for `~/.claude/**/memory/**` specifically — NOT for every sink.

    Deliberately narrow, and imported by `memory_posttool_audit`, which scans
    the CONTENT of an auto-memory write for project markers. Widening this to
    the whole deny-list would silently repoint that audit at files it was never
    written to judge, so the broad question has its own name below.
    """
    rule = _claude_home_rule()
    if rule is None:
        return False
    return is_foreign_sink(file_path, sinks=(rule,)) is not None


def _claude_home_rule() -> SinkRule | None:
    for rule in DEFAULT_SINKS:
        if rule.name == "claude_home_memory":
            return rule
    return None


def _policy(project_dir: str) -> tuple[tuple[SinkRule, ...], tuple[str, ...]]:
    """`(sinks, allow)` for this project — configured policy, defaults on failure.

    A hook must not block on an unreadable config: the gate is the layer that
    fails closed on unknown policy, and it runs on the same tree minutes later.
    Duplicating fail-closed here would turn one typo in `config.json` into an
    agent that cannot write ANY file until it is fixed — a self-inflicted outage
    where the gate gives a readable error at close time instead.
    """
    try:
        from memory_sinks import sinks_from_config  # noqa: PLC0415
        from project_config import load_config  # noqa: PLC0415

        sinks, allow, _err = sinks_from_config(load_config(os.path.join(project_dir, ".tausik")))
        return sinks, allow
    except Exception:  # noqa: BLE001 — defaults still protect; the gate reports the config error
        return DEFAULT_SINKS, ()


def _targets(event: dict, project_dir: str) -> list[str]:
    """Every path this tool call writes, for both vectors.

    A Bash command that did not TOKENIZE yields nothing here, and that is a
    deliberate difference from `bash_write_gate`. The parser's regex fallback
    over-detects by design; for QG-0 the worst case is being asked for a task
    the write needed anyway, but this hook's block accuses the agent of leaking
    project knowledge and offers only two exits — a `confirm: cross-project`
    marker that would be a lie, or a permanent config exemption for a one-off
    command. A guard that fires on a mere quoted MENTION of a sink path teaches
    the agent to reach for the escape hatch, which costs more than the writes it
    would have caught. Found by dogfooding: this hook blocked a diagnostic
    `python -c` over the garbage "path" `.cursor/rules/a.mdc/"',`.

    The gap is not silent and not unbounded: the degradation is recorded as a
    countable supervision event, and the in-tree half of the deny-list is judged
    again by the `memory_route` gate and the pre-commit hook before anything can
    be committed.
    """
    tool = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    if tool in _PATH_TOOLS:
        fp = tool_input.get("file_path")
        return [fp] if isinstance(fp, str) and fp else []
    # Which shells carry a command is `shell_channel`'s answer. The literal
    # `!= "Bash"` that stood here covered exactly one of the two shell tools the
    # agent is handed on win32, so `Set-Content ~/.claude/.../memory/x.md` — the
    # very write this hook exists to stop — went straight through.
    import shell_channel  # noqa: PLC0415

    command = shell_channel.command_of(event)
    if command is None:
        return []
    from write_confidence import CONFIDENCE_REGEX_FALLBACK  # noqa: PLC0415

    raw_targets, confidence = shell_channel.write_targets_with_confidence(str(tool), command)
    if confidence == CONFIDENCE_REGEX_FALLBACK:
        if raw_targets:
            from _common import emit_supervision_degradation  # noqa: PLC0415

            # The reason names the CHANNEL that failed to parse. `bash` is
            # preserved verbatim for the Bash tool because it is the string the
            # docs and the changelog already quote; a PowerShell miss counts
            # under its own name rather than being filed as a Bash one, or the
            # telemetry would attribute the gap to the wrong parser.
            emit_supervision_degradation(
                project_dir,
                f"unparseable_{str(tool).lower()}",
                "memory_pretool_block",
                f"command did not tokenize; {len(raw_targets)} guessed target(s) "
                f"not judged (over-detection would false-positive)",
            )
        return []

    out: list[str] = []
    for raw in raw_targets:
        # A shell redirect is relative to the shell's cwd — the project dir —
        # not to wherever this hook process launched. Same resolution
        # bash_write_gate applies, so the two agree on what a target is.
        expanded = os.path.expanduser(raw)
        cand = expanded if os.path.isabs(expanded) else os.path.join(project_dir, expanded)
        if cand not in out:
            out.append(cand)
    return out


def _bypass_present(transcript_path: str) -> bool:
    prompt = last_user_prompt_text(transcript_path)
    return marker_present_anchored(prompt, _BYPASS_MARKER)


def main() -> int:
    from _common import force_utf8_io  # noqa: PLC0415

    force_utf8_io()
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    # Both skip paths honored and instrumented. The umbrella TAUSIK_SKIP_HOOKS
    # disables this guard too (parity with the rest of the hook suite); the
    # specific TAUSIK_SKIP_MEMORY_HOOK disables only this one. Either way the
    # bypass is recorded — telemetry is the real protection, not flag-selection
    # (Decision #159). emit_supervision_bypass is best-effort: it never raises,
    # so a DB error cannot turn a skip into a block.
    if os.environ.get("TAUSIK_SKIP_HOOKS") or os.environ.get("TAUSIK_SKIP_MEMORY_HOOK"):
        from _common import emit_supervision_bypass  # noqa: PLC0415

        vector = "skip_hooks" if os.environ.get("TAUSIK_SKIP_HOOKS") else "skip_memory_hook"
        emit_supervision_bypass(project_dir, vector, "memory_pretool_block")
        return 0

    # v1.3.4 (med-batch-1-hooks #4): detect TAUSIK by .tausik/ dir, not
    # tausik.db file — covers the bootstrap-but-not-init window.
    if not is_tausik_project(project_dir):
        return 0

    event = _read_stdin_json()
    import shell_channel  # noqa: PLC0415

    if event.get("tool_name") not in (*_PATH_TOOLS, *shell_channel.SHELL_TOOLS):
        return 0

    targets = _targets(event, project_dir)
    if not targets:
        return 0

    sinks, allow = _policy(project_dir)
    hits = find_foreign_sinks(targets, project_dir, sinks=sinks, allow=allow)
    if not hits:
        return 0

    if _bypass_present(event.get("transcript_path") or ""):
        return 0

    from _common import cli_invocation  # noqa: PLC0415

    print(
        "BLOCKED: this write routes project knowledge into another agent's memory.\n"
        + redirect_message(hits, cli_invocation(), project_dir)
        + "\nIf it really is a cross-project user preference, reply with the marker "
        "`confirm: cross-project` in your next message, then retry.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
