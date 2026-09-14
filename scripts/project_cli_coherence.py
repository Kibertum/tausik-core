"""`tausik coherence` — assemble the repository-wide material, on demand only.

ON DEMAND IS PART OF THE DESIGN, not an omission. A repository review is
expensive and earns its keep by being rare; hanging it on every task closure
would turn it into noise the agent learns to scroll past, which is the failure
this lens is supposed to avoid rather than join. Nothing calls this
automatically, and no gate depends on it.

The command COLLECTS and prints. It does not judge — that is a model's job over
this output — and it does not file anything, because a lens that opens its own
tasks is grading its own homework.
"""

from __future__ import annotations

from typing import Any

from project_service import ProjectService


def cmd_coherence(svc: ProjectService, args: Any) -> None:
    """Handle `tausik coherence [--json]`."""
    import repo_coherence

    tasks = svc.be.task_list(limit=100000)
    material = repo_coherence.collect(".", tasks=tasks, service=svc)

    if getattr(args, "json", False):
        print(repo_coherence.render_json(material))
        return

    print(repo_coherence.render_markdown(material))
    print()
    print(
        f"Collectors: {material['collectors_run']} run, "
        f"{len(material['collectors_skipped'])} skipped."
    )
    if not material["findings"]:
        # Said on the terminal too, not only inside the document: the reader who
        # runs this and sees nothing is exactly the reader most likely to
        # conclude the repository is fine.
        print("NOTE: no finding is a suspicious result, not a clean bill — check the collectors.")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
