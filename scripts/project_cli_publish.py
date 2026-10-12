"""`tausik publish` — build and verify the public snapshot (decision #368).

Snapshot construction acts on OBJECTS: it touches neither the working tree,
index, branches nor remotes. Pushing and tagging remain the owner's separate
acts, done by hand only when the preceding check prints them.

  publish snapshot --from <ref> --parent <public-head> [--message M] [--dry-run]
      Build the filtered tree of <ref> and commit it on top of <public-head>.
      Prints what went in, what stayed behind, the leak classes measured on
      the snapshot, and the pre-push checks. It refuses a parent that is not a
      commit — but it cannot know the REMOTE's tip: a stale local `github/main`
      is caught only by git's fast-forward-only push, which is the owner's act.

  publish verify --snapshot <sha> --from <ref>
      "GitLab is identical to GitHub": the snapshot's tree equals the filtered
      tree of <ref>, byte for byte; a mismatch names the paths.

  publish ci-check --snapshot <sha> --from <ref> --tag <tag>
      Read GitHub Actions and wait for Tests success on that exact snapshot.
      Only success reveals the public tag refspec; this command moves no ref.

  publish notes --version X.Y.Z --body-file F     (release_notes)
  publish senar-check                             (senar_claim)
      Two checks of the release procedure, run before the owner tags: the
      release body links both whats-new pages; the SENAR edition TAUSIK claims
      is published on GitHub (exit 1 missing, 2 could not ask).
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import publication_scope as scope
import publication_snapshot as snap

_RELEASE_TAG = re.compile(r"^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)$")


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
        if sub == "ci-check":
            _ci_check(_root(svc), args)
            return
        if sub == "recovery":
            _recovery(_root(svc), args)
            return
        if sub == "remote-audit":
            _remote_audit(_root(svc), args)
            return
        if sub == "notes":
            _notes(args)
            return
        if sub == "senar-check":
            _senar_check()
            return
    except scope.PublicationError as e:
        # A typo in --from / --snapshot is ordinary input, not a crash:
        # the refusal names the git answer, without a traceback.
        print(f"REFUSED: {e}")
        sys.exit(1)
    if True:
        print(
            "Usage: tausik publish snapshot --from <ref> --parent <public-head> [--dry-run]\n"
            "       tausik publish recovery --from <ref> [--dry-run]\n"
            "       tausik publish remote-audit --remote <url> --ref <ref> --from <ref>\n"
            "       tausik publish verify --snapshot <sha> --from <ref>\n"
            "       tausik publish ci-check --snapshot <sha> --from <ref> --tag <tag>\n"
            "       tausik publish notes --version <X.Y.Z> --body-file <file>\n"
            "       tausik publish senar-check"
        )
        sys.exit(2)


def _notes(args: Any) -> None:
    """The release body links both whats-new pages (docs/en/publishing.md)."""
    from release_notes import missing_links

    with open(args.body_file, encoding="utf-8") as f:
        missing = missing_links(f.read(), args.version)
    if missing:
        print("REFUSED: the release body does not link " + ", ".join(missing))
        sys.exit(1)
    print(f"OK: the release body of {args.version} links both whats-new pages")


def _senar_check() -> None:
    """The claimed SENAR edition is public before a release tag (senar_claim)."""
    from senar_claim import check_message, published

    status, detail = published()
    print(check_message(status, detail))
    if status != "published":
        sys.exit(1 if status == "not-published" else 2)


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
    public, why_public = snap.snapshot_history_is_public(root, parent, source)
    if not public:
        print(f"REFUSED: unsafe public parent {parent}: {why_public}")
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
    source_commit = scope._git(root, "rev-parse", "--verify", f"{source}^{{commit}}")
    print(
        "Next (the owner's acts, by hand, after reading the above). The push is\n"
        "fast-forward only: if github/main moved since it was fetched, git refuses\n"
        "here and the snapshot is rebuilt on the new tip — never --force.\n"
        f"  git push github {commit}:refs/heads/main\n"
        f"  tausik publish ci-check --snapshot {commit} "
        f"--from {source_commit.stdout.strip()} --tag {tag}\n"
        "Do not push the tag or create the GitHub Release until `ci-check` succeeds\n"
        "for this exact public snapshot SHA. GitLab CI proves a different tree."
    )


def _tag_named_by(root: str, source: str) -> str | None:
    """The tag name the printed act carries, read from `--from`.

    `--from v1.9.0` names the tag itself; `--from <sha>` or a branch that a
    single tag points at names it through `git tag --points-at`. Two or more
    tags on the commit is an ambiguity, and a placeholder is printed rather
    than a guess.
    """
    if (
        _RELEASE_TAG.fullmatch(source)
        and scope._git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{source}").returncode
        == 0
    ):
        return source
    commit = scope._git(root, "rev-parse", "--verify", "--quiet", f"{source}^{{commit}}")
    if commit.returncode != 0:
        return None
    names = scope._git(root, "tag", "--points-at", commit.stdout.strip()).stdout.split()
    return names[0] if len(names) == 1 and _RELEASE_TAG.fullmatch(names[0]) else None


def _verify(root: str, args: Any) -> None:
    ok, why = snap.snapshot_candidate_is_public(root, args.snapshot, args.source)
    print(("OK  " if ok else "BAD ") + why)
    if not ok:
        sys.exit(1)


def _ci_check(root: str, args: Any) -> None:
    """Unlock the tag act only after GitHub Tests succeeds for the exact SHA."""
    import ci_lane_status

    ok, why = snap.snapshot_candidate_is_public(root, args.snapshot, args.source)
    if not ok:
        print("REFUSED: candidate failed the local snapshot audit: " + why)
        sys.exit(1)
    snapshot = scope._git(root, "rev-parse", "--verify", f"{args.snapshot}^{{commit}}")
    source = scope._git(root, "rev-parse", "--verify", f"{args.source}^{{commit}}")
    tag = str(args.tag)
    if not _RELEASE_TAG.fullmatch(tag):
        print("REFUSED: --tag must be a plain vMAJOR.MINOR.PATCH release tag")
        sys.exit(1)
    tagged = scope._git(root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    if tagged.returncode != 0:
        print(f"REFUSED: local release tag {tag} does not exist")
        sys.exit(1)
    if tagged.stdout.strip() != source.stdout.strip():
        print(f"REFUSED: local release tag {tag} does not name --from {args.source}")
        sys.exit(1)
    remotes = scope._git(root, "remote", "-v")
    slug = (
        ci_lane_status.named_github_slug(remotes.stdout, "github")
        if remotes.returncode == 0
        else None
    )
    if not slug:
        print("REFUSED: remote 'github' is missing or is not a canonical GitHub repository URL")
        sys.exit(1)
    passed, verdict = ci_lane_status.wait_for_exact(
        slug,
        snapshot.stdout.strip(),
        timeout=args.timeout,
        poll_interval=args.poll_interval,
    )
    if not passed:
        print("REFUSED: " + verdict)
        sys.exit(1)
    print("OK  " + verdict)
    print(
        "Next (the owner's act, by hand). Push the LIGHTWEIGHT public tag only now:\n"
        f"  git push github {snapshot.stdout.strip()}:refs/tags/{tag}\n"
        "Then record the tag in tausik/published_tags.json and create the GitHub Release.\n"
        "The local annotated tag remains on the development commit; the public tag is a\n"
        "refspec to the filtered snapshot."
    )


def _recovery(root: str, args: Any) -> None:
    """Build an orphan candidate without implying permission to replace a ref."""
    source = args.source
    leaks = snap.leaks_in_snapshot(root, source)
    if any(leaks.values()):
        print("REFUSED: a leak class is non-zero on the recovery snapshot.")
        sys.exit(1)
    tree = snap.snapshot_tree(root, source)
    if args.dry_run:
        print(f"Recovery snapshot of {source}: filtered tree {tree}")
        print("DRY RUN — no commit written and no ref moved.")
        return
    message = args.message or f"TAUSIK recovery snapshot of {source}"
    commit = snap.build_recovery_snapshot_commit(root, message, source)
    ok, why = snap.snapshot_candidate_is_public(root, commit, source)
    if not ok:
        print("REFUSED: recovery candidate failed its own audit: " + why)
        sys.exit(1)
    print(f"  recovery commit: {commit}")
    print("  OK  " + why)
    print(
        "OWNER APPROVAL REQUIRED — this command moved no ref and deliberately prints no push "
        "command. Back up exact remote refs and follow the containment runbook before any "
        "replacement."
    )


def _remote_audit(root: str, args: Any) -> None:
    from publication_remote_audit import audit_remote_ref

    ok, why, observed = audit_remote_ref(root, args.remote, args.ref, args.source)
    print(("OK  " if ok else "BAD ") + f"{observed} — {why}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
