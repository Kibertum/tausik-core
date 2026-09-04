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
from tausik_utils import utcnow_iso

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


def chain_state(path: str, root: str | None = None) -> tuple[int, str | None]:
    """(version to issue, back-link to publish) from ONE read of the journal.

    The two answers describe the same instant, so they are derived from the same
    pair of reads rather than each fetching its own. Two independent fetches
    also meant four git subprocesses per `--write`, and a HEAD that moved
    between them would have produced a version number and a `replaces` link
    computed from different journal states.
    """
    journal = journal_manifest(_root_of(path, root))
    disk = _existing_manifest(path)
    # The predecessor is the journal's entry; the working copy answers only when
    # the journal could not be read at all (None, never (0, None)).
    version, mid = journal if journal is not None else disk
    link = f"{mid}@v{version}" if version and mid else None
    return max(disk[0], journal[0] if journal else 0) + 1, link


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
    """The version a regeneration must carry: one past the highest VISIBLE here.

    §13.4.1 immutability is about NON-REUSE, so the floor is the maximum of the
    two places a version can be seen. Reading only the working copy let a
    deleted file reset the counter to 1 and re-issue v1 over different content
    — the comment at the call site claimed "never reset the version" while the
    code did exactly that. Reading only the journal would re-issue a number an
    uncommitted `--write` already put on disk. A gap in the numbering is not a
    break: the clause forbids reuse, not sparseness.

    KNOWN AND UNCLOSED, deliberately not overstated here: "visible" is the
    working copy plus the journal's TIP, not its whole history. A HEAD that
    does not carry the manifest while an earlier commit does — a branch older
    than the artifact, a revert of the commit that added it — lowers the floor
    and can re-issue a number the history already holds. Measured on this
    repository: `main` carries no manifest, so a `--write` from `main` today
    issues v1 a second time. Tracked as its own task; the fix is a high-water
    mark over the file's history, which is a different read from this one.

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
