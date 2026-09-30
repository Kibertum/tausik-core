"""Directories git cannot see, which is how a shell artefact lives in a tree for months.

THE MEASUREMENT THAT FILED THIS. A repository inventory found three directories nobody made on
purpose: one named after an unexpanded shell variable, and two named after fragments of a
`git config` command that became redirect targets. They were 24 to 46 days old, and NONE of them
appeared in `git status`.

WHY GIT CANNOT SEE THEM, and this is the whole point: git tracks FILES. An empty directory has
none, and a directory whose only contents are ignored has none that count — so `git status` is
silent, `.gitignore` has nothing to say, and every gate in the project looks straight through
them. They are invisible to the one tool everybody checks.

WHAT THIS REFUSES TO FLAG. A deliberate empty directory is normal: the agent worktree root exists
to be filled, and a vendored repository's `.git/refs/tags` is git's own business. Those are
declared below with their reason. Without that list the check would report the same handful every
run, which is how a signal becomes noise and then gets switched off.

A NAME WITH SHELL METACHARACTERS IS REPORTED SEPARATELY from a merely empty one, because the two
are different findings: `$SCRATCH` is the residue of a command that went wrong, while an empty
`build/` is usually just empty.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Callable, Final, NamedTuple

#: Trees git manages itself or that a tool owns wholesale — walking into them says nothing about
#: this repository's hygiene and costs the walk its speed.
SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {".git", "__pycache__", "venv", ".venv", "node_modules", ".pytest_cache", ".mypy_cache"}
)

#: EMPTY, and that is the finding rather than an omission. Two entries lived here — the agent
#: worktree root and a vendored repository — and both turned out to be redundant the moment the
#: check started asking git whether the DIRECTORY ITSELF is ignored: git ignores both, so both were
#: already skipped as machine territory. A hand-written exception list that duplicates git's answer
#: is a second source of truth, and this one also hardcoded ONE profile directory while the engine
#: supports seven.
#:
#: The mechanism stays because a genuinely deliberate empty directory can exist under git's view —
#: and then it belongs here WITH ITS REASON, which is what the test on this dict requires.
DECLARED_EMPTY: Final[dict[str, str]] = {}

#: Characters a shell would have interpreted. A directory whose NAME holds one is the residue of a
#: command that went wrong, not a place someone chose to make — reported as its own kind, because
#: an empty `build/` is usually just empty while `$SCRATCH` never is.
SHELL_RESIDUE: Final[re.Pattern[str]] = re.compile(r"[$;|<>&`'\"*?()\[\]]")


class Finding(NamedTuple):
    path: str
    kind: str  # "shell-residue" or "empty"
    why: str


def _is_declared(rel: str) -> bool:
    rel = rel.replace(os.sep, "/")
    return any(rel == d or rel.startswith(d + "/") for d in DECLARED_EMPTY)


def _has_a_file(path: str) -> bool:
    """Does this directory hold any file at all, at any depth?

    The subject is EMPTINESS, not ignorance: a directory with ignored files in it is somebody's
    working state and git ignoring its contents was a deliberate act. What no check can see is a
    directory with nothing in it.
    """
    for entry in os.scandir(path):
        if entry.is_file():
            return True
        if entry.is_dir() and entry.name not in SKIP_DIRS and _has_a_file(entry.path):
            return True
    return False


def find(repo_root: str, is_ignored: Callable[[str], bool] | None = None) -> list[Finding]:
    """Empty directories git cannot see, shell residue first.

    ``is_ignored(rel)`` answers whether git ignores that path; a directory git ignores is
    MACHINE TERRITORY — every deployed profile and generated tree here is ignored as a directory —
    and its whole subtree is skipped. Injected rather than called directly so a test can describe
    a tree without a git repository in it, and so a broken git cannot silently empty the report.
    """
    ignored = is_ignored or (lambda _rel: False)
    out: list[Finding] = []
    for current, subdirs, _files in os.walk(repo_root):
        subdirs[:] = [d for d in subdirs if d not in SKIP_DIRS]
        kept: list[str] = []
        for name in subdirs:
            path = os.path.join(current, name)
            rel = os.path.relpath(path, repo_root).replace(os.sep, "/")
            if _is_declared(rel) or ignored(rel):
                continue  # declared, or machine territory — do not descend either
            kept.append(name)
            if _has_a_file(path):
                continue
            if SHELL_RESIDUE.search(name):
                out.append(
                    Finding(
                        rel,
                        "shell-residue",
                        "the name holds a character a shell would have interpreted — residue of a "
                        "command that went wrong, not a directory anyone chose",
                    )
                )
            else:
                out.append(
                    Finding(rel, "empty", "it holds no file at any depth, so no check can see it")
                )
        subdirs[:] = kept
    out.sort(key=lambda f: (f.kind != "shell-residue", f.path))
    return out


def render(findings: list[Finding]) -> str:
    if not findings:
        return ""
    lines = [f"{len(findings)} directory(ies) git cannot see:"]
    for f in findings:
        lines.append(f"  {f.path}  [{f.kind}] — {f.why}")
    lines.append("")
    lines.append(
        "Empty by design? Add it to `invisible_dirs.DECLARED_EMPTY` with the reason. Otherwise "
        "remove it: a directory no check can see is a directory that outlives the mistake."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """`--check` exits 1 on a finding. Silent when the tree is clean.

    Its own entry point rather than a doctor line: the answer needs a git probe per directory, and
    a command that costs something belongs where somebody asked for it rather than in a dashboard
    everybody runs.
    """
    import argparse
    import functools
    import subprocess

    p = argparse.ArgumentParser(description="Directories git cannot see")
    p.add_argument("--check", action="store_true", help="Exit 1 when something is found")
    p.add_argument("--repo-root", default=".")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    @functools.lru_cache(maxsize=None)
    def is_ignored(rel: str) -> bool:
        # FAILS CLOSED, deliberately: if git cannot answer, the directory is NOT treated as
        # machine territory, so a broken git widens the report instead of silencing it.
        try:
            done = subprocess.run(  # ruff-not-enabled: S603 - fixed argv, shell=False
                ["git", "check-ignore", "-q", "--", rel],
                cwd=args.repo_root,
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return done.returncode == 0

    findings = find(args.repo_root, is_ignored)
    text = render(findings)
    if text:
        print(text)
    return 1 if (args.check and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
