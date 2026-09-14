"""`tausik publish` — build and verify the public snapshot (decision #368).

Two subcommands, both acts on OBJECTS: neither touches the working tree, the
index, a branch or a remote. Pushing the result and tagging it are the owner's
separate acts, done by hand after reading what this printed.

  publish snapshot --from <ref> --parent <public-head> [--message M] [--dry-run]
      Build the filtered tree of <ref> and commit it on top of <public-head>.
      Prints what went in, what stayed behind, the leak classes measured on
      the snapshot, and the pre-push checks. It refuses a parent that is not a
      commit — but it cannot know the REMOTE's tip: a stale local `github/main`
      is caught only by git's fast-forward-only push, which is the owner's act.

  publish verify --snapshot <sha> --from <ref>
      "GitLab is identical to GitHub": the snapshot's tree equals the filtered
      tree of <ref>, byte for byte; a mismatch names the paths.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import publication_scope as scope
import publication_snapshot as snap


def _root(svc: Any) -> str:
    return str(os.path.dirname(svc.tausik_dir()))


def cmd_publish(svc: Any, args: Any) -> None:
    sub = getattr(args, "publish_cmd", None)
    try:
        if sub == "snapshot":
            _snapshot(_root(svc), args)
            return
        if sub == "verify":
            _verify(_root(svc), args)
            return
    except scope.PublicationError as e:
        # A typo in --from / --snapshot is ordinary input, not a crash:
        # the refusal names the git answer, without a traceback.
        print(f"REFUSED: {e}")
        sys.exit(1)
    if True:
        print(
            "Usage: tausik publish snapshot --from <ref> --parent <public-head> [--dry-run]\n"
            "       tausik publish verify --snapshot <sha> --from <ref>"
        )
        sys.exit(2)


def _snapshot(root: str, args: Any) -> None:
    source, parent = args.source, args.parent
    # The cheap refusal first: a parent that is not a commit, before the scan.
    # What this CANNOT check is whether the parent is the remote's tip — the
    # command has no remote; git's fast-forward-only push is that guard.
    check = scope._git(root, "rev-parse", "--verify", f"{parent}^{{commit}}")
    if check.returncode != 0:
        print(
            f"REFUSED: --parent {parent} is not a commit in this repository: {check.stderr.strip()}"
        )
        sys.exit(1)
    kept, left = snap.snapshot_paths(root, source)
    print(f"Public snapshot of {source}:")
    print(f"  published: {len(kept)} file(s)")
    print(
        f"  excluded:  {len(left)} file(s) under {len(snap.EXCLUDED_FROM_PUBLIC_SNAPSHOT)} rule(s):"
    )
    for rule in snap.EXCLUDED_FROM_PUBLIC_SNAPSHOT:
        n = sum(1 for p in left if (p.startswith(rule) if rule.endswith("/") else p == rule))
        print(f"    {rule:<28} {n}")
    leaks = snap.leaks_in_snapshot(root, source)
    for name, files in leaks.items():
        print(f"  leak class '{name}': {len(files)} file(s)" + (f" — {files[:5]}" if files else ""))
    if any(leaks.values()):
        print(
            "REFUSED: a leak class is non-zero on the snapshot; the exclusion list did not cover it."
        )
        sys.exit(1)
    if args.dry_run:
        tree = snap.snapshot_tree(root, source)
        print(f"  filtered tree: {tree}")
        print(
            "DRY RUN — no commit written. Drop --dry-run to commit the snapshot on top of the parent."
        )
        return
    message = args.message or f"TAUSIK release snapshot of {source} (decision #368)"
    commit = snap.build_snapshot_commit(root, parent, message, source)
    ok_match, why_match = snap.snapshot_matches(root, commit, source)
    ok_base, why_base = scope.base_is_reachable(root, parent, commit)
    print(f"  snapshot commit: {commit}")
    print(f"  {'OK ' if ok_match else 'BAD'} {why_match}")
    print(f"  {'OK ' if ok_base else 'BAD'} {why_base}")
    if not (ok_match and ok_base):
        sys.exit(1)
    tag = _tag_named_by(root, source) or "v<version>"
    print(
        "Next (the owner's acts, by hand, after reading the above). The push is\n"
        "fast-forward only: if github/main moved since it was fetched, git refuses\n"
        "here and the snapshot is rebuilt on the new tip — never --force.\n"
        f"  git push github {commit}:refs/heads/main\n"
        f"  git push github {commit}:refs/tags/{tag}\n"
        "  then record the tag in tausik/published_tags.json (publishing.md)\n"
        "The tag is a refspec push, not `git tag -a`: the same NAME already names\n"
        "the release commit on the development line, and git will not create it\n"
        "twice. One name, two objects, one filtered tree — `publish verify` is the proof.\n"
        "It lands on GitHub as a LIGHTWEIGHT tag (no tag object, no message): the\n"
        "release notes are the CHANGELOG and the GitHub Release, not the tag."
    )


def _tag_named_by(root: str, source: str) -> str | None:
    """The tag name the printed act carries, read from `--from`.

    `--from v1.9.0` names the tag itself; `--from <sha>` or a branch that a
    single tag points at names it through `git tag --points-at`. Two or more
    tags on the commit is an ambiguity, and a placeholder is printed rather
    than a guess.
    """
    if scope._git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{source}").returncode == 0:
        return source
    commit = scope._git(root, "rev-parse", "--verify", "--quiet", f"{source}^{{commit}}")
    if commit.returncode != 0:
        return None
    names = scope._git(root, "tag", "--points-at", commit.stdout.strip()).stdout.split()
    return names[0] if len(names) == 1 else None


def _verify(root: str, args: Any) -> None:
    ok, why = snap.snapshot_matches(root, args.snapshot, args.source)
    print(("OK  " if ok else "BAD ") + why)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
