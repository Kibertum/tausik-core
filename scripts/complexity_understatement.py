"""l26-complexity-self-declared: make an understated complexity VISIBLE at close.

Every hard QG-0 gate keys on ``task.complexity in ('medium', 'complex')`` — the
scope_paths requirement (gate_qg0_check) and the rollback_plan requirement.
Complexity is DECLARED BY THE AGENT, so declaring ``simple`` (or leaving it
unset) silently downgrades SENAR Rule 2 and Rule 6 to mere warnings.

This detects the dodge at task-done — the first point an objective signal
exists: the files the task actually touched — and surfaces it instead of letting
it pass in silence (Decision #158). It is ADVISORY, never blocking: the proxy is
deliberately imperfect (a four-file rename is legitimately simple), so a false
positive costs only one advisory line, and the mechanism must never crash the
close (gotcha #271). The point is visibility, not prevention — a low declaration
that dodged the gates is recorded and shown, not punished.
"""

from __future__ import annotations

import re

# complexity-heuristic-counts-doc-mirrors. The proxy is "files touched", but a
# handful of them are touched by EVERY task regardless of size: both CHANGELOGs
# (made mandatory by convention #275), the framework-maintained CLAUDE.md and
# its synced AGENTS.md sibling, the generated constants, and each doc that
# exists twice because the project ships a Russian mirror. A one-line fix
# arrived at close carrying +6 files and was told it looked 'complex' — seven
# sessions running, and every one of those advisories was ALSO written to the
# supervision log, so the calibration data now holds a systematic
# understatement that never happened.
#
# CLAUDE.md and AGENTS.md are ONE decision written twice: `tausik
# update-claudemd` writes both from a single dynamic-content source
# (claudemd_writer.resolve_sibling_targets), so touching AGENTS.md carries no
# more behaviour than touching CLAUDE.md. The sibling basename is read from the
# producer — hand-listing a second copy here is how the two silently drift.
#
# The fix is to the measured quantity, not to the scale: the thresholds below
# are untouched. What changes is that a file only counts when it can carry a
# behaviour change.
try:
    from claudemd_writer import CLAUDEMD_SIBLING_BASENAME as _SIBLING
except ImportError:  # pragma: no cover — defensive: never crash the close (gotcha #271)
    _SIBLING = "AGENTS.md"

_CEREMONY_FILES = frozenset(
    {
        "changelog.md",
        "changelog.ru.md",
        "claude.md",
        _SIBLING.lower(),
    }
)

_GENERATED_DIRS = ("docs/_generated/",)

# `docs/ru/x.md` and `docs/en/x.md` are one document in two languages; so are
# `README.md` and `README.ru.md`. A pair is one decision, so it counts once.
_LANG_DIR_RE = re.compile(r"^(?P<head>.*?)docs/(?:ru|en)/(?P<tail>.+)$")
_LANG_SUFFIX_RE = re.compile(r"^(?P<stem>.+)\.(?:ru|en)\.md$")


def _normalise(path: str) -> str:
    """Forward slashes, no leading `./`, lowercase — Windows writes both ways."""
    return path.replace("\\", "/").strip().lstrip("./").lower()


def _canonical_key(path: str) -> str:
    """Collapse a translation mirror onto the document it mirrors.

    A LONE mirror keeps its own key by construction: the key is derived from the
    path, not looked up against the set, so editing only `README.ru.md` still
    counts as one file. Dropping it instead would make translation work
    invisible — the opposite error, and a more insulting one.
    """
    low = _normalise(path)
    m = _LANG_DIR_RE.match(low)
    if m:
        return f"{m.group('head')}docs/*/{m.group('tail')}"
    m = _LANG_SUFFIX_RE.match(low)
    if m:
        return f"{m.group('stem')}.md"
    return low


def behaviour_bearing_files(relevant_files: list[str] | None) -> list[str]:
    """The subset of `relevant_files` that can actually carry a behaviour change.

    Drops the files every task touches by ceremony, drops generated artefacts,
    and counts a document once rather than once per language. Returns the
    original paths (first spelling wins) so a caller can show them.
    """
    kept: dict[str, str] = {}
    for raw in relevant_files or []:
        if not raw or not isinstance(raw, str):
            continue
        low = _normalise(raw)
        if not low:
            continue
        if low in _CEREMONY_FILES:
            continue
        if any(f"/{low}".find(f"/{d}") >= 0 for d in _GENERATED_DIRS):
            continue
        kept.setdefault(_canonical_key(raw), raw)
    return list(kept.values())


# Objective ceilings on how many files a task of each declared complexity is
# expected to touch. Deliberately lenient: a simple task legitimately edits one
# or two files; touching MANY is the hallmark of the medium/complex work whose
# scope/rollback gates were dodged. These are the visibility thresholds, not a
# hard gate — raising them only quiets advisories, it never weakens a gate.
_SIMPLE_MAX_FILES = 3
_MEDIUM_MAX_FILES = 10

_RANK = {"simple": 1, "medium": 2, "complex": 3}


def implied_complexity(file_count: int) -> str:
    """The complexity the touched-file count alone would imply."""
    if file_count > _MEDIUM_MAX_FILES:
        return "complex"
    if file_count > _SIMPLE_MAX_FILES:
        return "medium"
    return "simple"


def understatement(declared: str | None, relevant_files: list[str] | None) -> dict | None:
    """Return ``{declared, implied, file_count, declared_count}`` when the declared
    complexity is LOWER than what the touched-file count implies, else ``None``.

    A ``None``/unknown ``declared`` is treated as ``simple``: an unset complexity
    dodges exactly the same gates as an explicit ``simple`` and so earns the same
    scrutiny. ``complex`` can never be understated (nothing outranks it).

    ``file_count`` is the count of BEHAVIOUR-BEARING files; ``declared_count``
    is how many were declared. Both are reported, because a warning that says
    "touched 9 files" about a task whose `git status` shows 13 reads like a bug
    in the warning.
    """
    # De-duplicate before counting: a caller that merges two `git diff` lists,
    # or a wrapper that double-adds a path, would otherwise inflate the count and
    # cross a threshold it should not — an avoidable false-positive advisory.
    declared_files = list(dict.fromkeys(f for f in (relevant_files or []) if f))
    files = behaviour_bearing_files(declared_files)
    count = len(files)
    declared_key = (declared or "simple").strip().lower()
    declared_rank = _RANK.get(declared_key, 1)  # unknown label -> treat as simple
    implied = implied_complexity(count)
    if _RANK[implied] > declared_rank:
        return {
            "declared": declared_key,
            "implied": implied,
            "file_count": count,
            "declared_count": len(declared_files),
        }
    return None


def warn_if_understated(be, slug: str, declared: str | None, relevant_files) -> str:
    """Detect an understated complexity, record it, and return a visible warning.

    Returns ``""`` when the declaration is honest. Records one supervision
    DETECTION event (``action='complexity_understated'``, details carry only the
    COUNT — never the paths) when it is not. Everything here is best-effort and
    swallowed: it runs inside ``task_done`` and must never block or crash the
    close (Decision #158, gotcha #271).
    """
    try:
        u = understatement(declared, relevant_files)
    except Exception:  # noqa: BLE001 — best-effort: never blocks the close
        return ""
    if u is None:
        return ""
    try:
        be.event_add(
            "supervision",
            slug,
            "complexity_understated",
            f"declared={u['declared']} implied={u['implied']} files={u['file_count']} "
            f"declared_files={u['declared_count']}",
        )
    except Exception:  # noqa: BLE001 — best-effort telemetry, never blocks
        pass
    return (
        f"COMPLEXITY UNDERSTATED: declared '{u['declared']}' but touched "
        f"{u['file_count']} behaviour-bearing files of {u['declared_count']} "
        f"declared — implies '{u['implied']}'. QG-0 scope/rollback "
        f"hard gates key on complexity, so a low declaration downgraded SENAR "
        f"Rules 2/6 to warnings. Recorded for audit."
    )
