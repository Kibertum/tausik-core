"""Every token-economy lever TAUSIK ships, and whether this project decided on it.

DOGFOODING IS A CLAIM, AND A CLAIM NEEDS A CHECK. The project states "this
framework is its own user", ships levers that reduce token cost, and had decided
on none of them: `output_mode` unset, `read_ledger` unset, the output thresholds
unset, `context_tier` set to the value it already defaults to. That divergence
was found by reading a config field, which is precisely how it should NOT be
found — a discrepancy nobody can trip over is a discrepancy that survives.

WHAT THIS MODULE ASSERTS is not "every lever is ON". Several are correctly off
here, and the measurement says why. It asserts that each lever has an EXPLICIT
decision: a value in `.tausik/config.json`, or an entry in `DELIBERATELY_UNSET`
carrying the reason. A default nobody chose is not a decision, and the whole
release exists to stop things that look decided from being merely unexamined.

THE REGISTRY CANNOT ROT (decision #335). An entry naming a lever that no longer
exists in the shipped code fails, and a lever that appears in the code and is
named by neither a value nor an entry fails too. Both directions, because a
registry checked in one direction only decays into a list of good intentions.
"""

from __future__ import annotations

import json
import os
from typing import Any

from tausik_utils import tausik_config_path

#: The levers, each with the code that PROVES it is shipped. The proof is a
#: (module path, symbol) pair, checked by reading the file — never by importing
#: it, so this stays usable on a tree nobody has reviewed.
SHIPPED_LEVERS: dict[str, tuple[str, str]] = {
    "output_mode": ("bootstrap/bootstrap_templates.py", "CAVEMAN_DIRECTIVE"),
    "context_tier": ("bootstrap/bootstrap_templates.py", "MINIMAL_TIER_FOOTER"),
    "tool_output_truncation_threshold": (
        "scripts/hooks/tool_output_truncation_nudge.py",
        "DEFAULT_THRESHOLD",
    ),
    "tool_output_truncation_bytes": (
        "scripts/hooks/tool_output_truncation_nudge.py",
        "DEFAULT_BYTE_THRESHOLD",
    ),
    "read_ledger": ("scripts/hooks/read_ledger.py", "DEFAULT_WINDOW_CALLS"),
}

#: Levers this project deliberately leaves at their default, and WHY. A reason
#: is required and is read by a human, so it says what was measured rather than
#: "not needed".
DELIBERATELY_UNSET: dict[str, str] = {
    "output_mode": (
        "OFF, measured. `caveman` compresses conversational prose only; it exempts code, "
        "commands, tool output and the durable record by name. On this project's own "
        "corpus prose is 1,493,022 of 16,287,948 characters of output — 9.2% — because "
        "90.6% is tool arguments (Bash commands 7.3M chars, Write contents 3.2M, Edit "
        "2.2M). Output is 71.6% of context growth, so the ceiling is 71.6% x 9.2% = 6.6%, "
        "and a third off the prose is about 2%. Second and decisive: the rules generator "
        "is preserve-if-exists and this project's CLAUDE.md is hand-written (doctor: 0 of "
        "14 headings shared with the template), so setting the flag would change NOTHING "
        "on disk while looking as if it had — the silent no-op warn_output_mode_not_applied "
        "exists to prevent. Applying it by hand needs 700 characters in a file whose "
        "static portion is capped at 4096 with roughly 90 free."
    ),
    "context_tier": (
        "INERT here, and removed from our config rather than left looking live. It picks "
        "how verbose the GENERATED rules file is, and the generator is preserve-if-exists: "
        "this project's CLAUDE.md is hand-written (doctor: 0 of 14 headings shared with the "
        "template), so the key was never read. Leaving `context_tier: standard` in place "
        "asserted a setting that did nothing — the same silent no-op as a flag that cannot "
        "reach the file it configures. Our rules verbosity is governed instead by the "
        "4096-byte cap on CLAUDE.md's static portion, which a test enforces."
    ),
    "read_ledger": (
        "OFF, measured, and off is the SHIPPED default for everyone. It refuses a re-read, "
        "and a wrong refusal after a compaction hands the agent an absence it cannot "
        "detect. Its ceiling here is small: Read is 2.07% of context growth and the "
        "mechanism targets ~0.49%, because 88% of this project's file reads go through "
        "Bash (2,196 reads inside commands against 285 through the Read tool). A mechanism "
        "that can cut data is not enabled for a fifth of one percent."
    ),
    "tool_output_truncation_threshold": (
        "DEFAULT (250 lines) accepted deliberately. The default was set from this "
        "project's own corpus and there is no measurement saying another number would be "
        "better here; changing it to look decided would be worse than accepting it."
    ),
    "tool_output_truncation_bytes": (
        "DEFAULT (24,000 bytes) accepted deliberately — set at the measured p99 of "
        "per-call context growth (6,386 tokens). Same reasoning as the line threshold."
    ),
}


def load_config(project_dir: str) -> dict[str, Any] | None:
    """The project's own config, or None when there is none.

    None is NOT an empty dict: a missing config means no decisions were recorded
    at all, and a checker that treated the two alike would go green on the very
    state it exists to catch.
    """
    try:
        with open(tausik_config_path(project_dir), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def lever_is_shipped(repo_root: str, lever: str) -> bool:
    """True when the code that implements `lever` is present in the tree.

    Read, never imported — a check that executes the tree it is checking cannot
    be run on a branch nobody has read yet.
    """
    entry = SHIPPED_LEVERS.get(lever)
    if entry is None:
        return False
    rel, symbol = entry
    try:
        with open(os.path.join(repo_root, rel), encoding="utf-8", errors="replace") as fh:
            return symbol in fh.read()
    except OSError:
        return False


def undecided_levers(project_dir: str, repo_root: str | None = None) -> list[str]:
    """Shipped levers this project has neither set nor deliberately left unset."""
    root = repo_root or project_dir
    cfg = load_config(project_dir)
    if cfg is None:
        return sorted(SHIPPED_LEVERS)
    return sorted(
        lever
        for lever in SHIPPED_LEVERS
        if lever_is_shipped(root, lever) and lever not in cfg and lever not in DELIBERATELY_UNSET
    )


def stale_registry_entries(repo_root: str) -> list[str]:
    """Registry entries naming a lever the shipped code no longer has.

    Decision #335: an entry that matches nothing live is not documentation, it is
    a claim about code that is gone.
    """
    return sorted(
        lever
        for lever in DELIBERATELY_UNSET
        if lever not in SHIPPED_LEVERS or not lever_is_shipped(repo_root, lever)
    )
