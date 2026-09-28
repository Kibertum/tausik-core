"""Append-only telemetry in `.tausik/` has a declared lifetime, per file, for a stated reason.

THE MEASUREMENT. Three sidecar files, about 20 MB between them: `routing_adherence.jsonl` at
46,192 lines, `observed_coverage.jsonl` at 54,000 lines and unwritten for twenty days,
`token_metrics.jsonl` at 8,216 lines. Nothing has ever removed a line from any of them. They sat
beside DB backups that DO get pruned, which is what gave the asymmetry away.

THE LIFETIME FOLLOWS THE READER, not a round number, because the only honest question is how much
of the tail anybody consumes:

* `token_metrics` — read over a "last N sessions" window. Lines older than the window are weight
  nobody reads.
* `routing_adherence` — aggregated into one rate over the whole file. A LIFETIME rate cannot show
  change: it dilutes every recent shift into a months-long average, so keeping everything makes
  the measurement worse rather than richer. Bounded to the recent tail on purpose.
* `observed_coverage` — the whole file IS the measurement (which test touched which file), so it
  is not trimmed by age. It is REGENERABLE by re-running the suite with the collector, and being
  twenty days stale means it already describes a tree that has changed. Its lifetime is one
  measurement run, and the honest action is to regenerate, not to truncate.

WHAT THE TRUNCATION REFUSES. It never touches a file whose reader needs all of it, and it keeps
the TAIL rather than the head: telemetry is append-only, so the newest lines are the ones every
reader wants. Trimming the wrong end would leave a file that looks healthy and answers about a
past nobody asked about.
"""

from __future__ import annotations

import os
from typing import Final, NamedTuple


class Policy(NamedTuple):
    """One file's declared lifetime. ``keep_lines`` of None means "not trimmed by age"."""

    name: str
    keep_lines: int | None
    reason: str


#: 8,000 lines is the measured size of `token_metrics` after a long working session, so one file's
#: worth of that is the window a reader of "the last N sessions" can actually reach. The same bound
#: is applied to the adherence sidecar, where it is the difference between a rate that can move and
#: an average that cannot.
WINDOW_LINES: Final[int] = 8_000

POLICIES: Final[tuple[Policy, ...]] = (
    Policy(
        "token_metrics.jsonl",
        WINDOW_LINES,
        "read over a last-N-sessions window; older lines are weight nobody reads",
    ),
    Policy(
        "routing_adherence.jsonl",
        WINDOW_LINES,
        "aggregated into one rate — a lifetime rate dilutes every recent shift into a "
        "months-long average, so an unbounded file makes the measurement worse",
    ),
    Policy(
        "semantic_rerank.jsonl",
        WINDOW_LINES,
        "one line per search, and the question it answers is whether the layer earns its keep "
        "on RECENT traffic; a lifetime rate would average a switched-off month into a "
        "switched-on week and say nothing about either",
    ),
    Policy(
        "observed_coverage.jsonl",
        None,
        "the whole file IS the measurement (which test touched which file), so it is not "
        "trimmed by age. It is regenerable by re-running the suite with the collector, and "
        "the honest action on a stale one is to regenerate rather than truncate",
    ),
)


def _path(tausik_dir: str, name: str) -> str:
    return os.path.join(tausik_dir, name)


def line_counts(tausik_dir: str) -> dict[str, int]:
    """Lines per declared file. A missing file is absent from the result, not zero."""
    out: dict[str, int] = {}
    for policy in POLICIES:
        path = _path(tausik_dir, policy.name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            out[policy.name] = sum(1 for _ in fh)
    return out


def over_window(tausik_dir: str) -> list[tuple[Policy, int]]:
    """Files past their declared window, with the count. Untrimmed ones never appear."""
    counts = line_counts(tausik_dir)
    return [
        (p, counts[p.name])
        for p in POLICIES
        if p.keep_lines is not None and counts.get(p.name, 0) > p.keep_lines
    ]


#: The RATCHET's limit, which is not the reader's window. A live session appends to these files
#: between one trim and the next — measured immediately after trimming to 8000, the two files were
#: at 8024 and 8048 within minutes — so a threshold of "nothing past the window" is unmeetable by
#: construction and would redden on ordinary work. One window for the reader plus one for the
#: session in progress is the smallest bound that still catches ACCUMULATION, which is the thing
#: the ratchet is for.
HARD_MULTIPLE: Final[int] = 2


def over_hard_limit(tausik_dir: str) -> list[tuple[Policy, int]]:
    """Files whose growth is ACCUMULATION rather than one session's worth of appending."""
    counts = line_counts(tausik_dir)
    return [
        (p, counts[p.name])
        for p in POLICIES
        if p.keep_lines is not None and counts.get(p.name, 0) > p.keep_lines * HARD_MULTIPLE
    ]


def truncate(tausik_dir: str, dry_run: bool = False) -> dict[str, tuple[int, int]]:
    """Keep the TAIL of each file past its window. ``{name: (before, after)}``.

    The tail, not the head: telemetry is append-only, so the newest lines are the ones every
    reader wants, and trimming the other end would leave a file that looks healthy while
    answering about a past nobody asked about.
    """
    result: dict[str, tuple[int, int]] = {}
    for policy, count in over_window(tausik_dir):
        keep = policy.keep_lines or 0
        result[policy.name] = (count, keep)
        if dry_run:
            continue
        path = _path(tausik_dir, policy.name)
        with open(path, encoding="utf-8", errors="replace") as fh:
            tail = fh.readlines()[-keep:]
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(tail)
    return result


def doctor_line(tausik_dir: str) -> tuple[str, str]:
    """``(level, detail)`` for `tausik doctor` — the signal half of the retention.

    A rule with a command and no signal is a rule nobody applies: that is exactly how 20 MB
    accumulated next to backups that were being pruned.
    """
    counts = line_counts(tausik_dir)
    if not counts:
        return "ok", "no telemetry sidecars"
    total_mb = sum(
        os.path.getsize(_path(tausik_dir, n))
        for n in counts
        if os.path.isfile(_path(tausik_dir, n))
    ) / (1024 * 1024)
    past = over_window(tausik_dir)
    if past:
        names = ", ".join(f"{p.name} ({n} lines)" for p, n in past)
        return "warn", (
            f"{len(counts)} sidecar(s), {total_mb:.0f} MiB — past their window: {names}. "
            f"Trim: `tausik db telemetry --apply`"
        )
    return "ok", f"{len(counts)} sidecar(s), {total_mb:.0f} MiB, all within their window"
