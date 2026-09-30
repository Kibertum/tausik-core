"""Does the run have room to FINISH another task, or should it hand off cleanly?

THE QUESTION IS NOT "HOW MUCH CONTEXT IS LEFT". A long run ends when the context does, and the
damage is not the ending but WHERE it lands: a task abandoned half-edited is worse than one never
started, because the next agent cannot tell which edits were verified. So the only decision this
module makes is taken BETWEEN tasks — start the next one, or close out and hand off.

WHAT THE MEASUREMENT SAID, and it said no. Three signals were available and none predicts the
ceiling:

* TOKENS PER CALL vary from 562 to 10,958 across the sessions that recorded both, a median near
  2,200 and a spread of twenty times. A call count converts to tokens only to within an order of
  magnitude, so a threshold in calls is a threshold in nothing.
* TOKENS ARE OFTEN ABSENT: 48 of 231 sessions with call data recorded no token figure at all.
* TIME IS RULED OUT by decision #376 — session duration is a signal, not a gate — and the sweep
  of sessions #196-#265 found not one that reached the 180-minute advisory.

So the project had been trying to INFER from its telemetry a number the runtime states outright:
an agent is told what remains of its context. This module therefore takes that figure as an
argument and spends its own care on the two failure directions instead.

BOTH DIRECTIONS ARE FAILURES, and the second is the one that hides. Running into the wall mid-task
leaves unaccountable edits. Stopping early leaves the composition half-done while the context was
fine — a polite refusal of autonomy, which is exactly the behaviour the /run skill exists to end.
An absent reading is NOT a reason to stop: the absence of a measurement is not a measurement of
the limit.
"""

from __future__ import annotations

from typing import Final, NamedTuple

#: What one task costs, as this project measures its own work rather than as a guess. Sessions
#: that recorded both calls and tokens put the median near 2,200 tokens per call, and a closed
#: task in this repository runs to roughly sixty calls once verify and the close are counted.
#: The product is the reserve a task needs end to end.
TOKENS_PER_CALL: Final[int] = 2_200
CALLS_PER_TASK: Final[int] = 60
TASK_RESERVE: Final[int] = TOKENS_PER_CALL * CALLS_PER_TASK

#: The margin on top of one task's reserve: closing out costs its own calls — the journal, the
#: AC evidence, verify, the close itself and the handoff. Measured against the same figures, that
#: tail is about a third of a task.
HANDOFF_RESERVE: Final[int] = TASK_RESERVE // 3


class Verdict(NamedTuple):
    """`go` plus the sentence explaining it. The reason travels with the decision because a
    driver that stopped without saying why reads exactly like a driver that gave up."""

    go: bool
    reason: str


def room_to_finish(remaining_tokens: int | None) -> Verdict:
    """Is there room to START another task and still close it and hand off?

    ``remaining_tokens`` is what the runtime reports it has left, or None when nothing reports
    it. None means GO: an unknown is not a limit, and 48 of 231 sessions in this project's own
    history carried no usage telemetry at all. Stopping on missing data would make the driver
    stop hardest exactly where it is least informed.
    """
    if remaining_tokens is None:
        return Verdict(True, "no capacity reading available — an absent measurement is not a limit")
    if remaining_tokens < 0:
        return Verdict(
            True, f"capacity reading is nonsense ({remaining_tokens}) — treated as absent"
        )
    needed = TASK_RESERVE + HANDOFF_RESERVE
    if remaining_tokens >= needed:
        return Verdict(
            True,
            f"{remaining_tokens} tokens left against {needed} needed for a task plus its handoff",
        )
    if remaining_tokens >= HANDOFF_RESERVE:
        return Verdict(
            False,
            f"{remaining_tokens} tokens left, under the {needed} a task needs end to end. "
            f"Close what is open, write the handoff, name the next task from the plan and stop — "
            f"stopping BETWEEN tasks is clean, stopping inside one is not",
        )
    return Verdict(
        False,
        f"only {remaining_tokens} tokens left, under the {HANDOFF_RESERVE} the handoff itself "
        f"costs. Write the handoff NOW, before it stops fitting",
    )


def advisory_line(remaining_tokens: int | None) -> str:
    """One line for the driver to print between tasks. Silent when there is room.

    Between tasks the driver prints one line per closed task and nothing else, because prose is
    what ends a turn and ending the turn is the failure /run was built against. A capacity notice
    earns its line only when it changes what happens next.
    """
    verdict = room_to_finish(remaining_tokens)
    return "" if verdict.go else f"/run STOPPING: {verdict.reason}."


def main(argv: list[str] | None = None) -> int:
    """`--remaining <tokens>` → exit 0 to go on, 1 to close out and hand off.

    A command rather than a paragraph of advice, because the skill's own history is the
    argument: autonomy asked for in prose got switched off the same week, and the capacity
    step was the last one still phrased as "judge whether there is room".
    """
    import argparse

    p = argparse.ArgumentParser(description="Has the run room to finish another task?")
    p.add_argument(
        "--remaining",
        type=int,
        default=None,
        help="Tokens the runtime reports as left. Omit when nothing reports it — an absent "
        "reading is not a limit, and the answer is then to go on.",
    )
    args = p.parse_args(argv)
    verdict = room_to_finish(args.remaining)
    if not verdict.go:
        print(advisory_line(args.remaining))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
