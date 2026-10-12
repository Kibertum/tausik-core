"""Where a project's source lives — asked of the PROJECT, not assumed.

MEASURED BEFORE THIS EXISTED (spike ag-spike-schema-against-three-stacks, on the
`tests/consumer_layout.py` fixture — a project where TAUSIK is a linked library):
`symbol_index.build_index` found ZERO declarations while `backend/api/orders.py`
and `backend/app/services/quota.py` sat there full of them. Nothing was broken.
The roots were `("scripts", "bootstrap", "tests", "harness")` — the names of OUR
tree, shipped as a constant into everybody else's.

WHY THAT IS WORSE THAN AN EMPTY ANSWER. A consumer usually DOES have a
`scripts/` directory holding its own deploy and backup scripts. So the index
returns a slice of the wrong thing and looks like it worked, which is the one
outcome an index must never produce.

THREE SOURCES, IN THIS ORDER, AND THE ANSWER SAYS WHICH ONE SPOKE:

  1. DECLARED  — `source_roots` in `.tausik/config.json`. The project's own word
     outranks anything we infer, the same way its gate configuration does.
  2. GIT       — top-level directories holding files git actually tracks.
     Tracked, not present on disk: `node_modules/` and `build/` are on disk and
     are not the project's source, and git already knows the difference because
     somebody wrote it down in `.gitignore`.
  3. DISK      — the same scan without git, for a project that is not a
     repository yet. Named separately because its answer is weaker and the
     reader is entitled to know that.

There is no fourth source and no hardcoded fallback list. A tree whose source we
cannot locate yields NO roots and says so — an empty answer that names its own
cause, rather than a confident answer about the wrong directories (decision
#334: an unmeasurable quantity yields absence, not zero).
"""

from __future__ import annotations

import json
import os
import subprocess


def _ide_profile_dirs() -> frozenset[str]:
    """Deployed IDE profile directories, FROM THE REGISTRY.

    Writing `.claude`, `.cursor`, `.qwen` here as literals would be a second
    list of the hosts, and a second list drifts from the first the moment a host
    is added — silently, because nothing compares them. `ide_utils` already
    holds the one list.
    """
    try:
        from ide_utils import IDE_REGISTRY
    except Exception:  # noqa: BLE001 — a root scan must not depend on the registry
        return frozenset()
    return frozenset(str(entry.get("config_dir", "")) for entry in IDE_REGISTRY.values() if entry)


#: Never a source root, whatever the tree looks like. Deployed IDE profiles are
#: byte-copies of `scripts/`, so counting them would triple every answer with
#: duplicates of the same definition; the rest are build output and caches.
_NEVER = _ide_profile_dirs() | frozenset(
    {
        ".git",
        ".tausik",
        ".tausik-lib",
        ".idea",
        ".vscode",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "vendor",
        "dist",
        "build",
        "target",
        ".next",
        ".nuxt",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        "coverage",
    }
)

#: Suffixes that make a directory worth indexing. Deliberately wider than the
#: symbol extractor supports: a root is where a project's SOURCE lives, and the
#: co-change layer works on all of it whether or not we can parse it.
_SOURCE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyi",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".ts",
        ".tsx",
        ".vue",
        ".svelte",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".swift",
        ".dart",
        ".php",
        ".rb",
        ".cs",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".hpp",
        ".tf",
        ".tfvars",
        ".hcl",
        ".sh",
        ".bash",
        ".ps1",
        ".sql",
        ".md",
        ".rst",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
    }
)

#: How deep a scan descends looking for source. A monorepo puts its code under
#: `packages/<name>/src`, so stopping at the top level would find nothing there;
#: going deeper than this starts returning leaf directories as "roots", which is
#: not what a root means.
_MAX_DEPTH = 2


def declared_roots(project_dir: str) -> list[str]:
    """`source_roots` from the project's own config, or an empty list."""
    from tausik_utils import tausik_config_path

    path = tausik_config_path(project_dir)
    try:
        with open(path, encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, ValueError):
        return []
    raw = config.get("source_roots")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(item).strip("/\\") for item in raw if str(item).strip("/\\")]


def _tracked_files(project_dir: str) -> list[str] | None:
    """Paths git tracks, or None when this is not a repository we can read."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=project_dir,
            capture_output=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    # -z and a manual decode: a path may hold bytes that are not valid UTF-8,
    # and losing the whole listing over one of them would silently shrink the
    # answer rather than fail.
    raw = result.stdout.decode("utf-8", errors="replace")
    return [part.replace("\\", "/") for part in raw.split("\0") if part]


def _roots_from_paths(paths: list[str]) -> list[str]:
    """The directories worth indexing, from a list of repo-relative paths."""
    found: set[str] = set()
    for path in paths:
        parts = path.split("/")
        if _NEVER & set(parts):
            continue
        if os.path.splitext(parts[-1])[1].lower() not in _SOURCE_SUFFIXES:
            continue
        if len(parts) == 1:
            continue  # a file at the top level belongs to no root
        # The shallowest directory is the root. `backend/api/orders.py` gives
        # `backend`, not `backend/api`: a root is a place to start walking, and
        # naming the deepest one would make the answer a file list.
        found.add(parts[0])
    return sorted(found)


def _roots_from_disk(project_dir: str) -> list[str]:
    """The same question asked of the filesystem, for a tree without git."""
    found: set[str] = set()
    for entry in sorted(os.listdir(project_dir)):
        # `_NEVER` and nothing else, so this answers the same question as the
        # git source. A blanket skip of dotted names looked tidier and made the
        # two disagree: `.github` is tracked source by one and invisible to the
        # other, and a resolver that answers differently depending on which
        # branch it took is worse than either answer.
        if entry in _NEVER:
            continue
        base = os.path.join(project_dir, entry)
        if not os.path.isdir(base):
            continue
        for current, dirnames, filenames in os.walk(base):
            depth = current[len(base) :].count(os.sep)
            if depth >= _MAX_DEPTH:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if d not in _NEVER]
            if any(os.path.splitext(f)[1].lower() in _SOURCE_SUFFIXES for f in filenames):
                found.add(entry)
                break
    return sorted(found)


def resolve(project_dir: str) -> tuple[list[str], str]:
    """(roots, where they came from) — one of declared, git, disk, none.

    The second element is not decoration. An answer built on `disk` is weaker
    than one built on `git`, and an empty answer means we could not find the
    project's source at all — three different states that would be
    indistinguishable if this returned a bare list.
    """
    declared = declared_roots(project_dir)
    if declared:
        return declared, "declared"

    tracked = _tracked_files(project_dir)
    if tracked is not None:
        roots = _roots_from_paths(tracked)
        if roots:
            return roots, "git"
        # A repository with nothing tracked yet is not a repository whose source
        # we know; fall through rather than answer "no source" about a full tree.

    try:
        roots = _roots_from_disk(project_dir)
    except OSError:
        roots = []
    return roots, ("disk" if roots else "none")


def describe(roots: list[str], source: str) -> str:
    """One line naming what was searched and on whose authority."""
    if not roots:
        return (
            "no source roots found: neither `source_roots` in .tausik/config.json, "
            "nor git-tracked files, nor a directory scan located source in this tree"
        )
    where = {
        "declared": "declared in .tausik/config.json",
        "git": "derived from git-tracked files",
        "disk": "scanned from disk (not a git repository)",
    }.get(source, source)
    return f"roots: {', '.join(roots)} ({where})"
