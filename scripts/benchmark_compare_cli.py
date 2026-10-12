"""CLI parser registration for natural cohort comparison."""

from __future__ import annotations

import argparse


def add_parser(metrics_sub: argparse._SubParsersAction) -> None:
    compare = metrics_sub.add_parser(
        "compare",
        help="Compare two naturally accumulated version/model/time cohorts",
    )
    for side in ("left", "right"):
        compare.add_argument(f"--{side}-label", default=side)
        compare.add_argument(f"--{side}-version")
        compare.add_argument(f"--{side}-model")
        compare.add_argument(f"--{side}-provider")
        compare.add_argument(f"--{side}-reasoning")
        compare.add_argument(f"--{side}-speed")
        compare.add_argument(f"--{side}-since")
        compare.add_argument(f"--{side}-until")
    compare.add_argument("--minimum-sample", type=int, default=5)
    compare.add_argument("--maturation-days", type=int, default=30)
    compare.add_argument("--save", help="Persist a privacy-safe reproducible JSON snapshot")
    compare.add_argument("--json", action="store_true", dest="as_json")
