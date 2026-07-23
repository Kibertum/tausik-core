"""A tiny `**`-aware path glob, and the normalisation every comparison needs.

Split out of `memory_sinks` for the filesize cap the framework enforces on
everyone else — and the split is on a real seam: this module knows nothing
about memory, agents, or policy. It answers one question, "does this pattern
describe this path", and `fnmatch` cannot: `fnmatch` treats `/` as an ordinary
character, so `.claude/**/memory/**` there matches nothing useful.

The language is deliberately smaller than gitignore's: `*` matches within one
path segment, `**` matches zero or more whole segments. Zero is the load-bearing
half — `.claude/**/memory/**` has to match `.claude/memory/notes.md`, which the
original hand-rolled check had to special-case.

Normalisation is lowercase, and that is a fix rather than a convenience: the
case-sensitive version of the auto-memory guard was a real bypass on Linux and
macOS (CHANGELOG: "memory_pretool_block Linux/macOS bypass via case") — a path
ending `/MEMORY/a.md` sailed past a rule spelled for `memory`, on the two
platforms where the filesystem lets both spellings exist.
"""

from __future__ import annotations

import fnmatch
import os


def normalize(path: str) -> str:
    """Lowercase, forward-slash, `.`-collapsed, unanchored form.

    Both sides of every comparison go through this, so a Windows backslash, a
    trailing separator and a `../` are not three different ways to spell the
    same path to a rule.
    """
    if not path:
        return ""
    return os.path.normpath(path).replace("\\", "/").strip("/").lower()


def _segment_match(pattern_seg: str, seg: str) -> bool:
    if pattern_seg == "*":
        return True
    if "*" not in pattern_seg:
        return pattern_seg == seg
    return fnmatch.fnmatchcase(seg, pattern_seg)


def glob_match(pattern: str, path: str) -> bool:
    """`**`-aware segment glob. Both arguments must already be normalised."""
    return _match_segments(pattern.split("/"), path.split("/"))


def _match_segments(pat: list[str], seg: list[str]) -> bool:
    if not pat:
        return not seg
    if pat[0] == "**":
        # Two readings, and `**` means both: consume zero segments here, or
        # consume one and stay on the same pattern element.
        if _match_segments(pat[1:], seg):
            return True
        return bool(seg) and _match_segments(pat, seg[1:])
    if not seg:
        return False
    return _segment_match(pat[0], seg[0]) and _match_segments(pat[1:], seg[1:])
