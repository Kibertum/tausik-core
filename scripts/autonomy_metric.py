"""How much work happens between two messages from the owner.

THE PROMISE THIS MAKES CHECKABLE. "The agent works autonomously through your plan until every
task is done" is words, and a user learns their price on their own project. The checkable form is
a number: closures per owner message, and stops per closure.

WHAT COUNTS AS A STOP, and this is the whole design. A stop is an owner message whose ONLY content
is a request to carry on — "keep going", "continue", "don't stop". That is the agent handing the
turn back while the composition still offered work, and the owner paying a message to undo it.

WHAT DOES NOT COUNT, because the alternative punishes the wrong thing: a message carrying a NEW
instruction is not a stop, however it is phrased. If it were, the metric would score a
conversation about plans as a failure, and the first real discussion would ruin the number. The
owner is allowed to talk; the agent is not allowed to freeze.

DESCRIPTIVE, NOT PREDICTIVE — like risk and calibration in this project. It says what happened over
a transcript that exists. It does not forecast the next run, and a good number is not a promise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Final, Iterator, NamedTuple

#: A message that asks for nothing except continuation. Matched on the WHOLE message after
#: stripping punctuation, never as a substring: "continue with the site task" carries an
#: instruction and is not a stop, while "continue" on its own is the owner paying a message to
#: restart an agent that froze.
_CONTINUE_ONLY: Final[re.Pattern[str]] = re.compile(
    r"^(?:"
    r"продолжа(?:й|ем|ть)|продолжай\s+работу|продолжай\s+автономно|"
    r"не\s+останавливайся|дальше|далее|ещё|еще|"
    r"continue|carry\s+on|keep\s+going|go\s+on|proceed|next"
    r")$",
    re.I,
)

#: Text the harness injects into a user turn that the owner never typed.
_NOT_FROM_THE_OWNER: Final[tuple[str, ...]] = (
    "<system-reminder>",
    "[SYSTEM NOTIFICATION",
    "<task-notification>",
    "<command-name>",
    "Base directory for this skill:",
    "Caveat: The messages below were generated",
)


class Counts(NamedTuple):
    owner_messages: int
    stops: int
    closures: int

    @property
    def closures_per_message(self) -> float:
        return self.closures / self.owner_messages if self.owner_messages else 0.0

    @property
    def stops_per_closure(self) -> float:
        return self.stops / self.closures if self.closures else 0.0


def _records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except (ValueError, TypeError):
                continue  # a partially written line at the tail is not a record


def owner_text(record: dict[str, Any]) -> str | None:
    """The owner's own words in this record, or None if the owner did not write it.

    A transcript's `user` records are mostly not from the user: tool results, reminders, harness
    notifications and skill bodies all arrive in that role. Measured on one session of this
    project: 5644 tool results and 43 notifications against 70 real messages, so a count that
    skipped this separation would be wrong by two orders of magnitude.
    """
    if record.get("type") != "user":
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        text = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    else:
        text = str(content or "")
    if not text.strip() or any(marker in text for marker in _NOT_FROM_THE_OWNER):
        return None
    return text.strip()


def is_stop(text: str) -> bool:
    """Is this message a bare request to carry on?

    The test is on the WHOLE message with punctuation stripped, because the distinction that
    matters is between "continue" and "continue with X": the second carries an instruction, and
    counting it would make the metric punish conversation instead of freezing.
    """
    stripped = re.sub(r"[\s.!,;:—-]+$", "", text.strip())
    return bool(_CONTINUE_ONLY.match(stripped))


def count(transcript: Path, closures: int) -> Counts:
    """Owner messages and stops in one transcript, against the closures it produced."""
    messages = [t for t in (owner_text(r) for r in _records(transcript)) if t]
    return Counts(len(messages), sum(1 for t in messages if is_stop(t)), closures)


def render(counts: Counts) -> str:
    lines = [
        f"Owner messages: {counts.owner_messages}",
        f"Stops (a message asking only to carry on): {counts.stops}",
        f"Task closures: {counts.closures}",
        f"Closures per owner message: {counts.closures_per_message:.2f}",
        f"Stops per closure: {counts.stops_per_closure:.2f}",
        "",
        "DESCRIPTIVE, NOT PREDICTIVE: this says what happened over one transcript. It does not",
        "forecast the next run, and a good number here is not a promise about the next one.",
        "A message carrying a new instruction is NOT counted as a stop — the owner is allowed to",
        "talk; the agent is not allowed to freeze.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Closures per owner message, from a transcript")
    p.add_argument("transcript", type=Path, help="The .jsonl transcript on disk")
    p.add_argument("--closures", type=int, required=True, help="Tasks closed during it")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not args.transcript.is_file():
        print(f"No such transcript: {args.transcript}")
        return 2
    print(render(count(args.transcript, args.closures)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
