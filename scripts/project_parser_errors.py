"""Self-correcting CLI errors — v15p-self-correcting-cli (T1).

Agents guess CLI arguments and burn iterations on bare argparse errors.
`SelfCorrectingParser.error()` appends the subcommand usage plus 1-2 known-
good examples so the agent recovers in a single retry (docs-mcp-server
grounding pattern, research 2026-06-12 T1).

The example registry is keyed by command prefix ("tausik task add"). The
failing parser may be the root one (argparse reports unrecognized extras at
the top level), so the lookup matches the *invoked argv*, not `self.prog`.
"""

from __future__ import annotations

import argparse
import sys

# Known-good invocations for the commands agents most often get wrong
# (epic add has only 2 positionals; task add requires --role; memory add
# takes type+title+content positionally; ...). Keep entries short — they
# are printed verbatim into the agent's context on every arg error.
EXAMPLES: dict[str, list[str]] = {
    "tausik task add": [
        'tausik task add <story-slug> <task-slug> "Title" --stack python --complexity medium --role developer',
    ],
    "tausik task quick": ['tausik task quick "Title" --goal "..." --role developer'],
    "tausik task start": ["tausik task start <slug>"],
    "tausik task done": [
        'tausik task done <slug> --ac-verified --relevant-files a.py b.py --evidence "AC verified: 1. ..."',
    ],
    "tausik task log": ['tausik task log <slug> "what was done"'],
    "tausik task update": [
        "tausik task update <slug> --goal '...' --acceptance-criteria '...'",
    ],
    "tausik task block": ['tausik task block <slug> --reason "why"'],
    "tausik epic add": ['tausik epic add <slug> "Title"'],
    "tausik story add": ['tausik story add <epic-slug> <story-slug> "Title"'],
    "tausik memory add": [
        'tausik memory add gotcha "Title" "Content" --tags tag1 tag2',
        "tausik memory add {context,convention,dead_end,gotcha,pattern} <title> <content>",
    ],
    "tausik decide": ['tausik decide "Decision text" --rationale "why" --task <slug>'],
    "tausik dead-end": ['tausik dead-end "approach tried" "why it failed"'],
    "tausik verify": ["tausik verify --task <slug>"],
    "tausik search": ['tausik search "query" --scope tasks --limit 10'],
    "tausik session": ["tausik session start", "tausik session end"],
    "tausik key": ["tausik key init", "tausik key show"],
    "tausik receipt": [
        "tausik receipt show --task <slug>",
        "tausik receipt export --task <slug>",
        "tausik receipt verify <file.json>",
    ],
    "tausik serve": ["tausik serve --port 8765"],
}


def find_examples(argv_tail: list[str] | None = None) -> list[str]:
    """Longest-prefix match of the invoked command against EXAMPLES."""
    tail = sys.argv[1:] if argv_tail is None else argv_tail
    cmdline = " ".join(["tausik"] + [a for a in tail if not a.startswith("-")])
    best = None
    for key in EXAMPLES:
        if cmdline.startswith(key) and (best is None or len(key) > len(best)):
            best = key
    return EXAMPLES[best] if best else []


class SelfCorrectingParser(argparse.ArgumentParser):
    """ArgumentParser whose arg errors teach the caller the right syntax.

    Subparsers created via add_subparsers().add_parser() inherit this class
    automatically (argparse uses the parent parser's class), so swapping the
    root parser covers the whole command tree.
    """

    def error(self, message: str):  # noqa: ANN201 - argparse signature
        parts = [f"{self.prog}: error: {message}", self.format_usage().rstrip()]
        examples = find_examples()
        if examples:
            parts.append("examples:")
            parts.extend("  " + e for e in examples)
        parts.append(
            f"hint: `{self.prog} --help` lists all options; full reference: docs/ru/cli.md"
        )
        self.exit(2, "\n".join(parts) + "\n")
