"""`tausik metrics answers` — the shape of the agent's answers (story J, 1.10)."""

from __future__ import annotations

from typing import Any


def add(metrics_sub: Any) -> None:
    ma = metrics_sub.add_parser(
        "answers",
        help="Shape of the agent's final answers over the last N host transcripts: "
        "words, verdict-first share, list share, filler (terse-answers-measured-first)",
    )
    ma.add_argument("--last", type=int, default=10, help="Last N transcripts (default: 10)")
    ma.add_argument("--json", action="store_true", dest="as_json", help="Machine-readable output")


def run(args: Any) -> None:
    import json
    import os

    from answer_shape import measure
    from project_config import find_tausik_dir

    sys_path_hooks = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks")
    import sys

    if sys_path_hooks not in sys.path:
        sys.path.insert(0, sys_path_hooks)
    from transcript_locator import newest_project_transcripts

    tdir = find_tausik_dir()
    project_dir = os.path.dirname(tdir) if tdir else os.getcwd()
    paths = newest_project_transcripts(project_dir, int(getattr(args, "last", 10) or 10))
    report, skipped = measure(paths)
    summary = report.summary()
    if getattr(args, "as_json", False):
        print(json.dumps({**summary, "skipped": skipped}, ensure_ascii=False))
        return
    if not paths:
        print("No host transcripts found for this project.")
        return
    for key, value in summary.items():
        print(f"{key}: {value}")
    for line in skipped:
        print(f"SKIPPED {line}")
