#!/usr/bin/env python3
"""Find the transcripts that belong to THIS project — by proof, not by guess.

The previous rule derived a directory name from the CWD (`path separators ->
dashes`) and, failing to match, fell back to "the most recently touched project
anywhere on this machine". On Windows the match NEVER succeeded: Claude Code
mangles `C:\\Projects\\...` to `c--Projects-…` (both the colon and the backslash become
a dash), while the derived slug was `C-Projects-…`. So the fallback was not a rare
edge — it was the normal path, and it silently handed this project another
project's conversation. Measured in session #227: three consecutive rebuilds of
the token ledger read 42, then 32, then 10 transcripts, because between calls a
different project became the most recently touched one. The same silent
substitution fed `session_metrics --auto` (session token totals and cost) and
`model_routing` (which model is running).

A transcript records the directory it was produced in, under `cwd`. That is
evidence, and it is the ONLY thing this module matches on — no slug is derived
at all, so there is no shape left to get wrong on the next host. Every IDE
profile is scanned (`ide_utils.all_profile_dirs`), not a hand-written pair.

When nothing verifiably belongs to this project the answer is None. Returning
someone else's transcript is worse than returning nothing: the caller cannot
tell, so it believes it.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ide_utils import all_profile_dirs  # noqa: E402

#: How far into a transcript to look for the `cwd` field before giving up. It
#: appears on the first user entry in practice; the cap keeps a mis-shaped or
#: enormous file from turning directory discovery into a full scan.
_CWD_PROBE_LINES = 50

#: Subdirectory each IDE profile keeps its per-project transcript folders under.
_PROJECTS_SUBDIR = "projects"


def _norm(path: str) -> str:
    """Compare-ready form of a filesystem path: absolute, forward slashes, lower."""
    return os.path.abspath(path).replace("\\", "/").rstrip("/").lower()


def _transcript_cwd(path: str) -> str | None:
    """The working directory a transcript was produced in, or None."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for index, line in enumerate(fh):
                if index >= _CWD_PROBE_LINES:
                    return None
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = entry.get("cwd") if isinstance(entry, dict) else None
                if isinstance(cwd, str) and cwd.strip():
                    return cwd
    except OSError:
        return None
    return None


def _jsonl_in(directory: str) -> list[str]:
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    return [os.path.join(directory, n) for n in names if n.endswith(".jsonl")]


def _candidate_dirs() -> list[str]:
    """Every per-project transcript directory the known IDE roots contain."""
    home = os.path.expanduser("~")
    dirs: list[str] = []
    # Every supported IDE profile, not a hand-written pair. Naming `.claude` and
    # `.cursor` by hand made the locator blind on the other five hosts, which is
    # the same "works on the author's setup" defect the ledger already had.
    for profile in sorted(all_profile_dirs()):
        root = os.path.join(home, profile, _PROJECTS_SUBDIR)
        if not os.path.isdir(root):
            continue
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            continue
        dirs.extend(
            os.path.join(root, name) for name in entries if os.path.isdir(os.path.join(root, name))
        )
    return dirs


def project_transcript_dirs(project_dir: str | None = None) -> list[str]:
    """Transcript directories whose contents PROVE they belong to `project_dir`.

    A directory qualifies when at least one transcript in it records a `cwd`
    equal to the project. More than one can qualify — the same project opened
    in two IDEs — and all of them are returned, because the ledger should cover
    the project's work rather than one tool's view of it.
    """
    target = _norm(project_dir or os.getcwd())
    matched: list[str] = []
    for directory in _candidate_dirs():
        files = _jsonl_in(directory)
        if not files:
            continue
        # Newest first: the most recent transcript is the one most likely to
        # still carry the current cwd, and one probe per directory is the whole
        # cost of being right instead of guessing.
        for path in sorted(files, key=_safe_mtime, reverse=True):
            cwd = _transcript_cwd(path)
            if cwd is None:
                continue
            if _norm(cwd) == target:
                matched.append(directory)
            break
    return matched


def _safe_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def project_transcripts(project_dir: str | None = None) -> list[str]:
    """Every transcript of this project across all IDE roots, oldest first."""
    files: list[str] = []
    for directory in project_transcript_dirs(project_dir):
        files.extend(_jsonl_in(directory))
    return sorted(files, key=_safe_mtime)


def latest_project_transcript(project_dir: str | None = None) -> str | None:
    """Newest transcript that verifiably belongs to this project, or None."""
    files = project_transcripts(project_dir)
    return files[-1] if files else None
