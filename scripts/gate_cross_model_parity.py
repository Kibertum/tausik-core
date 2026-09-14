"""Did a capability go host-only without anyone saying so?

cross-model-parity-has-no-gate. TAUSIK is cross-model by the owner's requirement
and by the second promise of 1.9 — "higher development quality on ANY model". A
capability that lands for one host and not another breaks that promise quietly,
because nothing compares the hosts.

WHAT IS COMPARED, AND WITH WHOM. Hosts are compared only with the hosts that
share their extension point. OpenCode enforces through a plugin and Claude
through hook commands; asking whether `tausik-qg0.js` is missing from Claude is a
question with no meaning, and answering it would have filled this gate with 23
false differences on the day it landed. Whether a host has an extension point AT
ALL is a separate statement, already made by the enforcement notice each host's
rules file opens with and by `doctor` — this gate does not restate it.

WHAT IT REFUSES TO DO is demand sameness. Cursor has no extension point; there is
nothing to be equal to. The subject is whether a difference is NAMED.

FOUND BY BUILDING IT, and the reason it exists: the parity test that already
guarded claude against qwen compared SCRIPT BASENAMES, so the two looked
identical at 23 hooks each — while six of those hooks were registered on
different MATCHERS. `task_done_verify.py` fires on four tool patterns under Qwen
and one under Claude; `task_call_counter.py` counts every tool under Qwen and
five under Claude. A parity check that cannot see that is a parity check that
passes while the hosts diverge.
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from host_mechanisms import (  # noqa: E402
    KIND_HOOK,
    MECHANISM_BUILDERS,
    cross_check_against_disk,
    matcher_table,
)

#: The gate's subject is the host layer. A task that does not touch it is not
#: asked about cross-host parity: a gate that runs on everything becomes a tax,
#: and a tax gets switched off.
HOST_LAYER_PREFIXES = ("bootstrap/", "scripts/hooks/", "harness/opencode/")

#: Two spellings of "every tool", one per host dialect. Normalising them is not a
#: convenience: without it every hook registered for all tools reads as a
#: difference, and a gate whose output is mostly noise is one nobody reads.
_ALL_TOOLS = "<all-tools>"
_ALL_TOOLS_SPELLINGS = frozenset({"", "*"})

#: Differences that are KNOWN and ACCEPTED, each with the reason it is accepted.
#: A reason is mandatory — an entry without one is refused, because "we know" is
#: not a statement anybody can check later.
#:
#: Both directions rot (decision #335): an entry naming a difference that no
#: longer exists fails just as loudly as a difference nobody declared.
DECLARED_DIFFERENCES: dict[str, str] = {
    "matcher:hook:PostToolUse:activity_event.py": (
        "Claude names ten tools, Qwen registers for every tool. Activity events "
        "drive gap-based ACTIVE time, and Qwen's wider net makes its sessions "
        "look busier than Claude's on identical work. Accepted rather than "
        "equalised here: narrowing Qwen would silently shorten sessions already "
        "measured, and widening Claude changes a number the 1.9 economy baseline "
        "is fixed against (decision #338)."
    ),
    "matcher:hook:PostToolUse:task_call_counter.py": (
        "Claude counts Write/Edit/MultiEdit/Bash/PowerShell; Qwen counts every "
        "tool. The two hosts therefore reach the session call budget at different "
        "points on the same work. Named, not fixed: the budget is calibrated "
        "against Claude's number, and changing the unit invalidates it."
    ),
    "matcher:hook:PostToolUse:tool_output_truncation_nudge.py": (
        "Claude nudges on Read/Grep/Glob/Bash/PowerShell, Qwen on every tool. The "
        "nudge is advisory in both cases, so the wider net costs nothing but a "
        "little noise."
    ),
    "matcher:hook:PostToolUse:task_done_verify.py": (
        "Qwen also registers the hook on task_done_v2, Bash and PowerShell; "
        "Claude only on the tausik_task_done MCP tool. This is the one difference "
        "with teeth: closing a task through the CLI is re-checked by the hook on "
        "Qwen and not on Claude. It is a belt over braces either way — QG-2 runs "
        "inside `task done` itself on both hosts — so the CLI path is verified "
        "with or without the hook."
    ),
}


def _touches_host_layer(files: list[str]) -> bool:
    for path in files or ():
        norm = str(path).replace("\\", "/")
        if any(norm.startswith(p) or f"/{p}" in norm for p in HOST_LAYER_PREFIXES):
            return True
    return False


def normalise_matcher(matcher: str) -> str:
    return _ALL_TOOLS if str(matcher).strip() in _ALL_TOOLS_SPELLINGS else str(matcher)


def find_differences(table: dict[str, dict[str, str]]) -> list[str]:
    """Difference ids across hosts that share an extension point.

    `table` maps host -> {capability: matcher}. Ids are built to be STABLE: a
    matcher disagreement is named once for the capability, never once per host,
    so a declaration does not have to be rewritten when a third host appears.
    """
    kinds: dict[str, list[str]] = {}
    for host, caps in table.items():
        for cap in caps:
            kinds.setdefault(cap.split(":", 1)[0], []).append(host)

    differences: list[str] = []
    for kind, _hosts in sorted(kinds.items()):
        group = sorted(
            h for h, caps in table.items() if any(c.startswith(f"{kind}:") for c in caps)
        )
        if len(group) < 2:
            continue  # one bearer: nothing to be different from
        universe = sorted({c for h in group for c in table[h] if c.startswith(f"{kind}:")})
        for cap in universe:
            absent = [h for h in group if cap not in table[h]]
            for host in absent:
                differences.append(f"missing:{cap}@{host}")
            matchers = {normalise_matcher(table[h][cap]) for h in group if cap in table[h]}
            if len(matchers) > 1:
                differences.append(f"matcher:{cap}")
    return sorted(differences)


def run_cross_model_parity_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Block when a capability differs between hosts and nobody said so."""
    if files and not _touches_host_layer(files):
        return True, "cross-model parity: not the host layer — skipped"

    table = matcher_table()
    broken = sorted(h for h, caps in table.items() if any(c.startswith("error:") for c in caps))
    if broken:
        return False, (
            f"cross-model parity: the mechanism generator for {', '.join(broken)} raised. "
            "A host whose payload cannot be built cannot be compared, and reporting "
            "that as parity would be the failure this gate exists to stop."
        )

    differences = find_differences(table)
    undeclared = [d for d in differences if d not in DECLARED_DIFFERENCES]
    stale = [d for d in DECLARED_DIFFERENCES if d not in differences]
    reasonless = [d for d, why in DECLARED_DIFFERENCES.items() if not str(why).strip()]
    drift = cross_check_against_disk(os.getcwd())

    problems: list[str] = []
    if undeclared:
        problems.append(
            "UNDECLARED difference(s) between hosts that share an extension point:\n  "
            + "\n  ".join(undeclared)
            + "\nDeclare each in DECLARED_DIFFERENCES with the reason it is accepted, "
            "or make the hosts agree. The gate does not require sameness — it requires "
            "the difference to be named."
        )
    if stale:
        problems.append(
            "DECLARED difference(s) that no longer exist:\n  "
            + "\n  ".join(stale)
            + "\nRemove them. A declaration matching nothing live is a note about the "
            "past presented as a statement about the present."
        )
    if reasonless:
        problems.append(f"declaration(s) carrying no reason: {', '.join(reasonless)}")
    if drift:
        problems.extend(drift)

    if problems:
        return False, "cross-model parity FAILED.\n" + "\n\n".join(problems)

    hosts = ", ".join(f"{h}:{len(c)}" for h, c in sorted(table.items()))
    return True, (
        f"cross-model parity: {hosts} — "
        f"{len(differences)} difference(s), all declared. "
        f"Hosts compared: {', '.join(sorted(MECHANISM_BUILDERS))}; host set read from "
        "ide_utils.IDE_REGISTRY (four host registries exist and disagree — collapsing "
        f"them is deferred to 1.10). Kinds present: {KIND_HOOK} and plugin."
    )
