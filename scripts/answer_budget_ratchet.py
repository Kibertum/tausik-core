"""The length of an answer is measured; this is the thing that goes red when it grows.

WHY IT EXISTS. `tausik metrics answers` has produced a number since 1.10 and nothing looked
at it. Story J closed as delivered while the median final answer went from 396 words to 522
against a budget of 200 — the measurement was taken, filed, and never compared to anything.
A number nobody compares is a number that only records the drift it was built to stop.

IT IS LOCAL, AND THAT IS WHY IT DOES NOT BLOCK A BUILD. The subject is host transcripts,
which live on the machine that produced them and never travel — the same property
`red_history` declares about which tests have been seen red. So: the ratchet runs where the
answers were written, reports ABSENCE where there are none (decision #334: a quantity that
cannot be obtained is not zero), and never turns "no data" into a failure. On a machine with
transcripts it is a real bound; on a fresh clone it is silent and says why.

THE BASELINE IS A MEASUREMENT, NOT A WISH. It is not the 200-word budget: a threshold that
ordinary work crosses on day one is a threshold somebody switches off, and this project has
paid for that lesson once already with a telemetry window. The baseline is where the median
actually sits, and it may only go down. The budget stays what the agent is told to aim at;
the ratchet is what notices it drifting away from it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Final, NamedTuple

#: Where the baseline lives, beside the other ratchets.
GATES_KEY: Final[str] = "answer_shape"

#: Fewer than this and a median says more about the sample than about the habit. Ten
#: transcripts is what `tausik metrics answers` reads by default.
MIN_ANSWERS: Final[int] = 20


class Verdict(NamedTuple):
    """``level`` is ok | warn | absent. ``detail`` is one line for a human."""

    level: str
    detail: str
    measured: dict[str, Any]


def baseline(repo_root: str = ".") -> dict[str, Any]:
    """The recorded baseline, or an empty dict when the key is absent."""
    path = os.path.join(repo_root, "tausik", "gates.json")
    try:
        with open(path, encoding="utf-8") as fh:
            node = json.load(fh).get(GATES_KEY)
    except (OSError, ValueError):
        return {}
    return node if isinstance(node, dict) else {}


def measure_local(project_dir: str, last: int = 10) -> dict[str, Any]:
    """`tausik metrics answers` as a dict, or ``{}`` when this machine has no transcripts."""
    import sys

    here = os.path.dirname(os.path.abspath(__file__))
    for p in (here, os.path.join(here, "hooks")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        from answer_shape import measure
        from transcript_locator import project_transcripts
    except ImportError:
        return {}
    paths = project_transcripts(project_dir)[: max(1, last)]
    if not paths:
        return {}
    report, _skipped = measure(paths)
    return report.summary()


def check(project_dir: str = ".", repo_root: str | None = None, last: int = 10) -> Verdict:
    """Compare this machine's answers against the recorded baseline.

    Absence is reported as absence three times over, because each is a different fact: no
    transcripts at all, too few answers inside them to make a median mean anything, and no
    baseline recorded yet. None of the three is a failure — a check that fails on missing
    data teaches people to pass `--skip`.
    """
    root = repo_root or project_dir
    base = baseline(root)
    got = measure_local(project_dir, last=last)
    if not got:
        return Verdict("absent", "no host transcripts on this machine — nothing to measure", {})
    answers = int(got.get("answers") or 0)
    if answers < MIN_ANSWERS:
        return Verdict(
            "absent",
            f"{answers} answer(s) in the transcripts read — below {MIN_ANSWERS}, "
            "a median here would describe the sample, not the habit",
            got,
        )
    if not base:
        return Verdict(
            "absent",
            f"no baseline in tausik/gates.json[{GATES_KEY}] — record the measured "
            f"median {got.get('final_words_median')} and p90 {got.get('final_words_p90')}",
            got,
        )
    grew = []
    shrank = []
    for key, name in (("final_words_median", "median"), ("final_words_p90", "p90")):
        want, have = base.get(key), got.get(key)
        if want is None or have is None:
            continue
        if have > want:
            grew.append(f"{name} {have} > {want}")
        elif have < want:
            shrank.append(f"{name} {have} (was {want})")
    if grew:
        return Verdict(
            "warn",
            "answers GREW: "
            + "; ".join(grew)
            + ". The shape is in the rules file; this says it is not being followed.",
            got,
        )
    if shrank:
        return Verdict(
            "ok",
            "answers shrank: " + "; ".join(shrank) + " — record the lower numbers in "
            f"tausik/gates.json[{GATES_KEY}], a ratchet only holds what it was told",
            got,
        )
    return Verdict("ok", f"answers at the baseline ({answers} measured)", got)


def doctor_line(project_dir: str = ".", repo_root: str | None = None) -> tuple[str, str]:
    """``(level, detail)`` for `tausik doctor`. Never raises."""
    try:
        v = check(project_dir, repo_root=repo_root)
    except Exception:  # noqa: BLE001 - a dashboard row must not take the dashboard down
        return "ok", "answer shape: not measured (transcript read failed)"
    return ("warn" if v.level == "warn" else "ok"), v.detail


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    p = argparse.ArgumentParser(description="Answer-length ratchet against the recorded baseline")
    p.add_argument("--project-dir", default=".")
    p.add_argument("--repo-root", default=None)
    p.add_argument("--last", type=int, default=10)
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    v = check(args.project_dir, repo_root=args.repo_root, last=args.last)
    if args.as_json:
        print(json.dumps({"level": v.level, "detail": v.detail, **v.measured}, ensure_ascii=False))
    else:
        print(f"[{v.level}] {v.detail}")
    # Absence is not a failure; growth is.
    return 1 if v.level == "warn" else 0


if __name__ == "__main__":
    raise SystemExit(main())
