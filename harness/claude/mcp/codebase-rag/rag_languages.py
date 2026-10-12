"""Which files RAG reads, and where it cuts them — built in, and per project.

GitLab #11 (github#26): a Godot project indexed its design docs and tools and
not one file of the game. TAUSIK lets a user add a STACK (.tausik/stacks/<name>/),
but the RAG language list was closed: .gd/.gdshader/.tscn/.tres/.godot had no
entry, `detect_language` returned None, and the files never reached chunking.
Patching the deployed server does not survive bootstrap.

So two things. The Godot formats are built in (below). And a project can add its
own in `.tausik/config.json`, which bootstrap never overwrites:

    "rag": {
      "extra_extensions": {".unity": "unity-scene"},
      "boundaries": {"unity-scene": "^--- !u!"}
    }

A built-in entry is never overridden by the knob. A bad entry — an extension
without its dot, an empty language, a regex that does not compile, a block that
is not a mapping — is skipped and REPORTED: `problems` travels to `rag_status`.
Falling silently back to "no language" is exactly the failure this module fixes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

BUILTIN_EXTENSIONS: dict[str, str] = {
    ".gd": "gdscript",
    ".gdshader": "gdshader",
    ".tscn": "godot-scene",
    ".tres": "godot-resource",
    ".godot": "godot-project",
}

BUILTIN_BOUNDARIES: dict[str, re.Pattern[str]] = {
    "gdscript": re.compile(
        r"^(func |static func |class |class_name |signal |enum |@export)", re.MULTILINE
    ),
    "gdshader": re.compile(r"^(void |uniform |shader_type |struct |const )", re.MULTILINE),
    "godot-scene": re.compile(r"^\[", re.MULTILINE),
    "godot-resource": re.compile(r"^\[", re.MULTILINE),
}


#: A group that contains a quantifier and is itself quantified — `(a+)+`,
#: `(\\w+\\s?)*` — backtracks exponentially on a near-miss line. Such a regex from
#: the config would hang the indexer (session #267 review: 35 characters, >120 s).
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[*+?}][^)]*\)\s*[*+?{]")


@dataclass
class ProjectLanguages:
    """What one project adds on top of the built-in lists."""

    extensions: dict[str, str] = field(default_factory=dict)
    boundaries: dict[str, re.Pattern[str]] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


def _config_path(project_dir: str) -> str | None:
    """The project's config path from the one helper that builds it (tausik_utils).

    The helper lives in `scripts/`, two levels up when deployed
    (.claude/mcp/codebase-rag -> .claude/scripts) and four in the source tree;
    the background reindex puts only this directory on sys.path, so both are tried.
    """
    import sys

    here = os.path.dirname(os.path.abspath(__file__))
    for up in (("..", ".."), ("..", "..", "..", "..")):
        cand = os.path.normpath(os.path.join(here, *up, "scripts"))
        if os.path.isfile(os.path.join(cand, "tausik_utils.py")) and cand not in sys.path:
            sys.path.append(cand)
    try:
        from tausik_utils import tausik_config_path
    except ImportError:
        return None
    return tausik_config_path(project_dir)


def _rag_block(project_dir: str) -> tuple[object, str | None]:
    path = _config_path(project_dir)
    if path is None:
        return {}, "tausik_utils not found next to the RAG server; rag.* not applied"
    if not os.path.isfile(path):
        return {}, None
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        return {}, f"config.json unreadable, rag.* not applied: {e}"
    return (cfg.get("rag", {}) if isinstance(cfg, dict) else {}), None


def load(project_dir: str, builtin_ext: dict[str, str] | None = None) -> ProjectLanguages:
    """The project's `rag.extra_extensions` / `rag.boundaries`, validated."""
    out = ProjectLanguages()
    block, err = _rag_block(project_dir)
    if err:
        out.problems.append(err)
    if not isinstance(block, dict):
        out.problems.append("rag must be a mapping; ignored")
        return out
    builtin = builtin_ext or {}
    exts = block.get("extra_extensions", {})
    if not isinstance(exts, dict):
        out.problems.append("rag.extra_extensions must be a mapping {'.ext': 'language'}; ignored")
        exts = {}
    for ext, lang in exts.items():
        key = str(ext).lower()
        if not key.startswith(".") or len(key) < 2:
            out.problems.append(f"rag.extra_extensions: {ext!r} is not an extension like '.gd'")
        elif not isinstance(lang, str) or not lang.strip():
            out.problems.append(f"rag.extra_extensions: {ext!r} names no language")
        elif key in builtin or key in BUILTIN_EXTENSIONS:
            out.problems.append(f"rag.extra_extensions: {ext!r} is built in; the built-in wins")
        else:
            out.extensions[key] = lang.strip()
    bounds = block.get("boundaries", {})
    if not isinstance(bounds, dict):
        out.problems.append("rag.boundaries must be a mapping {'language': 'regex'}; ignored")
        bounds = {}
    for lang, rx in bounds.items():
        if _NESTED_QUANTIFIER.search(str(rx)):
            out.problems.append(
                f"rag.boundaries: {lang!r} regex nests quantifiers (like (a+)+) and could "
                "hang the indexer; rewrite it without a quantified group of quantifiers"
            )
            continue
        try:
            out.boundaries[str(lang)] = re.compile(str(rx), re.MULTILINE)
        except re.error as e:
            out.problems.append(f"rag.boundaries: {lang!r} regex does not compile: {e}")
    return out
