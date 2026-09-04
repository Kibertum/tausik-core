r"""One notion of "this path is an example, not a claim", shared by two detectors.

WHY ONE MODULE. `memory lint` (stale_file) and `audit evidence` are independent
detectors that made the SAME mistake for the same reason: neither told a
citation from a mention. Measured in session #209 on this corpus:

* `audit evidence` — 25 refs in NEVER_EXISTED, of which 13 are conventional
  examples quoted by tasks whose very SUBJECT is fake or rotted citations
  (`tests/test_does_not_exist.py`, `tests/test_foo.py::test_bar`,
  `tests/../scripts/prod.py`). Three are genuine misses. The headline number
  therefore over-reported real rot by a factor of two, next to a ROTTED bucket
  of 22 that a reader is being taught to skim past.
* `memory lint` — 7 stale_file findings, of which 5 are not stale at all.

Fixing that in each detector separately is how two lists of placeholder names
drift apart, so the notion lives here and both import it.

WHAT COUNTS AS ILLUSTRATIVE. Three mechanical rules, each chosen because it was
measured on the corpus, not because it sounded plausible:

1. A PLACEHOLDER BASENAME — `foo.py`, `x.py`, `tests/test_bar.py`. The stems are
   the conventional example names, kept deliberately narrow so a genuine
   one-word module is not swallowed.
2. A PLACEHOLDER MEMBER — `tests/test_real.py::test_a`. This carries its own
   rule so that a real-looking FILE name quoted with an example member is
   caught without widening the file-name list, which would silence a genuine
   `test_real.py` if one were ever written.
3. A RUNTIME-RELATIVE PATH — a leading `./` or any `..` segment
   (`./probe.sh`, `tests/../scripts/prod.py`). Such a token is relative to
   whatever directory a command happened to run in, so it is not a claim about
   a file at a repo-relative location, which is the only claim these detectors
   are entitled to check.

WHAT DELIBERATELY DOES NOT COUNT. A path that a memory mentions in order to say
it is ABSENT (memory #322 names `tausik/tausik.db` while explaining that the
database is not there) still reads as a stale reference. Recognising that needs
the sentence's intent, and guessing intent is how a detector becomes a silencer.
It stays reported, and that is the honest answer until someone measures a rule
for it.
"""

from __future__ import annotations

import re

#: Conventional example stems. `does_not_exist` is here because the corpus put
#: it in NEVER_EXISTED twice; the rest were already in use by `memory lint`
#: before this module existed. Nothing is added on a hunch: an unmeasured stem
#: silences a real file the day someone writes one with that name.
_PLACEHOLDER_BASENAME_RE = re.compile(
    r"^(?:[a-z]|foo|bar|baz|qux"
    r"|test_(?:[a-z]|foo|bar|baz|file|name|thing|func|module|does_not_exist))"
    r"\.[a-z0-9]{1,6}$",
    re.IGNORECASE,
)

#: Example member names. Narrow on purpose — the file name carries most of the
#: signal, and a single-letter or foo/bar member is the rest of it.
_PLACEHOLDER_MEMBER_RE = re.compile(
    r"^(?:test_)?(?:[a-z]|foo|bar|baz|qux)$",
    re.IGNORECASE,
)


def split_ref(ref: str) -> tuple[str, str]:
    """Split ``path::member`` into its two halves; member is ``""`` when absent."""
    path, _, member = (ref or "").partition("::")
    return path, member


def is_placeholder_basename(path: str) -> bool:
    """True for a conventional example file name (``foo.py``, ``tests/test_x.py``)."""
    if not path:
        return False
    return bool(_PLACEHOLDER_BASENAME_RE.match(path.replace("\\", "/").rsplit("/", 1)[-1]))


def is_placeholder_member(member: str) -> bool:
    """True for a conventional example member name (``test_a``, ``test_bar``).

    The LAST segment is tested, so ``TestX::test_a`` is read by its member.
    """
    if not member:
        return False
    return bool(_PLACEHOLDER_MEMBER_RE.match(member.rsplit("::", 1)[-1]))


def is_runtime_relative(path: str) -> bool:
    """True for a path anchored to a working directory rather than the repo.

    ``./probe.sh`` and ``tests/../scripts/prod.py`` both name a file only in
    relation to wherever a command ran. Neither is a claim that something sits
    at that repo-relative location, so neither can be stale in the sense these
    detectors report.
    """
    if not path:
        return False
    segments = path.replace("\\", "/").split("/")
    return segments[0] == "." or ".." in segments


def is_illustrative(ref: str) -> bool:
    """True when ``ref`` is an example being quoted, not a file being cited."""
    path, member = split_ref(ref)
    return (
        is_runtime_relative(path) or is_placeholder_basename(path) or is_placeholder_member(member)
    )


def why_illustrative(ref: str) -> str | None:
    """The rule that fired, for a report that must not be a black box.

    A reader who cannot see WHY a citation was set aside has no way to tell a
    correct exclusion from a detector quietly going blind.
    """
    path, member = split_ref(ref)
    if is_runtime_relative(path):
        return "path is relative to a working directory, not to the repository"
    if is_placeholder_basename(path):
        return "conventional example file name"
    if is_placeholder_member(member):
        return "conventional example member name"
    return None
