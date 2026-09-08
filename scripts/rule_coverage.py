"""What holds each rule on THIS host — by rule, not by host.

kilo-enforcement-through-the-mcp-boundary. Session #230 made the enforcement
notice honest, but per-HOST: on Kilo it says "everything below is instructions,
not checks". That is no longer a lie, and it is still coarser than the truth.

On Kilo, "no closing without a receipt" IS enforced, because closing a task goes
through our tool and our tool refuses. "No code without a task" is NOT enforced,
because the file is written by the host's own editor, which we never see. One
sentence about the whole host cannot say both.

MEASURED FIRST (session #232, AST over harness/claude/mcp/project): 146 declared
tools, 44 mutating handlers, and NOT ONE reaches the backend directly — 29 go
through the service layer and 15 delegate further. So the service layer's
refusals already travel to the MCP boundary. The work is proving and declaring
that, not moving it.

THE SPLIT IS DERIVED FROM WHERE THE ACTION HAPPENS, not from a rule-to-hook
table. A rule whose subject is an operation WE perform (opening a task, closing
it, recording knowledge) is enforced wherever our tools run, which is every host
that can reach the MCP server. A rule whose subject is an operation the HOST
performs (writing a file, running a shell command) can only be enforced by
intercepting the host, which needs a real-time mechanism deployed into its
profile. That distinction is a fact about the action, and it is what decides the
answer — a table of "rule → hook" would drift the way the rules text drifted from
the mechanism (decision #335).

WHAT THIS REFUSES TO CLAIM: that a rule is enforced because a hook file with a
matching name exists. Every `SURFACE` entry below names the tool whose refusal
carries it, and tests/test_rule_coverage.py drives that tool and requires the
refusal. An entry nobody can demonstrate is a defect, not a note.
"""

from __future__ import annotations

import json
import os
from typing import NamedTuple

#: The rule is carried by a mechanism that intercepts the HOST's own action. It
#: holds only where such a mechanism is deployed, and nowhere else.
NEEDS_INTERCEPTION = "needs-interception"

#: The rule is carried by a refusal inside our own tools. It holds on every host
#: that can reach them — which is every host, since the MCP server is what a
#: hostless install still has.
SURFACE = "surface"


class Rule(NamedTuple):
    """One rule, and what kind of thing has to hold it."""

    rule: str
    #: The action the rule governs, in the words of whoever performs it.
    governs: str
    kind: str
    #: For SURFACE rules: the tool whose refusal carries it. The test drives this
    #: tool and requires a refusal, so the field is evidence rather than a label.
    #: For NEEDS_INTERCEPTION rules: the host operation that would have to be
    #: intercepted, which is why our surface cannot help.
    carried_by: str
    #: For NEEDS_INTERCEPTION rules: the deployed artifact(s) that carry this one
    #: rule, ANY of which is enough. Asking instead "does the host deploy
    #: anything?" reported OpenCode as covering all three interception rules,
    #: while its single plugin implements QG-0 and nothing else — an over-claim
    #: produced by the code, which is how over-claims usually arrive.
    #:
    #: Both directions are held live by tests/test_rule_coverage.py: a name here
    #: that no host deploys fails, and so does a name that exists in no source
    #: tree (decision #335).
    artifacts: tuple[str, ...] = ()


#: The critical rules, and what each needs. Order is the reading order of the
#: rules table an agent is handed.
RULES: tuple[Rule, ...] = (
    Rule(
        "QG-0 Context Gate",
        "opening a task without a goal, acceptance criteria or a negative scenario",
        SURFACE,
        "tausik_task_start",
    ),
    Rule(
        "QG-2 Implementation Gate",
        "closing a task without a fresh signed verification",
        SURFACE,
        "tausik_task_done",
    ),
    Rule(
        "Rule 9.2 Session limit",
        "starting work past the session's active-time limit",
        SURFACE,
        "tausik_task_start",
    ),
    Rule(
        "Rule 1 Task before code",
        "writing or editing a file with no active task",
        NEEDS_INTERCEPTION,
        "the host's own Write/Edit tool",
        # Two shapes of the same guarantee: the hook on hosts that take hooks,
        # the QG-0 plugin on OpenCode.
        ("hook:task_gate.py", "plugin:tausik-qg0.js"),
    ),
    Rule(
        "Rule 2 Scope Boundaries",
        "writing outside the task's declared scope_paths",
        NEEDS_INTERCEPTION,
        "the host's own Write/Edit tool and its shell",
        ("hook:scope_write_gate.py", "hook:bash_write_gate.py"),
    ),
    Rule(
        "Rule 10.12 Secret scan",
        "putting a secret into a file or a command line",
        NEEDS_INTERCEPTION,
        "the host's own Write/Edit tool and its shell",
        ("hook:secret_scan.py",),
    ),
    Rule(
        "Memory routing",
        "recording project knowledge into the host's own memory instead of the project's",
        SURFACE,
        "tausik_memory_add",
    ),
)


def deployed_artifacts(profile_dir: str | None) -> set[str]:
    """`hook:<script>` / `plugin:<file>` names actually deployed in a profile.

    Reduced from the capability ids `host_mechanisms` produces, which carry the
    event as well (`hook:PreToolUse:task_gate.py`). The event is what a PARITY
    check compares; here the question is only whether the artifact is present at
    all, so it is dropped rather than being matched loosely.
    """
    from enforcement_coverage import PLUGIN_SUBDIR, SETTINGS_FILES

    found: set[str] = set()
    if not profile_dir or not os.path.isdir(profile_dir):
        return found
    for name in SETTINGS_FILES:
        path = os.path.join(profile_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks, dict):
            continue
        for entries in hooks.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                for hook in entry.get("hooks") or []:
                    if not isinstance(hook, dict):
                        continue
                    for token in str(hook.get("command", "")).replace("\\", "/").split():
                        if token.endswith(".py"):
                            found.add(f"hook:{os.path.basename(token)}")
    plugins = os.path.join(profile_dir, PLUGIN_SUBDIR)
    if os.path.isdir(plugins):
        try:
            for name in os.listdir(plugins):
                if name.endswith((".js", ".mjs")):
                    found.add(f"plugin:{name}")
        except OSError:
            pass
    return found


def coverage_for_host(profile_dir: str | None) -> list[tuple[Rule, str]]:
    """(rule, what holds it here) for every rule, derived from the deployment.

    A SURFACE rule holds everywhere: our tools are the enforcement point and they
    travel with the MCP server. A NEEDS_INTERCEPTION rule holds only where the
    artifact that carries THAT rule is deployed — asking whether the host deploys
    anything at all reported OpenCode as covering rules its plugin never touches.
    """
    deployed = deployed_artifacts(profile_dir)
    out: list[tuple[Rule, str]] = []
    for rule in RULES:
        if rule.kind == SURFACE:
            out.append((rule, SURFACE))
        elif deployed.intersection(rule.artifacts):
            out.append((rule, "realtime"))
        else:
            out.append((rule, NEEDS_INTERCEPTION))
    return out


def render_rule_notice(profile_dir: str | None) -> str:
    """The per-rule paragraph a host's rules file carries.

    Replaces nothing: the per-host sentence still opens the file and answers "are
    these checks or instructions". This says which of them are which, because on
    a host without a mechanism the answer differs BY RULE and a single sentence
    cannot carry two answers.
    """
    if profile_dir is None:
        # Host-agnostic file (AGENTS.md, which codex and kilo share). Which rules
        # are intercepted depends on a host nobody has named here, and answering
        # "none of them" would be a guess dressed as a measurement (decision
        # #334). The UNKNOWN notice already says the answer is unknown.
        return ""
    rows = coverage_for_host(profile_dir)
    unenforced = [r for r, holds in rows if holds == NEEDS_INTERCEPTION]
    if not unenforced:
        return ""
    held = ", ".join(r.rule for r, holds in rows if holds != NEEDS_INTERCEPTION)
    missing = ", ".join(f"**{r.rule}**" for r in unenforced)
    # Where the host deploys NOTHING, this paragraph also carries the mechanism
    # fact, and `build_full_body` drops the separate host sentence: two
    # paragraphs saying one thing cost a line on every turn.
    # ASKED OF THE SAME PROBE the host sentence uses. Deriving it from the
    # rule rows instead made the two disagree: a host deploying five hooks none
    # of which is `task_gate.py` has a mechanism AND leaves Rule 1 unintercepted,
    # and both sentences are true. Two probes answering one question is how a
    # page ends up contradicting itself.
    from enforcement_coverage import deployed_enforcement

    found = deployed_enforcement(profile_dir)
    deploys_nothing = not (found.get("hooks") or found.get("plugins"))
    lead = (
        "**NO REAL-TIME MECHANISM IS DEPLOYED HERE** — bootstrap wrote no hook "
        "and no plugin into this host's profile, which states what TAUSIK "
        "deployed, not what the host supports: TAUSIK does not generate a "
        "real-time payload for this host yet. "
        if deploys_nothing
        else ""
    )
    return (
        f"{lead}WHICH rules are checked here differs BY RULE. Refused by `tausik_*` "
        f"/ the CLI on every host, this one included: {held}. NOT enforced here: "
        f"{missing} — each governs something this host's own editor or shell does, "
        f"which nothing of ours observes.\n"
    )
