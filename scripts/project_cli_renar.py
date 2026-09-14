"""TAUSIK CLI handler for `tausik renar` (v16r-conformance-yaml).

`tausik renar conformance` generates a RENAR-CONFORMANCE.yaml self-assessment
whose level is computed from live DB state (§13.4.3), not declared. Prints to
stdout; `--write` persists to RENAR-CONFORMANCE.yaml at the project root.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import git_exec
from project_config import load_config
from project_service import ProjectService
from renar_conformance import generate
from tausik_utils import ServiceError, utcnow_iso

# Neutral fallback when no assessor can be resolved. Surfaced verbatim in the
# manifest so a self-assessment is never silently attributed to a real person.
FALLBACK_ASSESSOR = "unknown-assessor"

# The audit journal of §13.4.1 is this file's git history — one name, used by
# the writer and by both readers of a predecessor.
MANIFEST_FILENAME = "RENAR-CONFORMANCE.yaml"

# Bound for every git call here: reading one blob out of HEAD is local and
# fast, and an unbounded git call is itself a hang risk (see git_exec).
_GIT_TIMEOUT = 10


def _git_user_name() -> str | None:
    """Best-effort `git config user.name`. None on any failure (no git, no repo)."""
    try:
        out = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    name = (out.stdout or "").strip()
    return name or None


def resolve_assessor(explicit: str | None, cfg: dict | None = None) -> str:
    """Resolve the conformance assessor id without baking in any personal identity.

    Resolution order: explicit --assessor → config['renar_default_assessor'] →
    git user.name → neutral FALLBACK_ASSESSOR. The fallback is intentional and
    visible: a manifest must never misattribute the self-assessment to a real
    person who did not run it.
    """
    if explicit and explicit.strip():
        return explicit.strip()
    cfg = cfg if cfg is not None else load_config()
    # `or ""` collapses a JSON null (Python None) to "" — a present-but-null
    # config key would otherwise make `cfg.get(key, "")` return None, and
    # str(None) == "None" would be returned as a (fictional) assessor id.
    configured = str(cfg.get("renar_default_assessor") or "").strip()
    if configured:
        return configured
    git_name = _git_user_name()
    if git_name:
        return git_name
    return FALLBACK_ASSESSOR


def _parse_manifest(text: str) -> tuple[int, str | None]:
    """(manifest-version, manifest-id) from manifest YAML text; (0, None) if unreadable.

    One parser for both sources of a manifest — the working copy and the audit
    journal — so the two can never disagree about how a manifest is read.
    """
    try:
        import yaml  # lazy: PyYAML is an optional RENAR dep, not a core CLI dep
    except ModuleNotFoundError:
        return 0, None
    try:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            return 0, None
        mid = data.get("manifest-id")
        return int(data.get("manifest-version", 0)), (str(mid) if mid else None)
    except (TypeError, ValueError, yaml.YAMLError):
        return 0, None


def _existing_manifest(path: str) -> tuple[int, str | None]:
    """(manifest-version, manifest-id) of an existing manifest; (0, None) if absent."""
    if not os.path.isfile(path):
        return 0, None
    try:
        with open(path, encoding="utf-8") as f:
            return _parse_manifest(f.read())
    except OSError:
        return 0, None


def _existing_version(path: str) -> int:
    """Read manifest-version from an existing manifest; 0 if absent/unreadable."""
    return _existing_manifest(path)[0]


def journal_manifest(root: str) -> tuple[int, str | None] | None:
    """(version, id) of the manifest as the AUDIT JOURNAL holds it — git HEAD.

    §13.4.1 makes the artifact's git history the audit journal, so the entry a
    new manifest supersedes is the one at HEAD, not the one on disk: an
    uncommitted `--write` bumps the working copy without ever entering the
    journal.

    Returns ``None`` — not ``(0, None)`` — whenever the journal cannot be read
    (no git, not a repository, no commits, a damaged object store). The
    distinction is the whole point: "the journal holds no manifest" is a fact
    this module acts on, "the journal is unreadable" is not, and only the
    latter falls back to the working copy.

    ABSENCE IS ASKED AS ITS OWN QUESTION, because `git_exec.run` does not raise
    on a non-zero exit (by design) and git answers 128 to nearly everything.
    Reading absence off `git show`'s exit code therefore sorted every failure
    it can have — a pruned blob, a locked object file, a partial clone that
    could not fetch — onto the "journal is empty" side, which is the one side
    that deliberately refuses to fall back. `ls-tree` separates the three
    states without ambiguity: non-zero is an error, zero with no output is a
    genuine absence, zero with output means the blob is there to be read.
    """
    try:
        # Pathspecs are cwd-relative, so this asks about THIS project's manifest
        # even when the project root sits below the worktree top.
        listed = git_exec.run(
            ["ls-tree", "--name-only", "HEAD", "--", MANIFEST_FILENAME],
            cwd=root,
            timeout=_GIT_TIMEOUT,
        )
        if listed.returncode != 0:
            return None  # no repository, no HEAD, or git could not answer
        if not (listed.stdout or "").strip():
            return 0, None  # HEAD was read, and it holds no manifest here
        # `./` is load-bearing: without it git resolves the path against the
        # TOP LEVEL of the worktree, not against cwd, and the project root is
        # under no obligation to be the top level (a package inside a monorepo
        # is the ordinary case). Bare `HEAD:<name>` reads a DIFFERENT project's
        # manifest when one sits at the top, and fails outright when none does.
        show = git_exec.run(["show", f"HEAD:./{MANIFEST_FILENAME}"], cwd=root, timeout=_GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None  # no git binary, or it hung past the bound
    if show.returncode != 0:
        return None  # listed in HEAD yet unreadable — an error, not an absence
    return _parse_manifest(show.stdout or "")


def _root_of(path: str, root: str | None) -> str:
    """The directory a journal read runs in: the caller's root, else the file's own."""
    return root or os.path.dirname(path) or "."


def _batch_blobs(raw: bytes) -> list[bytes]:
    """Blob contents out of `git cat-file --batch` output, in request order.

    Each answer is a header line then the object body then one LF. A header of
    ``<sha> <type> <size>`` is followed by exactly ``<size>`` bytes; ``<name>
    missing`` (the path is not in that commit — a deletion commit lists in
    rev-list too) and ``<name> ambiguous`` carry no body. A body is returned
    only for a ``blob``: the path naming a tree is skipped over, not read as a
    manifest. Sizes are BYTES, which is why the caller reads git in binary
    mode: a manifest with Cyrillic in it would split wrong on decoded text.

    Raises ``ValueError`` on a header that is neither shape, so a caller can
    file an unparseable stream under "unreadable" rather than under "empty".
    """
    blobs: list[bytes] = []
    pos = 0
    while pos < len(raw):
        nl = raw.find(b"\n", pos)
        if nl < 0:
            raise ValueError("cat-file --batch output ends mid-header")
        header = raw[pos:nl]
        parts = header.split()
        pos = nl + 1
        if len(parts) == 2:
            continue  # "<name> missing" / "<name> ambiguous": no body follows
        if len(parts) != 3:
            raise ValueError(f"unexpected cat-file header: {header!r}")
        size = int(parts[2])
        # A size is only a promise until the bytes are there. A negative one
        # walked `pos` backwards and, because a negative start clamps to the
        # beginning, re-read the first header forever — a hang no subprocess
        # timeout could reach, found by review. An oversized one sliced short
        # and fed a truncated blob to the parser as if it were whole.
        if size < 0 or pos + size + 1 > len(raw):
            raise ValueError(f"cat-file body of {size} bytes does not fit the stream")
        body, pos = raw[pos : pos + size], pos + size + 1
        if parts[1] == b"blob":
            blobs.append(body)
    return blobs


def journal_high_water(root: str) -> int | None:
    """Highest manifest-version the audit journal has EVER held, across every ref.

    §13.4.1 forbids REUSE, and a number is used the moment any commit carries
    it — on this branch, on another, in a commit later reverted. The tip of
    HEAD can sit below all of those. Measured on this repository: `main` has
    never carried the manifest, so a `--write` from `main` read a floor of 0
    and would have re-issued v1 over different content while commit 42a0232
    holds v1. Reading history only when HEAD carries nothing would not close
    that either: a branch cut at v1 carries v1 at its tip while v17 exists
    elsewhere, and would re-issue v2. So the floor is the maximum over every
    commit that ever touched the file, reachable from ANY ref.

    `--full-history` IS LOAD-BEARING. A path-limited `rev-list` simplifies
    history by default: a merge resolved by keeping one side is TREESAME to
    that parent, the walk follows only that parent, and the other side's
    commits drop out of the listing while staying reachable. Two branches
    that each ran `--write`, merged with `-s ours`, the losing branch deleted
    — the version issued on the losing side was reachable, unlisted, and
    re-issued (external review #38, reproduced: 2 of 4 commits listed, v3
    handed out twice). The flag turns simplification off; the process count
    does not change.

    Same three answers as :func:`journal_manifest`, for the same reason: ``None``
    when the journal cannot be read (not a repository, git could not answer, a
    stream that does not parse), ``0`` when it answered and never held a
    manifest here, ``N`` otherwise. A commit that DELETED the file lists in
    rev-list and reads back as ``missing`` — a fact about that commit, not a
    failure — and is skipped, so the mark survives a deletion.

    Cost, measured rather than assumed, on this repository (10 commits):
    `rev-list` 28 ms and `cat-file --batch` 27 ms — two processes whatever the
    length of the history, because cat-file streams every blob out of one
    invocation. The n+1 shape the task feared (one `show` per commit at ~25 ms
    each) was never needed. The PROCESS count is flat; the COST is not: every
    listed blob is parsed as YAML (~6.5 ms per KB), so end to end this read
    took 125–151 ms here and grows linearly with the number of manifest
    commits. A 500-commit journal would spend seconds of parsing per
    `--write`, once per session — accepted and stated, not hidden behind the
    process count (review #38).
    """
    try:
        # Pathspecs are cwd-relative, so this lists the commits that touched
        # THIS project's manifest, not a namesake at the worktree top.
        revs = git_exec.run(
            ["rev-list", "--all", "--full-history", "--", MANIFEST_FILENAME],
            cwd=root,
            timeout=_GIT_TIMEOUT,
        )
        if revs.returncode != 0:
            return None  # not a repository, or git could not answer
        shas = (revs.stdout or "").split()
        if not shas:
            return 0  # the journal answered: no commit ever carried one here
        # `./` for the same reason as in journal_manifest: an object name is
        # resolved against the top level unless anchored to cwd.
        wanted = "".join(f"{sha}:./{MANIFEST_FILENAME}\n" for sha in shas).encode("ascii")
        batch = git_exec.run(
            ["cat-file", "--batch"], cwd=root, timeout=_GIT_TIMEOUT, binary=True, input=wanted
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        # No git binary, a hang past the bound, or a rev-list line that is not
        # hex (git's output was decoded with errors="replace", so a damaged
        # stream reaches here as U+FFFD, which is not ASCII).
        return None
    if batch.returncode != 0:
        return None
    try:
        blobs = _batch_blobs(batch.stdout or b"")
    except ValueError:
        return None
    high = 0
    for blob in blobs:
        high = max(high, _parse_manifest(blob.decode("utf-8", errors="replace"))[0])
    return high


def chain_state(path: str, root: str | None = None) -> tuple[int, str | None]:
    """(version to issue, back-link to publish) from one pass over the journal.

    Two questions, two reads, one call. The PREDECESSOR is the journal's tip —
    the entry this branch's audit trail actually continues from. The FLOOR is
    the journal's whole history over every ref plus the working copy, because
    §13.4.1 forbids reuse of a number wherever it was issued. A branch that
    never carried the manifest therefore publishes no `replaces` (nothing here
    to supersede) and still does not re-issue v1.

    Each answer comes from exactly one read — a `--write` used to fetch the
    tip twice and could publish a link and a number from different journal
    states. The two reads are still two: a commit landing between the tip pair
    and the history pair is not excluded, only made unlikely by the ~100 ms
    window of a local CLI.

    UNREADABLE HISTORY IS REFUSED, NOT ROUNDED DOWN. The tip reader's `None`
    falls back to the working copy because "no repository here" is a state a
    project may legitimately be in. The history reader answering `None` while
    the tip answered is not that state: git is present and spoke, and then
    `rev-list` or `cat-file` failed. Folding that into a floor of 0 would
    re-issue exactly the number this function exists to protect, silently, on
    a transient failure — found by review. Raises :class:`ServiceError`, which
    the CLI prints and exits on; no manifest is written over a floor nobody
    could read. A repository without commits is not this case: its tip is
    unreadable (no HEAD) and its history answers 0 or the other refs' mark.
    """
    where = _root_of(path, root)
    journal = journal_manifest(where)
    history = journal_high_water(where)
    if journal is not None and history is None:
        raise ServiceError(
            f"the audit journal of {MANIFEST_FILENAME} could not be read past HEAD "
            "(git rev-list/cat-file failed); refusing to issue a manifest-version "
            "that may already exist in history"
        )
    disk = _existing_manifest(path)
    # The predecessor is the journal's entry; the working copy answers only when
    # the journal could not be read at all (None, never (0, None)).
    version, mid = journal if journal is not None else disk
    link = f"{mid}@v{version}" if version and mid else None
    floor = max(disk[0], journal[0] if journal else 0, history or 0)
    return floor + 1, link


def previous_link(path: str, root: str | None = None) -> str | None:
    """`<manifest-id>@v<version>` of the manifest a regeneration supersedes.

    Two ways of composing this link have already broken the §13.4.2 chain, and
    both are guarded here.

    1. TODAY's date plus the previous version number (`CFM-<today>-tausik@v<n-1>`)
       names a manifest only if the predecessor was written the same day. Seven
       regenerations happened to be; the first cross-day one broke the chain
       (review #208, record #24).
    2. The WORKING COPY's id, which is the predecessor only if it was committed.
       The counter advances on every `--write` while the journal records only
       commits, so versions v4, v5, v6, v8, v10 and v12 were issued on disk and
       never existed as audit records — 5 of the first 8 links resolved to
       nothing because of this, not because of the date.

    The journal's own last entry is the only link that resolves by construction.

    Convenience over :func:`chain_state` for a caller that wants only the link;
    a `--write` wants both and asks once.
    """
    return chain_state(path, root)[1]


def next_version(path: str, root: str | None = None) -> int:
    """The version a regeneration must carry: one past the highest EVER ISSUED.

    §13.4.1 immutability is about NON-REUSE, so the floor is the maximum over
    every place a version can have been seen. Reading only the working copy
    let a deleted file reset the counter to 1 and re-issue v1 over different
    content — the comment at the call site claimed "never reset the version"
    while the code did exactly that. Reading only the journal would re-issue a
    number an uncommitted `--write` already put on disk. Reading only the
    journal's TIP lowered the floor on any HEAD that carried less than the
    history did — `main` here, a branch cut before the artifact, a revert of
    the commit that added it — and re-issued v1 from `main`. The floor is now
    the working copy, the tip, and the whole history over every ref
    (:func:`journal_high_water`). A gap in the numbering is not a break: the
    clause forbids reuse, not sparseness.

    What remains outside: a commit that exists in NO ref — unreachable after a
    reset, a branch deleted before it was merged — is not in the audit
    journal by git's own definition, and a number issued only there is not
    one the journal holds. A branch deleted AFTER it was merged is inside:
    its commits stay reachable through the merge, and the history walk is
    run without simplification so that they are listed (review #38).

    Convenience over :func:`chain_state` for a caller that wants only the
    version; a `--write` wants both and asks once.
    """
    return chain_state(path, root)[0]


def cmd_renar(svc: ProjectService, args: Any) -> None:
    cmd = getattr(args, "renar_cmd", None) or "conformance"
    if cmd == "export":
        _cmd_renar_export(svc, args)
        return
    if cmd != "conformance":
        print(f"Unknown renar subcommand: {cmd!r}")
        return
    assessor = resolve_assessor(getattr(args, "assessor", None))
    date = utcnow_iso()[:10]
    write = getattr(args, "write", False)

    path = None
    manifest_version = 1
    link = None
    if write:
        from project_config import find_tausik_dir

        root = os.path.dirname(find_tausik_dir())
        path = os.path.join(root, MANIFEST_FILENAME)
        # §13.4.1 immutability: never reset and never reuse a version, and name
        # as predecessor the entry the audit journal actually holds. Both come
        # from ONE read of the journal, so they describe the same instant.
        manifest_version, link = chain_state(path, root)

    # `replaces` is passed IN, not patched onto the rendered manifest afterwards:
    # a second renderer is a second chance for the two to disagree.
    manifest, text = generate(svc.be._conn, assessor, date, manifest_version, link)

    if write and path:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)  # atomic — no partial-write corruption
        print(f"Wrote {path} (manifest-version {manifest_version})")

    excl = manifest.get("scope-exclusion")
    level = manifest["level"] or (
        f"(none — non-conformant by declaration, {excl['clause']})"
        if excl
        else "(none — pre-adoption)"
    )
    print(text)
    print(f"# inferred level: {level} | pre_adoption: {manifest['pre-adoption']}")
    if manifest["assessment-evidence"]["blocked-at"]:
        print(f"# blocked at: {manifest['assessment-evidence']['blocked-at']}")


def _resolve_out_dir(explicit: str | None) -> str:
    """Resolve + safety-check the export target dir.

    Default is <project_root>/renar/. An explicit --out is accepted only if it
    stays strictly inside the project root (assert_export_target) — the write
    path reconciles *.md deletions and must never escape the repo.
    """
    from project_config import find_tausik_dir
    from renar_export import assert_export_target

    project_root = os.path.dirname(find_tausik_dir())
    target = (
        explicit.strip() if (explicit and explicit.strip()) else os.path.join(project_root, "renar")
    )
    return assert_export_target(target, project_root)


def _cmd_renar_export(svc: ProjectService, args: Any) -> None:
    """`tausik renar export [--out renar/] [--check]` — sqlite → derived tree.

    --check exits 1 on drift (stale tree) like `doc constants --check`; the
    default write reconciles deletions and reports written/deleted counts.
    """
    from renar_export import build_tree, check_tree, write_tree

    try:
        out = _resolve_out_dir(getattr(args, "out", None))
    except ValueError as e:
        print(f"renar export: {e}")
        raise SystemExit(1) from e

    tree = build_tree(svc)

    try:
        if getattr(args, "check", False):
            drift = check_tree(out, tree)
            if drift:
                print(f"Drift: {out} does not match live DB state ({len(drift)} issue(s)):")
                for msg in drift:
                    print(f"  {msg}")
                print("  Run: tausik renar export")
                raise SystemExit(1)
            print(f"OK — {out} matches the RENAR artifact store ({len(tree)} file(s)).")
            return

        counts = write_tree(out, tree)
    except OSError as e:
        print(f"renar export failed: {e}")
        raise SystemExit(1) from e

    print(
        f"Exported {counts['written']} file(s) to {out}"
        + (f" (removed {counts['deleted']} stale)" if counts["deleted"] else "")
    )


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
