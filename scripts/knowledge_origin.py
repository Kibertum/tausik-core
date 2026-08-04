"""Attribution for shared-store rows that survives being read from another project.

THE PROBLEM THIS SOLVES. The shared store is one file under one OS account, and
`origin_project` used to hold the ABSOLUTE root of the project each row came
from. On a machine where one person works for several clients out of one home
directory — the path of this very repository names a client — that made every
client's directory name readable from every other project, with no export and
no privilege: open the file, `SELECT origin_project`, read the list. The trust
boundary in consulting is the CLIENT, not the OS account, and an absolute path
crosses it by construction.

WHY NOT JUST SHORTEN ON DISPLAY. The read path already showed the last
component only. That fixes what a command PRINTS and nothing else: the value at
rest still named the client, so `sqlite3 knowledge.db`, the logical export, and
any backup of it all carried the disclosure. A privacy property that holds only
while everyone uses the intended reader is not a property.

WHY NOT A PSEUDONYM PLUS A MAPPING TABLE. That was the obvious alternative and
it fails for a stated reason: the table has to live somewhere, and wherever it
lives it holds exactly the string that was supposed to stop existing. The
fingerprint here is COMPUTED, not assigned — a project derives its own label
from its own root whenever it needs to, so "is this row mine?" is answerable
with no dictionary anywhere. Nothing needs to store the inverse because nothing
needs the inverse.

WHY THE BASENAME STAYS IN THE CLEAR. Attribution has to be legible or it is not
attribution; a row labelled `a3f91c22` tells a reader nothing they can act on.
The basename is the part a person recognises (`core`, `server`), and it was
already the only part the display showed. What the label adds is the eight hex
digits that make two projects called `core` distinguishable — the reason the
absolute root was stored in the first place. So the label keeps the property the
path was there for and drops the part that was never needed for it.

WHY EIGHT DIGITS. Enough that two roots on one machine colliding is not
something to design around; short enough to read aloud and to fit in a list
without wrapping. This is a disambiguator among a person's own projects, not a
content-addressed identity, and it is not relied on to be unforgeable.
"""

from __future__ import annotations

import hashlib
import os
import re

# `name@deadbeef`. The name half excludes separators on purpose: that is what
# tells a label apart from a path, and it is the whole test the migration uses
# to decide whether a stored value has already been dealt with.
_LABEL_RE = re.compile(r"^[^/\\]+@[0-9a-f]{8}$")

# What the migration accepts as "this is a project root someone stored", spelled
# so it means the same thing on every platform: a leading separator, or a
# Windows drive, or a UNC share. `os.path.isabs` cannot be used — on Linux it
# calls `D:\Work\clients\acme\repo` relative, and the whole point is to redact
# rows written on Windows no matter where they are read.
#
# The narrowness is the feature. `origin_project` is free text by design, so a
# value that merely CONTAINS a separator — `team/backend`, a hand-set tag — is
# not a path, and fingerprinting it would destroy a legitimate value
# irreversibly to fix a disclosure that was never there.
_ABSOLUTE_RE = re.compile(r"^(?:[/\\]|[A-Za-z]:[/\\])")

FINGERPRINT_LEN = 8


def _canonical(abs_root: str, *, resolve: bool) -> str:
    """One spelling of a root, so the same project always fingerprints the same.

    `resolve` decides whether the FILESYSTEM is consulted, and the two callers
    want opposite answers.

    WRITING (`resolve=True`). The root is this project's own, it exists, and it
    is local — `find_tausik_dir` just found it. `realpath` there is cheap and
    buys the spellings case folding cannot cover: an 8.3 short name
    (`C:\\PROGRA~1\\proj`), a junction, a symlink.

    MIGRATING (`resolve=False`). The input is a STRING someone else stored,
    possibly years ago, possibly naming a share that no longer answers. This
    runs on every open of the shared store, in every project on the machine, and
    `realpath` on an unreachable UNC or a disconnected mapped drive blocks for
    the OS's full network timeout — freezing not one command but all of them,
    uninterruptibly. A label computed lexically is worth incomparably more than
    a label computed correctly after two minutes of nothing.

    Case folding is `lower()` rather than `os.path.normcase` DELIBERATELY. A
    stored `D:\\Work\\Core` must fingerprint the same whether the process
    reading it runs on Windows or on Linux — the store is explicitly shared
    across a machine, WSL included, and `normcase` is a no-op on POSIX, so it
    would hand the same row two identities depending on who opened it first. The
    price is that two roots on a case-sensitive filesystem differing only in
    case collapse to one label; that is an attribution nuisance and it is the
    smaller of the two.

    KNOWN LIMITS, stated rather than implied: a UNC path and a drive letter
    mapped to the same share fingerprint differently, and so can a legacy row
    whose root is a symlink — it is migrated lexically while a fresh write from
    the same project resolves. Both show one project under two origins. Neither
    discloses anything.
    """
    path = os.path.realpath(abs_root) if resolve else abs_root
    return path.replace("\\", "/").rstrip("/").lower()


def origin_fingerprint(abs_root: str, *, resolve: bool = True) -> str:
    """Eight hex digits derived from the canonical root. Not reversible."""
    canonical = _canonical(abs_root, resolve=resolve)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:FINGERPRINT_LEN]


def origin_label_for(abs_root: str, *, resolve: bool = True) -> str:
    """The value a shared row stores instead of a path: `basename@fingerprint`.

    A root with no basename — a drive root, or a path ending in a separator that
    survived normalisation — would otherwise produce `@abcd1234`, which reads as
    a bug. `project` is used instead: uninformative, but honest and well-formed,
    and the fingerprint still distinguishes it from any other such root.
    """
    basename = os.path.basename(_canonical(abs_root, resolve=resolve)) or "project"
    return f"{basename}@{origin_fingerprint(abs_root, resolve=resolve)}"


def is_origin_label(value: str | None) -> bool:
    """True when a stored value is already in label form and must be left alone."""
    if not value:
        return False
    return _LABEL_RE.match(value) is not None


def redacted_origin(value: str | None) -> str | None:
    """A stored `origin_project` in label form, or None when it must not be touched.

    Returning None rather than the input is deliberate: the migration writes only
    what this function turns into a string, so "nothing to do" cannot be confused
    with "rewrite it to the same value" and the UPDATE count stays an honest
    measure of how much was actually disclosed.

    Empty and NULL are left alone because they disclose nothing, and a value that
    is neither an ABSOLUTE path nor a label — a hand-written tag, a fixture,
    `brain:<hash>` from the wiki mirror — is left alone because inventing a
    fingerprint for it would fabricate attribution rather than remove
    disclosure, and it would do so irreversibly.
    """
    if not value or is_origin_label(value):
        return None
    if not _ABSOLUTE_RE.match(value):
        return None
    # `resolve=False`: never touch the filesystem for a value someone else
    # stored. See `_canonical` — this runs on every open, and one unreachable
    # share would hang every command on the machine.
    return origin_label_for(value, resolve=False)


def relative_source_file(source_file: str | None, project_root: str) -> str | None:
    """A snippet's `source_file` with the machine's directory layout taken out.

    Inside the project, the answer is the path relative to its root — which is
    how the file is named in the repository anyway, so nothing is lost. Outside
    it, the answer is the basename: a `../../` chain climbing out of the project
    would put the very directory names being removed back into the value, only
    spelled relatively.

    Already-relative values are returned unchanged. They came from a project
    store that had already normalised them, and re-resolving them against a root
    they may not belong to would be a guess.

    Absoluteness is decided by `_ABSOLUTE_RE`, the predicate this module already
    defines a hundred lines above with the reason spelled out — and this function
    was the one place that did not use it. It asked `os.path.isabs`, and that
    answer moves: Python 3.13 changed `ntpath.isabs` so a path with one leading
    separator and no drive letter (`\\work\\clients\\acme\\repo\\a.py`) is no
    longer absolute on Windows. The function then returned such a path
    UNCHANGED — leaving the machine's directory layout in the very column this
    redaction exists to clear, on one platform, from one minor release onward,
    without a word. What is absolute is a property of how the path is SPELLED;
    asking the interpreter what it thinks today makes the answer a moving target.
    """
    if not source_file:
        return source_file
    if not _ABSOLUTE_RE.match(source_file):
        return source_file
    root = os.path.abspath(project_root)
    resolved = os.path.abspath(source_file)
    if os.path.normcase(resolved).startswith(os.path.normcase(root) + os.sep):
        return os.path.relpath(resolved, root).replace("\\", "/")
    return os.path.basename(resolved)
