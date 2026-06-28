"""AIDD scaffold handler — `tausik init --template aidd`.

Copies AIDD layer files (idea.md / vision.md / conventions.md) from the
framework's templates directory into the current project root. Existing
files are preserved by default; the user is prompted with a 4-option
conflict choice (overwrite / merge-append / skip / abort-all). `--force`
short-circuits the prompt and overwrites.
"""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any, Callable

AIDD_FILES: tuple[str, ...] = ("idea.md", "vision.md", "conventions.md")

_KNOWN_TEMPLATES: frozenset[str] = frozenset({"aidd"})

# Conflict-prompt choices. First letter is the canonical key; defaults
# to skip when the user hits Enter.
_PROMPT = "[o] overwrite  [m] merge-append  [s] skip (default)  [a] abort-all"


def is_known_template(name: str) -> bool:
    return name in _KNOWN_TEMPLATES


def find_templates_dir() -> str | None:
    """Return absolute path of harness/aidd-templates/ relative to this file's
    repo. Returns None if it doesn't exist."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)  # scripts/ → repo root
    cand = os.path.join(repo, "harness/aidd-templates")
    if os.path.isdir(cand):
        return cand
    return None


def _read(path: str) -> str:
    # errors="replace": an existing user file may be non-UTF-8 (e.g. cp1252
    # on Windows); the merge/read paths must not crash on a bad byte.
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _merge_append_content(existing: str, new: str) -> str:
    """Append `new` after `existing` with a merge marker. Pure string op."""
    if not existing.endswith("\n"):
        existing += "\n"
    return existing + "\n<!-- merged from AIDD template -->\n" + new


def _merge_append(existing_path: str, template_path: str) -> None:
    _write(existing_path, _merge_append_content(_read(existing_path), _read(template_path)))


def _resolve_choice(raw: str) -> str:
    """Map prompt input to canonical action. Empty / unknown → skip."""
    s = (raw or "").strip().lower()
    if not s:
        return "skip"
    if s[0] == "o":
        return "overwrite"
    if s[0] == "m":
        return "merge-append"
    if s[0] == "a":
        return "abort-all"
    return "skip"


def _apply_action(action: str, dst: str, src: str, log: Callable[[str], None]) -> str:
    """Returns one of: 'created', 'overwritten', 'merged', 'skipped'."""
    if action == "overwrite":
        shutil.copyfile(src, dst)
        log(f"  overwritten: {os.path.basename(dst)}")
        return "overwritten"
    if action == "merge-append":
        _merge_append(dst, src)
        log(f"  merged-append: {os.path.basename(dst)}")
        return "merged"
    log(f"  skipped: {os.path.basename(dst)} (existing file preserved)")
    return "skipped"


def write_file_with_conflict(
    dst: str,
    content: str,
    *,
    force: bool = False,
    prompt: Callable[[str], str] | None = None,
    log: Callable[[str], None] | None = None,
) -> str:
    """Write `content` to a single file honoring AIDD conflict semantics.

    Mirrors scaffold_aidd's per-file behaviour for generated (in-memory)
    content rather than a template source path. Returns one of:
    'created', 'overwritten', 'merged', 'skipped'.
    """
    log = log or (lambda msg: print(msg))
    prompt = prompt or input
    name = os.path.basename(dst)
    if not os.path.exists(dst):
        _write(dst, content)
        log(f"  created: {name}")
        return "created"
    if force:
        _write(dst, content)
        log(f"  overwritten (--force): {name}")
        return "overwritten"
    log(f"Conflict: {name} already exists. {_PROMPT}")
    action = _resolve_choice(prompt("> "))
    if action == "overwrite":
        _write(dst, content)
        log(f"  overwritten: {name}")
        return "overwritten"
    if action == "merge-append":
        _write(dst, _merge_append_content(_read(dst), content))
        log(f"  merged-append: {name}")
        return "merged"
    # skip + abort-all both leave the existing single file untouched.
    log(f"  skipped: {name} (existing file preserved)")
    return "skipped"


def scaffold_aidd(
    project_root: str,
    *,
    force: bool = False,
    prompt: Callable[[str], str] | None = None,
    log: Callable[[str], None] | None = None,
) -> dict:
    """Copy AIDD templates into project_root with conflict handling.

    Returns a dict: {created: [...], overwritten: [...], merged: [...],
    skipped: [...], aborted: bool}.
    """
    log = log or (lambda msg: print(msg))
    prompt = prompt or input

    src_dir = find_templates_dir()
    if src_dir is None:
        raise FileNotFoundError("AIDD templates not found in harness/aidd-templates")

    result: dict[str, Any] = {
        "created": [],
        "overwritten": [],
        "merged": [],
        "skipped": [],
        "aborted": False,
    }
    aborted = False

    for fname in AIDD_FILES:
        src = os.path.join(src_dir, fname)
        dst = os.path.join(project_root, fname)
        if not os.path.exists(dst):
            shutil.copyfile(src, dst)
            log(f"  created: {fname}")
            result["created"].append(fname)
            continue
        # Conflict.
        if force:
            shutil.copyfile(src, dst)
            log(f"  overwritten (--force): {fname}")
            result["overwritten"].append(fname)
            continue
        if aborted:
            log(f"  skipped (aborted): {fname}")
            result["skipped"].append(fname)
            continue
        log(f"Conflict: {fname} already exists. {_PROMPT}")
        action = _resolve_choice(prompt("> "))
        if action == "abort-all":
            aborted = True
            result["aborted"] = True
            log(f"  abort-all: {fname} and remaining files left untouched")
            result["skipped"].append(fname)
            continue
        outcome = _apply_action(action, dst, src, log)
        bucket = {"overwritten": "overwritten", "merged": "merged", "skipped": "skipped"}[outcome]
        result[bucket].append(fname)

    return result


def cmd_init_template(template: str, force: bool = False) -> int:
    """CLI entry. Returns POSIX-style exit code (0 ok, non-zero on error)."""
    if not is_known_template(template):
        print(f"Unknown template: {template}", file=sys.stderr)
        return 2
    project_root = os.getcwd()
    try:
        result = scaffold_aidd(project_root, force=force)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    created = len(result["created"])
    overwritten = len(result["overwritten"])
    merged = len(result["merged"])
    skipped = len(result["skipped"])
    print(
        f"AIDD scaffold ({template}): "
        f"{created} created, {overwritten} overwritten, "
        f"{merged} merged, {skipped} skipped."
    )
    return 0
