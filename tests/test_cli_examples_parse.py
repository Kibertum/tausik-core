"""Every EXAMPLES entry must be an invocation the real parser accepts.

`SelfCorrectingParser` prints these on an argument error so an agent recovers
in one retry. That makes each entry a CLAIM about the CLI, not a comment — and
a wrong hint is worse than no hint, because it looks authoritative and costs a
second failed attempt before the agent falls back to `--help`.

Measured in session #199: `tausik task add` advertised three positionals
(`<story-slug> <task-slug> "Title"`) while the real signature takes one
positional and passes story and slug as options. An agent followed the hint and
got the identical error a second time.

The registry is hand-written text next to a parser that changes, so drift is
the default state, not an accident. This test removes the drift by executing
the claim.
"""

from __future__ import annotations

import contextlib
import io
import os
import shlex
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "scripts"))

from project_parser import build_parser  # noqa: E402
from project_parser_errors import EXAMPLES  # noqa: E402

# Reads a registry in scripts/ and the parser it describes; no import edge
# would otherwise select this test from a change to either.
CROSSCUTTING_SCOPE = ["scripts/"]


def _all_examples() -> list[tuple[str, str]]:
    return [(key, ex) for key, exs in EXAMPLES.items() for ex in exs]


def _parses(example: str) -> bool:
    """True when the real parser accepts the example verbatim.

    Placeholders like `<slug>` are ordinary strings to argparse, so they parse;
    what does NOT parse is a wrong arity or an option that does not exist —
    exactly the drift this test is for.
    """
    argv = shlex.split(example)
    parser = build_parser()
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            parser.parse_args(argv[1:])
    except SystemExit:
        return False
    return True


def test_the_registry_is_not_empty():
    """Guards against a vacuous pass.

    An empty registry — or an import that silently yields nothing — would make
    every assertion below true without comparing anything. Zero examples and
    twenty-four healthy ones must not look alike.
    """
    assert len(_all_examples()) >= 20


@pytest.mark.parametrize("key,example", _all_examples(), ids=lambda v: v[:40])
def test_example_parses(key: str, example: str):
    assert shlex.split(example)[0] == "tausik", f"[{key}] example must start with `tausik`"
    assert _parses(example), (
        f"[{key}] this hint does not parse — an agent following it gets the same "
        f"error a second time:\n    {example}\n"
        "Fix the entry in scripts/project_parser_errors.py::EXAMPLES to match the "
        "real signature (`tausik <cmd> --help`)."
    )


def test_a_wrong_example_is_caught():
    """The detector's own red-proof, run in-process.

    Without it, "all examples parse" is indistinguishable from a checker that
    parses nothing. Uses an arity error of the same shape as the real defect:
    an extra positional on a command that takes none.
    """
    assert not _parses("tausik verify --task x extra-positional-that-does-not-exist")
    assert _parses("tausik verify --task x")
