"""The one place shared-store content passes on its way off this machine.

WHY ONE PLACE. Until decision #358 the framework decided "may this leave?" in
four spots — a classifier at `decide`, a second run of it in the publish flow,
`scrub_inputs` in the MCP writer and a database-ownership guard — each with its
own idea of the answer, and a leak that slipped one of them slipped the rest.
The Notion transport took all four with it. What remains is `tausik knowledge
export`, which checked the SHAPE of a destination and nothing about the
content: a backup meant to travel carried absolute paths, e-mails and client
names verbatim, because the only argument for storing them unredacted was "it
never leaves the machine" and a backup is the act of leaving.

Two questions, both answered here and nowhere else:

* `assert_local_destination` — may bytes go THERE? Refused by shape (URL
  scheme, UNC path), because a remote that is down today is still a remote.
* `redact` — what may the bytes SAY? Built on the four detectors of
  `brain_scrubbing` (absolute paths, e-mails, private URLs, project names), but
  it REPLACES a match with a typed placeholder instead of refusing: a scrubber
  that refuses on the first absolute path never produces a backup, and a backup
  that quietly does not happen is discovered at the one moment it was needed.

A local backup is NOT redacted by default. It exists to restore what it saved,
on the same machine, and redacting it would trade that for privacy against
oneself; `--redacted` is the form meant to travel, and its manifest says so.

`tests/test_publication_boundary.py` holds the property (convention #354):
every module that reads the shared store and writes files or the network
imports this one, allowlist exceptions named with their reason.
"""

from __future__ import annotations

import re
from typing import Iterable, NamedTuple
from urllib.parse import urlparse

# The detectors are the scrubber's own; a second copy of a regex is a second
# answer to "what is a private path", and the two would drift.
from brain_scrubbing import _EMAIL, _POSIX_PATH, _URL, _WINDOWS_PATH, _compile_patterns
from tausik_utils import ServiceError

_NETWORK_SCHEMES = frozenset(
    {
        "s3",
        "gs",
        "az",
        "azure",
        "http",
        "https",
        "ftp",
        "ftps",
        "sftp",
        "scp",
        "ssh",
        "smb",
        "webdav",
    }
)

PLACEHOLDERS = {
    "path": "[REDACTED:path]",
    "email": "[REDACTED:email]",
    "url": "[REDACTED:url]",
    "project": "[REDACTED:project]",
}


class Redaction(NamedTuple):
    text: str
    counts: dict[str, int]  # detector -> replacements made

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def assert_local_destination(dest: str) -> str:
    """Return the absolute path, or refuse a destination that leaves this machine.

    Refusal is by SHAPE, not by reachability: a URL scheme, or a UNC path, means
    the bytes go somewhere this machine does not solely control. Testing whether
    a remote answers would be the wrong check — a remote that happens to be down
    today is still a remote.

    Deliberately permissive about ordinary paths, including ones on other drives
    or on a mounted volume: a mounted network share is indistinguishable from a
    local disk at this level, and refusing every mount would refuse the external
    drive that is the most likely backup target there is. The line drawn here is
    the one that can be drawn honestly; the rest is documented, not pretended.
    """
    import os

    if not dest or not dest.strip():
        raise ServiceError("Backup destination is empty. Give a local directory to write into.")

    raw = dest.strip()
    if raw.startswith("\\\\") or raw.startswith("//"):
        raise ServiceError(
            f"Refusing the UNC destination {raw!r}. The shared knowledge database is stored "
            "WITHOUT redaction — the memories, decisions and code snippets in it are free "
            "text and can name a client outright — so backups must stay on this machine. "
            "Give a local directory, or export with --redacted before moving the files."
        )

    scheme = urlparse(raw).scheme.lower()
    if len(scheme) > 1 and scheme in _NETWORK_SCHEMES:
        raise ServiceError(
            f"Refusing the remote destination {raw!r} (scheme {scheme!r}). The shared knowledge "
            "database is stored WITHOUT redaction — the memories, decisions and code snippets "
            "in it are free text and can name a client outright — so backups must stay on this "
            "machine. Export with --redacted into a local directory, then move the files."
        )
    if len(scheme) > 1:
        raise ServiceError(
            f"Refusing the destination {raw!r}: {scheme!r} is not a local path. "
            "Give a local directory."
        )
    return os.path.abspath(os.path.expanduser(raw))


def _replace_all(text: str, pattern: re.Pattern[str], placeholder: str) -> tuple[str, int]:
    return pattern.subn(placeholder, text)


def _replace_private_urls(text: str, patterns: list[re.Pattern[str]]) -> tuple[str, int]:
    if not patterns:
        return text, 0
    count = 0

    def _sub(m: re.Match[str]) -> str:
        nonlocal count
        url = m.group(0)
        if any(p.search(url) for p in patterns):
            count += 1
            return PLACEHOLDERS["url"]
        return url

    return _URL.sub(_sub, text), count


def _replace_project_names(text: str, names: Iterable[str]) -> tuple[str, int]:
    count = 0
    for name in names:
        if not isinstance(name, str) or not name.strip():
            continue
        text, n = re.subn(
            re.escape(name.strip()), PLACEHOLDERS["project"], text, flags=re.IGNORECASE
        )
        count += n
    return text, count


def redact(
    content: str,
    *,
    project_names: Iterable[str] = (),
    private_url_patterns: Iterable[str] = (),
) -> Redaction:
    """Replace what the four detectors would have refused, and count each kind.

    Order matters and is deliberate: paths first, because a Windows path can
    contain what looks like an e-mail-shaped token and a URL can contain a path;
    URLs before project names so a project name inside a private URL vanishes
    with the URL rather than leaving `[REDACTED:project]` inside a live link.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    counts = dict.fromkeys(PLACEHOLDERS, 0)
    text, n = _replace_all(content, _WINDOWS_PATH, PLACEHOLDERS["path"])
    counts["path"] += n
    text, n = _replace_all(text, _POSIX_PATH, PLACEHOLDERS["path"])
    counts["path"] += n
    text, n = _replace_private_urls(text, _compile_patterns(private_url_patterns))
    counts["url"] += n
    text, n = _replace_all(text, _EMAIL, PLACEHOLDERS["email"])
    counts["email"] += n
    text, n = _replace_project_names(text, project_names)
    counts["project"] += n
    return Redaction(text, counts)


__all__ = ["PLACEHOLDERS", "Redaction", "assert_local_destination", "redact"]
