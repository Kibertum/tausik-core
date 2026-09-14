"""The public snapshot: the tracked tree MINUS one declared exclusion list.

Decision #368 (owner, session #251) changed what leaves for the public remote.
Under decision #257 `publication_scope.published_paths` had one rule —
"everything git tracks is published, there is no second rule" — and a module
whose whole point was to have NO exclusion list. Measured on the day the
owner ruled: `github/main` carried 2438 files of `tausik/` out of 3576, the
project's own accounting (tasks, decisions, memory) making up 70 % of what a
consumer cloned, and the two leak classes the publication guard still declares
as a remainder (internal host, dev-machine paths) lived almost entirely inside
that accounting. The public line is a release mirror, not a second archive.

So there IS an exclusion list now — and it keeps the property #257 was after,
which was never "no list" but "one reviewable declaration, checked by machine":

* `EXCLUDED_FROM_PUBLIC_SNAPSHOT` is the ONE list. It names directories of the
  state projection (which the GitLab line keeps committed on purpose — see the
  `.gitignore` note about `tausik/`) and three internal files. The ratchet
  files `tausik/*.json` stay: gates and tests read them.
* `snapshot_tree` builds the filtered tree from OBJECTS, through a temporary
  index — the working tree, the index and the branch are never touched.
* `snapshot_matches` is the machine's word for "GitLab is identical to GitHub":
  the snapshot's tree equals the filtered tree of the source, byte for byte,
  and a mismatch names the paths.

Everything else about the act is unchanged and still lives in
`publication_scope`: the snapshot is committed ON TOP of the public head
(`base_is_reachable`), never by force, and no tag is repointed by it.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

from publication_scope import PublicationError, _git, tree_of

#: The ONE declaration of what the public snapshot leaves out. Directories end
#: with `/` and match by prefix; files match whole. Decision #368.
EXCLUDED_FROM_PUBLIC_SNAPSHOT: tuple[str, ...] = (
    # The state projection: every task, story, epic, decision and memory row
    # serialised to Markdown so the DEVELOPMENT line can carry state between
    # machines. A consumer of the framework has no use for the framework's own
    # ledger, and it is where the declared leak remainder lives.
    "tausik/tasks/",
    "tausik/stories/",
    "tausik/epics/",
    "tausik/decisions/",
    "tausik/memory/",
    "tausik/graph-snapshots/",
    # Internal working documents: the scratch list, the release charter that
    # names decisions by number, and the GitLab pipeline of the development line.
    "TODO.md",
    "TAUSIK-plan-1.9.md",
    ".gitlab-ci.yml",
)


#: A file that DESCRIBES a leak class is not an occurrence of it — the same
#: allowlist `tests/test_publication_lines.py` keeps, plus the two changelogs,
#: whose one remaining match is the entry that names the class.
MAY_DESCRIBE_LEAKS: frozenset[str] = frozenset(
    {
        "docs/ru/publishing.md",
        "docs/en/publishing.md",
        "tests/test_publication_lines.py",
        "CHANGELOG.md",
        "CHANGELOG.ru.md",
    }
)


#: The two leak classes the publication guard still declares as a remainder
#: on the whole tree (`tests/test_publication_lines.py`); on the snapshot they
#: must be zero. Extended regular expressions, as `git grep -E` reads them.
LEAK_CLASSES: dict[str, str] = {
    "internal host": "gitlab\\.yumash\\.ru",
    "dev-machine path": "[Dd]:[\\\\/]{1,2}Work",
}


def is_excluded(path: str) -> bool:
    """Whether a tracked path stays behind. Prefix for directories, exact for files."""
    p = path.replace("\\", "/")
    for rule in EXCLUDED_FROM_PUBLIC_SNAPSHOT:
        if rule.endswith("/"):
            if p.startswith(rule):
                return True
        elif p == rule:
            return True
    return False


def tracked_at(repo_root: str, rev: str) -> tuple[str, ...]:
    """Every path in `rev`'s tree, in git's order."""
    result = _git(repo_root, "ls-tree", "-r", "--name-only", rev)
    if result.returncode != 0:
        raise PublicationError(f"git ls-tree {rev} failed: {result.stderr.strip()}")
    return tuple(line for line in result.stdout.splitlines() if line)


def snapshot_paths(repo_root: str, rev: str = "HEAD") -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(published, excluded) for `rev` — both lists, so a report can show each."""
    kept: list[str] = []
    left: list[str] = []
    for path in tracked_at(repo_root, rev):
        (left if is_excluded(path) else kept).append(path)
    return tuple(kept), tuple(left)


def snapshot_tree(repo_root: str, rev: str = "HEAD") -> str:
    """The filtered tree object of `rev`, built through a temporary index.

    `read-tree` loads the source tree into an index of its own, `rm --cached`
    drops the excluded paths from that index only, `write-tree` writes the
    result as an object. Nothing here reads or writes the working tree, the
    real index, or any ref — a publication is an act on objects (decision #260),
    and an act on objects cannot lose an uncommitted edit.
    """
    tree = tree_of(repo_root, rev)
    fd, index = tempfile.mkstemp(prefix="tausik-snapshot-", suffix=".idx")
    os.close(fd)
    os.remove(index)  # git wants to create it; an empty file is a corrupt index
    env = {**os.environ, "GIT_INDEX_FILE": index}
    try:
        r = subprocess.run(
            ["git", "read-tree", tree],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=120,
        )
        if r.returncode != 0:
            raise PublicationError(f"read-tree failed: {r.stderr.strip()}")
        # The RULES go on the command line, not the expanded file list: 3090
        # paths overflow the Windows command line (WinError 206), and `rm -r`
        # on a directory prefix is the same set. `--ignore-unmatch` covers a
        # rule that names nothing in this revision.
        rules = [rule.rstrip("/") for rule in EXCLUDED_FROM_PUBLIC_SNAPSHOT]
        if rules:
            r = subprocess.run(
                ["git", "rm", "--cached", "-r", "-q", "--ignore-unmatch", "--", *rules],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdin=subprocess.DEVNULL,
                timeout=300,
            )
            if r.returncode != 0:
                raise PublicationError(f"rm --cached failed: {r.stderr.strip()}")
        r = subprocess.run(
            ["git", "write-tree"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=120,
        )
        if r.returncode != 0:
            raise PublicationError(f"write-tree failed: {r.stderr.strip()}")
        return r.stdout.strip()
    finally:
        try:
            os.remove(index)
        except OSError:
            pass


def build_snapshot_commit(repo_root: str, base: str, message: str, source: str = "HEAD") -> str:
    """Commit the filtered tree of `source` ON TOP of `base`; return the commit.

    `base` is the public head and becomes the parent, so the public history
    gains a commit rather than being replaced (`base_is_reachable` proves it
    afterwards). `commit-tree`, not checkout/commit: no ref moves here.
    """
    tree = snapshot_tree(repo_root, source)
    result = _git(repo_root, "commit-tree", tree, "-p", base, "-m", message)
    if result.returncode != 0:
        raise PublicationError(f"commit-tree failed: {result.stderr.strip()}")
    return result.stdout.strip()


def snapshot_matches(repo_root: str, snapshot: str, source: str = "HEAD") -> tuple[bool, str]:
    """ "GitLab is identical to GitHub", asked of objects: does `snapshot`'s tree
    equal the filtered tree of `source`? A mismatch names the paths, both ways —
    a file the snapshot lost and a file it carries that the filter would drop.
    """
    expected = snapshot_tree(repo_root, source)
    actual = tree_of(repo_root, snapshot)
    if expected == actual:
        return True, f"snapshot tree {actual[:12]} equals the filtered tree of {source}"
    result = _git(repo_root, "diff-tree", "-r", "--name-status", expected, actual)
    if result.returncode != 0:
        raise PublicationError(f"diff-tree failed: {result.stderr.strip()}")
    changed = [line for line in result.stdout.splitlines() if line]
    head = "\n".join(f"  {line}" for line in changed[:20])
    more = f"\n  ... and {len(changed) - 20} more" if len(changed) > 20 else ""
    return False, (
        f"snapshot differs from the filtered tree of {source} in {len(changed)} path(s) "
        f"(A = only in the snapshot, D = missing from it, M = same path, different "
        f"content):\n{head}{more}"
    )


def leaks_in_snapshot(repo_root: str, rev: str = "HEAD") -> dict[str, list[str]]:
    """The publication guard's leak classes, measured on the SNAPSHOT set.

    `tests/test_publication_lines.py` declares two classes as a remainder on
    the whole tree; on the snapshot they are expected at zero, because the
    remainder lives in the excluded accounting. Reads blobs of the source
    REVISION, never the working tree (a snapshot is of a commit) — one
    `git grep` per class over the revision, then the hits are kept to the
    snapshot set in Python: a `git show` per file cost 23 s over 1300 files
    (review, session #256), and a path list on the command line is what
    overflows Windows.
    """
    kept = set(snapshot_paths(repo_root, rev)[0])
    hits: dict[str, list[str]] = {}
    for name, pattern in LEAK_CLASSES.items():
        r = _git(repo_root, "grep", "-I", "-l", "-i", "-E", "-e", pattern, rev)
        # exit 1 = no match; anything above is a real failure
        if r.returncode not in (0, 1):
            raise PublicationError(f"git grep failed: {r.stderr.strip()}")
        found = []
        for line in r.stdout.splitlines():
            path = line.split(":", 1)[1] if ":" in line else line
            if path in kept and path not in MAY_DESCRIBE_LEAKS:
                found.append(path)
        hits[name] = found
    return hits
