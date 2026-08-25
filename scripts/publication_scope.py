"""The ONE declaration of what leaves this repository for the public remote.

Decision #257 settled the direction: GitHub becomes the primary place of
development, GitLab becomes its mirror, and the public history moves FORWARD
from the current point instead of being rewritten. That decision makes the scope
rule small enough to state in a sentence:

    Everything git tracks is published. Nothing else is. There is no second rule.

The sentence is short, and that is exactly why it needs a module. Publication
before #257 was a hand-curated snapshot -- 1069 files out of 3403, chosen by a
person, re-chosen at every release -- and nobody could say from the repository
alone which of the two numbers was correct or why. A rule that lives only in
somebody's habit is indistinguishable from no rule at all: it cannot be wrong,
so it cannot be checked, so it drifts without ever failing.

WHAT THIS MODULE DELIBERATELY DOES NOT HAVE: an exclusion list, an include
pattern, a filter hook. `published_paths` asks git and returns the answer
unmodified. Adding a filter here is the failure this module exists to prevent,
and `tests/test_publication_scope.py` asserts the returned set equals git's own
output precisely so that adding one turns red instead of shipping quietly.

The boundary between "published" and "kept" therefore belongs to `.gitignore`
and to nothing else. That is a real, single, reviewable place -- and it is the
place a reader already looks.

The three pre-push checks live here too, next to the rule they protect, because
each of them answers a question about the SAME act: does the publication commit
keep the public history intact?

  * `nothing_dropped`   -- the commit publishes HEAD's tree entire, not a subset.
  * `base_is_reachable` -- the existing public head stays in the new history.
  * `tags_unmoved`      -- no tag is repointed by the act of publishing.

None of the three can be answered by reading a diff, and all three are cheap.
They are separate functions rather than one `verify()` so that a caller reports
WHICH promise broke -- a single boolean would leave the operator guessing at the
one moment when guessing is least affordable.
"""

from __future__ import annotations

import subprocess

_TIMEOUT = 120


def _git(repo_root: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run git in `repo_root` and hand back the completed process.

    Failures are NOT swallowed into a default here. Every caller in this module
    turns a non-zero return code into a named refusal, because the whole point
    of the module is that publication never proceeds on a silent assumption.
    """
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=_TIMEOUT,
        # Without this a git subcommand that decides to prompt (credentials, a
        # pager, an editor) inherits the caller's stdin and waits forever. In an
        # MCP-reachable module there is no terminal to answer it, so the hang is
        # indistinguishable from a slow repository. Pinned by
        # tests/test_risk_compute_stdin.py, which caught this exact omission.
        stdin=subprocess.DEVNULL,
    )


class PublicationError(RuntimeError):
    """A git command needed to answer a publication question did not answer it.

    Raised rather than returned: a caller that cannot tell "the check passed"
    from "the check could not run" would report the second as the first, which
    is the exact conflation `check-result-conflates-could-not-run-with-passed`
    was filed about. Publication is irreversible, so it fails loudly instead.
    """


def published_paths(repo_root: str) -> tuple[str, ...]:
    """Every path that goes out, in git's own order.

    This IS the rule. It has no parameters beyond the repository because there
    is nothing to choose: the tracked set is the published set.

    Note what is absent by construction -- ignored files, untracked files, and
    anything a person felt should stay behind. If a file must not be published,
    it must not be tracked, and `.gitignore` is where that is said.
    """
    result = _git(repo_root, "ls-files")
    if result.returncode != 0:
        raise PublicationError(f"git ls-files failed: {result.stderr.strip()}")
    return tuple(line for line in result.stdout.splitlines() if line)


def tree_of(repo_root: str, rev: str) -> str:
    """The tree object `rev` points at.

    Comparing TREES rather than diffs is what makes "nothing was dropped"
    provable in one comparison: two commits with the same tree hold byte
    identical content, whatever their messages, parents or authors say.
    """
    result = _git(repo_root, "rev-parse", f"{rev}^{{tree}}")
    if result.returncode != 0:
        raise PublicationError(f"cannot resolve tree of {rev}: {result.stderr.strip()}")
    return result.stdout.strip()


def build_publication_commit(repo_root: str, base: str, message: str, source: str = "HEAD") -> str:
    """Commit `source`'s tree ON TOP of `base`, and return the new commit.

    `base` is the public head. Passing it as the parent is the whole of AC5: the
    public history gains a commit instead of being replaced by one, so every
    object reachable from `base` stays reachable, and consumers who pinned a SHA
    keep resolving it.

    Uses `commit-tree` rather than checkout/add/commit on purpose: this must not
    touch the working tree, the index, or the current branch. The publication is
    an act on objects, and an act on objects cannot lose an uncommitted edit.
    """
    tree = tree_of(repo_root, source)
    result = _git(repo_root, "commit-tree", tree, "-p", base, "-m", message)
    if result.returncode != 0:
        raise PublicationError(f"commit-tree failed: {result.stderr.strip()}")
    return result.stdout.strip()


def nothing_dropped(repo_root: str, commit: str, source: str = "HEAD") -> tuple[bool, str]:
    """Does `commit` publish `source`'s tree entire?

    Answers with the tree comparison first and only reaches for a diff to SAY
    what differs. A caller told "the trees differ" still has to open a terminal;
    a caller told which paths differ does not.
    """
    if tree_of(repo_root, commit) == tree_of(repo_root, source):
        return True, "publication tree is identical to the source tree"

    result = _git(repo_root, "diff", "--name-status", commit, source)
    if result.returncode != 0:
        raise PublicationError(f"git diff failed: {result.stderr.strip()}")
    changed = [line for line in result.stdout.splitlines() if line]
    head = "\n".join(f"  {line}" for line in changed[:20])
    more = f"\n  ... and {len(changed) - 20} more" if len(changed) > 20 else ""
    return False, f"publication tree differs from {source} in {len(changed)} path(s):\n{head}{more}"


def base_is_reachable(repo_root: str, base: str, commit: str) -> tuple[bool, str]:
    """Is the old public head still part of the new history?

    The question that separates "we published" from "we overwrote". A force-push
    onto an unrelated commit answers no, and answering no AFTER the push is not
    an answer at all -- the objects are already unreferenced on the remote.
    """
    result = _git(repo_root, "merge-base", "--is-ancestor", base, commit)
    if result.returncode == 0:
        return True, f"{base} remains an ancestor of {commit}"
    if result.returncode == 1:
        return False, f"{base} is NOT an ancestor of {commit} -- this would orphan public history"
    raise PublicationError(f"merge-base failed: {result.stderr.strip()}")


def tag_map(repo_root: str) -> dict[str, str]:
    """Every tag and the object it names, as a snapshot to compare against.

    Taken before and after so the comparison is against MEASURED state rather
    than against a remembered count. "22 tags" is not the promise; "these 22
    tags still name these 22 objects" is.
    """
    result = _git(
        repo_root, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/tags/"
    )
    if result.returncode != 0:
        raise PublicationError(f"for-each-ref failed: {result.stderr.strip()}")
    out: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        name, _, sha = line.partition(" ")
        out[name] = sha.strip()
    return out


def tags_unmoved(before: dict[str, str], after: dict[str, str]) -> tuple[bool, str]:
    """Did any tag change, appear, or vanish between the two snapshots?

    All three count as movement. A tag that DISAPPEARS is as broken a pin for a
    consumer as one that moved, and a check that only compared shared keys would
    call that case clean.
    """
    problems: list[str] = []
    for name in sorted(set(before) | set(after)):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        if old is None:
            problems.append(f"{name}: appeared -> {new}")
        elif new is None:
            problems.append(f"{name}: vanished (was {old})")
        else:
            problems.append(f"{name}: {old} -> {new}")
    if not problems:
        return True, f"all {len(before)} tag(s) still name the same objects"
    return False, "tags moved:\n" + "\n".join(f"  {p}" for p in problems)
