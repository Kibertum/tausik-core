"""Where the shared store is allowed to live, and what to do when it isn't.

WHAT RESTS ON THIS. The write path deliberately does not scrub, and the reason
given is that the store is a file in the user's own home which never leaves the
machine. That premise is not a fact about the code — it is a fact about a
DIRECTORY, and `TAUSIK_HOME` lets anything name that directory. Point it inside
a work tree and the accumulated knowledge of every project this person works on
leaves with the first `git add -A`. Point it at OneDrive or Dropbox — which are
physically inside the home directory, so "it is in my home" stays true while
the conclusion drawn from it stops being — and it leaves over the network.

Neither needs malice to happen: a wrong variable in a CI config, an MCP wrapper
launched with someone else's environment, a copied `.env`.

WHY THE ANSWER IS NOT SIMPLY "REFUSE". Refusing everything inside a git tree
would reject the DEFAULT location for everyone who keeps their home directory
in a dotfiles repository, which is a common and entirely sensible practice. A
guard whose first act is a false alarm on an ordinary setup gets disabled, and
then it guards nothing. So the response is split by whether we can remove the
danger ourselves:

  - A network path or a cloud-sync directory: REFUSE. Nothing written locally
    changes what a sync client does, so there is no safe way to continue.
  - A git work tree: NEUTRALISE. A `.gitignore` in the store's own directory
    makes `git add -A` skip it, the same trick the project's own `.tausik/`
    uses. No refusal needed, because the danger is gone rather than tolerated.
  - A store git is ALREADY TRACKING: REFUSE. `.gitignore` does not untrack what
    is already indexed, so there the disclosure has happened, and continuing
    quietly would add to it.

THE TWO HALVES ARE SPLIT ON PURPOSE, and it is not tidiness. What a PATH says —
its spelling, its volume, the sync directory it sits under — cannot change while
a process runs, so it is validated once and cached. What GIT says can change
under a running process: a directory becomes a repository, a file gets added.
A long-lived MCP server is exactly the case the paragraph above names, and a
cached "this was not a repository half an hour ago" would be the guard switching
itself off. So `protect_home_in_git` re-decides every time, and it is called
only from the code that is about to open the store — never from a read that
merely asks where the store would be.

That split is also what keeps it cheap. Finding the work tree walks up looking
for `.git`, which costs a few `stat` calls; `git` itself is only run once a work
tree has actually been found, which for most people is never.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

from tausik_utils import ServiceError

# Matched as whole PATH COMPONENTS, case-insensitively, plus the prefix forms
# below — never as substrings. `~/notes/my-dropbox-notes` is a directory someone
# named after a tool, not a directory the tool syncs, and refusing it would be
# exactly the false alarm this module exists to avoid.
#
# Bare `box` and `mega` are deliberately ABSENT despite being real products:
# they are ordinary English words, and `~/archive/mega/` is a likelier thing to
# exist than a sync root spelled that way. Their real sync roots carry the
# suffixed names below.
_CLOUD_SYNC_DIRS = frozenset(
    {
        "dropbox",
        "google drive",
        "googledrive",
        "google drive file stream",
        "my drive",
        "icloud drive",
        "mobile documents",  # macOS iCloud: `~/Library/Mobile Documents/`
        "cloudstorage",  # macOS 12+: `~/Library/CloudStorage/<provider>-<account>`
        "onedrive",
        "yandexdisk",
        "yandex.disk",
        "яндекс.диск",
        "nextcloud",
        "owncloud",
        "pcloud",
        "pclouddrive",
        "megasync",
        "sync.com",
        "creative cloud files",
        "box sync",
    }
)

# `OneDrive - Acme Corp` is the default folder name on essentially every managed
# Windows machine, so matching only the bare `onedrive` component misses all of
# them. The separator is spelled out — space, hyphen, space — rather than a bare
# `onedrive` prefix, because a bare prefix also swallows `onedrive-backup-
# scripts`, an ordinary directory someone named after the thing it backs up.
# Refusing that would be exactly the false alarm this module exists to avoid.
#
# The macOS spellings (`OneDrive-AcmeCorp`, `GoogleDrive-someone@example.com`)
# need no entry here: they live under `~/Library/CloudStorage/`, and the
# `cloudstorage` component above catches every provider under it at once.
_CLOUD_SYNC_PREFIXES = ("onedrive - ",)

# Windows `GetDriveType` — a mapped network drive is a network path wearing a
# drive letter, which is how a corporate roaming home directory usually looks.
_DRIVE_REMOTE = 4

# Filesystems that are somebody else's disk. Consulted on Linux via /proc/mounts.
_NETWORK_FSTYPES = frozenset(
    {"nfs", "nfs4", "cifs", "smbfs", "smb3", "afs", "afpfs", "fuse.sshfs", "9p", "ncpfs"}
)

_GITIGNORE_BODY = (
    "# Written by TAUSIK. The shared knowledge store accumulates what was\n"
    "# learned across every project on this machine and is stored WITHOUT\n"
    "# redaction, on the argument that it never leaves the machine. This\n"
    "# directory sits inside a git work tree, so without this file one\n"
    "# `git add -A` would end that argument. Ignoring everything, including\n"
    "# this file, is deliberate.\n"
    "*\n"
)

# resolved home -> None. Only the PATH-shaped verdict is cached; see the module
# docstring for why the git verdict deliberately is not.
_checked: dict[str, None] = {}
_lock = threading.Lock()


def _components(path: str) -> list[str]:
    return [p for p in path.replace("\\", "/").lower().split("/") if p]


def _network_refusal(path: str, why: str) -> str:
    return (
        f"Refusing the shared knowledge store at {path}: {why}. The store is kept "
        "WITHOUT redaction because it does not leave this machine, and a network "
        "location ends that. Point TAUSIK_HOME at a local directory."
    )


def _is_unc(path: str) -> bool:
    return path.startswith("\\\\") or path.startswith("//")


def _is_network_volume(path: str) -> bool:
    """Whether the VOLUME under `path` is remote. Best effort, per platform.

    UNC syntax is the obvious case and is handled by the caller. This is the
    unobvious one: `Z:\\` handed out by a logon script, or `/mnt/nas` mounted
    from fstab. Both are "in my home directory" by every name-based test and
    are somebody else's disk in fact.

    Unknown means False. A guard that refused whatever it could not classify
    would refuse ordinary local disks on any platform whose plumbing is not
    covered here — macOS `/Volumes` among them, which is where its LOCAL
    external drives appear too. That is a real gap and it is named rather than
    papered over: on macOS a network mount is not detected.
    """
    if sys.platform == "win32":
        drive = os.path.splitdrive(os.path.abspath(path))[0]
        if not drive:
            return False
        try:
            import ctypes

            kind = ctypes.windll.kernel32.GetDriveTypeW(f"{drive}\\")  # type: ignore[attr-defined]
            return bool(kind == _DRIVE_REMOTE)
        except (AttributeError, OSError, ValueError):  # pragma: no cover
            return False
    try:
        with open("/proc/mounts", encoding="utf-8") as fh:
            mounts = [line.split() for line in fh]
    except OSError:
        return False
    target = os.path.abspath(path)
    best_len, best_type = -1, ""
    for fields in mounts:
        if len(fields) < 3:
            continue
        point, fstype = fields[1], fields[2]
        if (target == point or target.startswith(point.rstrip("/") + "/")) and len(
            point
        ) > best_len:
            best_len, best_type = len(point), fstype
    return best_type in _NETWORK_FSTYPES


def _cloud_component(path: str) -> str | None:
    for component in _components(path):
        if component in _CLOUD_SYNC_DIRS:
            return component
        if component.startswith(_CLOUD_SYNC_PREFIXES):
            return component
    return None


def _nearest_existing_dir(path: str) -> str | None:
    probe = path
    while not os.path.isdir(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent
    return probe


def find_work_tree(path: str) -> str | None:
    """The git work tree containing `path`, by walking up for `.git`. Or None.

    Filesystem rather than `git rev-parse`, and that is the deliberate choice:
    this runs on every open of the store, whereas a subprocess costs more than
    everything else on that path put together. It does not know about `GIT_DIR`
    or `core.worktree`; git is asked the questions only git can answer, and only
    once this has found something, which for most people is never.
    """
    probe = _nearest_existing_dir(path)
    while probe:
        if os.path.exists(os.path.join(probe, ".git")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent
    return None


def _git(work_tree: str, *args: str) -> subprocess.CompletedProcess | None:
    """Run git, or None when it could not be run at all."""
    try:
        return subprocess.run(
            ["git", "-C", work_tree, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            # This module is reachable from the MCP server, where a child that
            # decides to read stdin has nothing to read and no terminal to say
            # so — it simply hangs, and takes the request with it.
            stdin=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _is_tracked(work_tree: str, db_path: str) -> bool:
    """True only when git POSITIVELY says the store file is already indexed.

    Unanswerable without git, and it does not pretend otherwise: with no git to
    ask, this reports False and the store is protected going forward rather than
    refused. A refusal resting on an unanswerable question is a guess wearing a
    refusal's clothes, and the ignore rule still covers everything not indexed.
    """
    out = _git(work_tree, "ls-files", "--error-unmatch", db_path)
    return out is not None and out.returncode == 0


def _is_ignored(work_tree: str, db_path: str) -> bool | None:
    """Whether git would ignore the store. None when git could not be asked."""
    out = _git(work_tree, "check-ignore", "-q", db_path)
    if out is None:
        return None
    # 0 = ignored, 1 = not ignored, anything else = git could not decide.
    if out.returncode in (0, 1):
        return out.returncode == 0
    return None


def _ignore_rule_present(home: str) -> bool:
    """The fallback for "is it ignored" when git cannot be asked.

    Only recognises the rule this module writes. A narrower answer than git's,
    which is the right direction to be wrong in: an unrecognised file leads to
    the rule being appended, and an ignore rule appended twice is harmless.
    """
    target = os.path.join(home, ".gitignore")
    try:
        with open(target, encoding="utf-8") as fh:
            return any(line.strip() == "*" for line in fh)
    except OSError:
        return False


def assert_safe_knowledge_home(home: str, db_filename: str) -> str:
    """Validate the store's directory by its PATH. Returns the resolved path.

    Path-shaped facts only — see the module docstring for why the git ones are
    decided elsewhere. Free of side effects, because this is reached from read
    paths too, and the store's laziness contract is that someone who never asked
    for a shared store does not acquire one by running `status`.

    Resolution comes first and is not cosmetic: a junction named
    `~/.tausik-knowledge` pointing into `~/Dropbox` passes every name-based
    check while being exactly the case being guarded against.
    """
    if not home or not home.strip():
        raise ServiceError(
            "TAUSIK_HOME is set but empty. Refusing to guess — an empty value would "
            "resolve to the current directory, which changes with every command and "
            "is frequently inside a project. Unset it, or give a real directory."
        )

    # Checked on the RAW value, before `abspath` touches it. UNC is a SPELLING,
    # and a spelling belongs to the string rather than to the OS reading it —
    # but `abspath` destroys it off Windows: on Linux a backslash is an ordinary
    # character, so `\\server\share\kn` came back as
    # `<cwd>/\\server\share\kn`, sailed past the check below, and the guard went
    # on to create a directory with that literal name. The one refusal the whole
    # no-redaction argument rests on was Windows-only, and its test said so only
    # because it had never run anywhere else.
    raw = home.strip()
    if _is_unc(raw):
        raise ServiceError(_network_refusal(raw, "that is a UNC network path"))

    expanded = os.path.abspath(os.path.expanduser(home))
    # Checked BEFORE `realpath`, not only after. Resolving a UNC path reaches for
    # the network, and an unreachable share blocks for as long as the OS is
    # willing to wait — on a path that is going to be refused anyway.
    if _is_unc(expanded):
        raise ServiceError(_network_refusal(expanded, "that is a UNC network path"))

    resolved = os.path.realpath(expanded)
    if resolved in _checked:
        return resolved

    if _is_unc(resolved):
        raise ServiceError(_network_refusal(resolved, "it resolves to a UNC network path"))
    if _is_network_volume(resolved):
        raise ServiceError(
            _network_refusal(resolved, "it is on a mapped or mounted network volume")
        )

    cloud = _cloud_component(resolved)
    if cloud:
        raise ServiceError(
            f"Refusing the shared knowledge store at {resolved}: {cloud!r} is a "
            "cloud-sync directory. The store holds knowledge from every project on "
            "this machine and is kept WITHOUT redaction because it stays here — "
            "syncing it to a provider ends that argument. Point TAUSIK_HOME at a "
            "directory outside the synced tree."
        )

    with _lock:
        _checked[resolved] = None
    return resolved


def protect_home_in_git(home: str, db_filename: str) -> None:
    """Keep the store out of git, or refuse when it is already in. Re-decided every call.

    Called by the code that is about to open the store, never by a path that
    only asks where the store would be — writing a file is a side effect, and
    the read path must not have one.

    An existing `.gitignore` is not taken as proof of anything. A store
    directory can easily have picked one up from scaffolding or an editor, and
    `*.log` in it protects nothing; treating its mere presence as "already
    handled" is how the guard silently does nothing in the one case it exists
    for. So the question asked is whether GIT ignores the store — and when the
    answer is no, the rule is appended rather than the file replaced, because
    the other rules in it are somebody's and not ours to drop.
    """
    work_tree = find_work_tree(home)
    if work_tree is None:
        return

    db_path = os.path.join(home, db_filename)
    if _is_tracked(work_tree, db_path):
        raise ServiceError(
            f"Refusing the shared knowledge store at {db_path}: git is ALREADY "
            f"TRACKING it in the work tree at {work_tree}. Adding a .gitignore does "
            "not untrack what is already indexed, so this store is being committed. "
            "Untrack it with git's cached-removal option, and move TAUSIK_HOME "
            "outside the repository."
        )

    ignored = _is_ignored(work_tree, db_path)
    if ignored is None:
        ignored = _ignore_rule_present(home)
    if ignored:
        return

    target = os.path.join(home, ".gitignore")
    try:
        existing = ""
        if os.path.exists(target):
            with open(target, encoding="utf-8") as fh:
                existing = fh.read()
            if existing and not existing.endswith("\n"):
                existing += "\n"
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(existing + _GITIGNORE_BODY)
    except OSError:
        # A read-only or otherwise hostile directory. The store's own open fails
        # moments later for the same reason, with a better message than this.
        return


def reset_cache() -> None:
    """Forget what has been validated. For tests, which move the home around."""
    with _lock:
        _checked.clear()
