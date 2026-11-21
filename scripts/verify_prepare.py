"""The two calls every task pays before a check can be green.

MEASURED. Two gates go red for reasons known in advance and fixed by a fixed command:
`ruff_format` unless `ruff format` has run, and `bootstrap_drift` after any edit under
`scripts/` unless the profile has been redeployed. Both are deterministic, neither is a
judgement, and each costs its own call — at the project's measured 482 000 tokens of prefix
re-sent per call, about a million tokens per task, against roughly 400 closures a month.

WHY THIS IS NOT THE GATE HEALING ITSELF. `bootstrap_drift` refuses to rebuild the copies it
evaluates, and rightly: a gate that mutates the state it judges certifies its own repair.
What runs here is not the gate — it is the AGENT, asking for the preparation by name before
the gates look at anything. The asking is explicit, the step list is data rather than
something assembled on the way, and the outcome is reported so a green never quietly means
"green after something changed the tree".

WHAT PREPARATION IS ALLOWED TO BE. Formatting and redeployment: two operations whose result
does not depend on what the code means. Anything that needed judgement would be the agent
laundering a decision through a flag, so the list is closed and a test holds it closed.

AND IT TOUCHES ONLY THE DECLARED SCOPE. The first version ran `ruff format .` and rewrote
90 files on its first real use, including ones deliberately held on the
`ruff_format.legacy_unformatted` list — a ratchet that only shrinks, quietly emptied by a
convenience. Editing files nobody declared is Rule 2 by another route, so a step that takes
files is given the task's own relevant_files and is SKIPPED, out loud, when there are none.

CONSUMER LAYOUT. Deployed copies under `.{ide}/scripts/` are formatted by rewriting the
`library_source` originals, then redeployed — never by applying the product `pyproject`
line-length to the deploy tree (that oscillates with `bootstrap_drift`). On a consumer the
bootstrap entrypoint is `.tausik-lib/bootstrap/bootstrap.py` when `bootstrap/` is absent.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tausik_utils import library_source

# MIRROR of bootstrap_config.SCAFFOLD_IDES — keep in step (convention #249).
_SCAFFOLD_IDES = ("claude", "cursor", "qwen", "kilo", "opencode", "codex")
_BOOTSTRAP_CANDIDATES = (
    "bootstrap/bootstrap.py",
    ".tausik-lib/bootstrap/bootstrap.py",
)


@dataclass(frozen=True)
class Step:
    """One preparation command: what it is called, what it runs, why it exists."""

    name: str
    argv: tuple[str, ...]
    because: str
    #: True when the command must be told WHICH files to touch. Such a step is skipped
    #: rather than run tree-wide: a prepare that edits undeclared files is a scope breach
    #: wearing a convenience's clothes.
    takes_files: bool = False
    #: File suffixes accepted by a file-taking command. Passing JSON or Markdown to
    #: `ruff format` can rewrite valid data as Python-like syntax, so selection belongs
    #: to the preparation contract rather than to caller discipline.
    suffixes: tuple[str, ...] | None = None
    #: Dynamic bootstrap resolution — see `resolve_bootstrap_argv`. When True, `argv` is
    #: only a template for tests that inspect STEPS; `run` rebuilds it per tree.
    resolves_bootstrap: bool = False


#: The closed list. Adding to it is a decision about what "preparation" means, so it is
#: made here, in data, where a test can read it — not assembled per run from what looks
#: convenient at the time.
STEPS: tuple[Step, ...] = (
    Step(
        name="ruff format",
        argv=("ruff", "format"),
        because="the ruff_format gate goes red on unformatted files, and formatting is "
        "deterministic — running it is not a judgement about the code",
        takes_files=True,
        suffixes=(".py", ".pyi"),
    ),
    Step(
        name="bootstrap redeploy",
        argv=(sys.executable, "bootstrap/bootstrap.py", "--ide", "all"),
        because="the CLI runs the DEPLOYED copies under .claude/, so an edit under "
        "scripts/ leaves bootstrap_drift red until the profile is rebuilt",
        resolves_bootstrap=True,
    ),
)


class PreparationFailed(RuntimeError):
    """A preparation step failed. The run stops here rather than judging an unprepared tree."""


def resolve_bootstrap_argv(root: str | Path) -> list[str] | None:
    """Bootstrap entrypoint for this tree, or None when neither layout is present."""
    base = Path(root)
    for rel in _BOOTSTRAP_CANDIDATES:
        if (base / rel).is_file():
            return [sys.executable, rel.replace("/", os.sep), "--ide", "all"]
    return None


def map_format_target(root: str | Path, rel: str) -> str:
    """Map a declared path to the file `ruff format` should rewrite.

    Deployed `.{ide}/scripts/...` copies are rewritten at `library_source` so the
    product pyproject never reformats TAUSIK harness code to a different line length.
    Product and test paths pass through unchanged.
    """
    norm = rel.replace("\\", "/")
    src = library_source(str(root), "scripts")
    if src is None:
        return rel
    src_path = Path(src)
    root_path = Path(root)
    for ide in _SCAFFOLD_IDES:
        prefix = f".{ide}/scripts/"
        if not norm.startswith(prefix):
            continue
        mapped = src_path / norm[len(prefix) :]
        if mapped.is_file():
            try:
                return str(mapped.relative_to(root_path)).replace("\\", "/")
            except ValueError:
                return str(mapped)
        return rel
    return rel


def format_targets(
    root: str | Path, files: Sequence[str], suffixes: tuple[str, ...] | None
) -> list[str]:
    """Declared Python paths, deploy→library mapped, de-duplicated, order preserved."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in files:
        if not raw:
            continue
        if suffixes and Path(raw).suffix not in suffixes:
            continue
        mapped = map_format_target(root, raw)
        key = mapped.replace("\\", "/")
        if key in seen:
            continue
        seen.add(key)
        out.append(mapped)
    return out


def run(
    root: str | Path, files: Sequence[str] | None = None, *, runner=subprocess.run
) -> list[str]:
    """Run every step in order. Returns one line per step, for the reader and the record.

    `files` is the task's declared scope. A step that takes files and is given none is
    skipped and SAYS so — running it over the whole tree is what rewrote 90 files the first
    time this ran, and silence about a skip reads exactly like success.

    Raises `PreparationFailed` on the first non-zero exit, carrying that step's own output.
    Continuing would run the gates over a tree the agent believes was prepared and was not,
    and a green from that says the opposite of what it seems to say.
    """
    said: list[str] = []
    targets = [f for f in (files or []) if f]
    for step in STEPS:
        if step.resolves_bootstrap:
            argv = resolve_bootstrap_argv(root)
            if argv is None:
                said.append(
                    "NOT PREPARED: bootstrap redeploy — this tree has no "
                    "bootstrap/bootstrap.py and no .tausik-lib/bootstrap/bootstrap.py, "
                    "so the step does not apply here. It has not failed."
                )
                continue
            proc = runner(
                argv,
                cwd=str(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                raise PreparationFailed(
                    f"preparation step '{step.name}' exited {proc.returncode} — the gates were "
                    f"NOT run, because a check over a tree that was not prepared would report "
                    f"on something other than what was asked for.\n"
                    f"{(proc.stderr or proc.stdout or '').strip()[:2000]}"
                )
            tail = (proc.stdout or "").strip().splitlines()
            said.append(f"PREPARED: {step.name} — {tail[-1] if tail else 'ok'}")
            continue

        step_targets = format_targets(root, targets, step.suffixes) if step.takes_files else []
        if step.takes_files and not step_targets:
            said.append(
                f"NOT PREPARED: {step.name} — no supported file in the declared scope, "
                "and applying it tree-wide would edit files nobody declared."
            )
            continue
        proc = runner(
            list(step.argv) + (step_targets if step.takes_files else []),
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise PreparationFailed(
                f"preparation step '{step.name}' exited {proc.returncode} — the gates were "
                f"NOT run, because a check over a tree that was not prepared would report "
                f"on something other than what was asked for.\n"
                f"{(proc.stderr or proc.stdout or '').strip()[:2000]}"
            )
        tail = (proc.stdout or "").strip().splitlines()
        said.append(f"PREPARED: {step.name} — {tail[-1] if tail else 'ok'}")
    return said


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
