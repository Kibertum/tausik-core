"""What the state projection costs the tree, measured rather than guessed.

THE GUESS THAT FILED THIS. A hygiene story planned on the belief that soft-archiving old
done tasks would cut a projection occupying 69% of the tree. Both halves were wrong:
`state_export` selects FROM tasks with NO `archived_at` filter, so archiving changes the
projection by nothing at all; and even if archived rows did leave, the reachable shrink is
a fifth of the paths, not two thirds.

WHY THE PROJECTION CANNOT SIMPLY SHRINK, which is the fact the guess was missing:
`.tausik/tausik.db` is GITIGNORED. The Markdown tree is the only carrier of state between
machines, so a row dropped from it is a row a fresh clone never sees. Hiding a task from
`task list` and deleting its file are different acts, and only the first is what archival
was for.

DESCRIPTIVE, NOT A GATE. This reports; it never fails a build. A threshold on "projection
share of the tree" would be crossed by ordinary work — every closed task adds a file — and
a threshold ordinary work crosses is one somebody switches off, taking the measurement with
it. The lever that does bound the growth is per-entry journal length, which already has a
budget at the point of writing.
"""

from __future__ import annotations

import os
import subprocess
from typing import Final, NamedTuple

#: The projection subtrees, in the order the report reads best: biggest first, because the
#: answer to "what costs" is the first line and the rest is context.
KINDS: Final[tuple[str, ...]] = (
    "tasks",
    "memory",
    "decisions",
    "stories",
    "epics",
    "graph-snapshots",
)

#: The section header a task file's journal starts at. The journal is where the evidence of
#: a closure lives, so it is also where the bytes are — measured separately because it is
#: the one part of the projection whose size is a WRITING habit rather than a row count.
JOURNAL_HEADING: Final[str] = "\n## Journal"


class Kind(NamedTuple):
    name: str
    files: int
    bytes_: int

    @property
    def avg(self) -> int:
        return self.bytes_ // self.files if self.files else 0


class Census(NamedTuple):
    tracked_files: int
    tracked_bytes: int
    kinds: tuple[Kind, ...]
    journal_bytes: int

    @property
    def files(self) -> int:
        return sum(k.files for k in self.kinds)

    @property
    def bytes_(self) -> int:
        return sum(k.bytes_ for k in self.kinds)

    @property
    def path_share(self) -> float:
        return 100.0 * self.files / self.tracked_files if self.tracked_files else 0.0

    @property
    def byte_share(self) -> float:
        return 100.0 * self.bytes_ / self.tracked_bytes if self.tracked_bytes else 0.0


def tracked_files(repo_root: str) -> list[str]:
    """Paths git tracks. Untracked files are somebody's working state, not the tree."""
    done = subprocess.run(  # ruff-not-enabled: S603 - fixed argv, shell=False
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    if done.returncode != 0:
        return []
    return [p for p in done.stdout.decode("utf-8", "replace").split("\0") if p]


def _size(repo_root: str, rel: str) -> int:
    try:
        return os.path.getsize(os.path.join(repo_root, rel))
    except OSError:
        return 0  # a tracked path missing from the checkout contributes nothing, not a crash


def journal_bytes(repo_root: str, paths: list[str]) -> int:
    """Bytes of task files that sit below `## Journal`.

    Separated from the rest because it answers a different question: the row count is what
    the project has DONE, while the journal is how much was written about each closure —
    the only part a habit can move.
    """
    total = 0
    for rel in paths:
        full = os.path.join(repo_root, rel)
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        idx = text.find(JOURNAL_HEADING)
        if idx >= 0:
            total += len(text[idx:].encode("utf-8"))
    return total


def census(repo_root: str = ".") -> Census:
    """Count and weigh the projection against the whole tracked tree."""
    paths = tracked_files(repo_root)
    tracked_bytes = sum(_size(repo_root, p) for p in paths)
    by_kind: dict[str, list[int]] = {k: [0, 0] for k in KINDS}
    task_paths: list[str] = []
    for rel in paths:
        parts = rel.replace(os.sep, "/").split("/")
        if len(parts) < 3 or parts[0] != "tausik":
            continue
        kind = parts[1]
        if kind not in by_kind:
            continue
        size = _size(repo_root, rel)
        by_kind[kind][0] += 1
        by_kind[kind][1] += size
        if kind == "tasks":
            task_paths.append(rel)
    kinds = tuple(Kind(k, by_kind[k][0], by_kind[k][1]) for k in KINDS if by_kind[k][0])
    return Census(
        tracked_files=len(paths),
        tracked_bytes=tracked_bytes,
        kinds=kinds,
        journal_bytes=journal_bytes(repo_root, task_paths),
    )


def reachable_shrink(conn, repo_root: str = ".", age_days: int = 90) -> tuple[int, int]:
    """``(files, bytes)`` that WOULD leave if archived task files stopped being exported.

    The number exists to be compared with the guess that filed this: it is the ceiling on
    what archival could ever remove from the tree, and it is far from the whole projection.
    Nothing here removes anything — the cost of removal is that a fresh clone loses those
    tasks, since the database does not travel.
    """
    rows = conn.execute(
        "SELECT slug FROM tasks WHERE status='done' AND completed_at IS NOT NULL "
        "AND completed_at <= datetime('now', ?)",
        (f"-{int(age_days)} days",),
    ).fetchall()
    files = 0
    total = 0
    for (slug,) in rows:
        rel = f"tausik/tasks/{slug}.md"
        if os.path.isfile(os.path.join(repo_root, rel)):
            files += 1
            total += _size(repo_root, rel)
    return files, total


def render(c: Census, shrink: tuple[int, int] | None = None) -> str:
    """The report. First line is the answer; the rest is what it is made of."""
    lines = [
        f"State projection: {c.files} of {c.tracked_files} tracked files "
        f"({c.path_share:.1f}% of paths, {c.byte_share:.1f}% of bytes)",
        "",
    ]
    for k in c.kinds:
        share = 100.0 * k.bytes_ / c.tracked_bytes if c.tracked_bytes else 0.0
        lines.append(
            f"  {k.name:<16} {k.files:>5} files  {k.bytes_:>11,} bytes  "
            f"avg {k.avg:>6}  {share:4.1f}% of tree"
        )
    tasks = next((k for k in c.kinds if k.name == "tasks"), None)
    if tasks and tasks.bytes_:
        lines += [
            "",
            f"  Journals are {100.0 * c.journal_bytes / tasks.bytes_:.1f}% of task-file bytes "
            f"({c.journal_bytes:,}) — the one part a writing habit moves, and it has a "
            f"budget at the point of writing.",
        ]
    if shrink is not None:
        files, total = shrink
        lines += [
            "",
            f"  Archival could reach at most {files} files ({total:,} bytes, "
            f"{100.0 * files / c.tracked_files:.1f}% of paths) — and does not today: the "
            f"exporter has no archived_at filter. Removing them would cost a fresh clone "
            f"those tasks, because .tausik/tausik.db is gitignored and the tree is the "
            f"only carrier.",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """`tausik`-independent entry point. Always exits 0: this measures, it does not judge."""
    import argparse
    import sys

    p = argparse.ArgumentParser(description="What the state projection costs the tree")
    p.add_argument("--repo-root", default=".")
    p.add_argument(
        "--db",
        default=None,
        help="Path to tausik.db — adds the ceiling on what archival could ever remove",
    )
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    c = census(args.repo_root)
    shrink = None
    if args.db:
        import sqlite3

        conn = sqlite3.connect(args.db)
        try:
            shrink = reachable_shrink(conn, args.repo_root)
        finally:
            conn.close()
    print(render(c, shrink))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
