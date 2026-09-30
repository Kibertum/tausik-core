"""`tausik changelog` — the per-task fragments and folding them into the shipped files.

A thin presentation layer. Everything about what a fragment IS, and what folding means,
lives in `changelog_fragments`; this decides only the exit code and what gets printed.
"""

from __future__ import annotations

from typing import Any


def cmd_changelog(svc: Any, args: Any) -> None:
    """Handle the `changelog` subcommands."""
    sub = getattr(args, "changelog_cmd", None) or "assemble"
    if sub != "assemble":
        print(f"changelog: unknown subcommand '{sub}'. Known: assemble.")
        raise SystemExit(2)

    from changelog_fragments import MalformedFragment, assemble
    from project_root import root_from_service

    root = root_from_service(svc)
    if not root:
        # Assembly WRITES two files and deletes several. Doing that wherever the process
        # happens to stand would edit another checkout, so a service that names no project
        # gets a refusal rather than a best guess.
        print(
            "changelog assemble: this service names no project root, and assembly writes "
            "to the changelogs and removes the fragments. Refusing rather than guessing "
            "at which tree was meant."
        )
        raise SystemExit(2)
    try:
        for line in assemble(root, apply=bool(getattr(args, "apply", False))):
            print(line)
    except MalformedFragment as exc:
        # NOTHING was written: `assemble` reads every fragment before touching a file, so
        # a bad one stops the whole fold rather than leaving half of them applied and the
        # rest deleted with nothing to show for them.
        print(f"changelog assemble refused, and nothing was written: {exc}")
        raise SystemExit(2) from exc


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
