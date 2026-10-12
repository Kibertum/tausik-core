"""Deterministic serialization primitives for the git-native state export.

`state-git-export` projects the TAUSIK DB to a `tausik/` markdown tree, one file
per entity, so team state travels git-native (Decision #172, spec
`docs/ru/team-state-in-git.md`). The whole epic rests on ONE property: the same
DB state yields a **byte-identical** file on every machine and on every re-run —
otherwise the diff churns and merges falsely conflict.

That property is bought here, not in the entity renderers: a hand-rolled YAML
frontmatter emitter (stdlib only — the export is core, not an optional PyYAML
dep) with a FIXED key order, deterministic list sorting, explicit `null`, and
conservative quoting of strings a YAML parser could misread as a number/bool/
date (`2026-01`, `on`). Newlines are LF-only with exactly one trailing `\n`.
Prose lives in the body; the frontmatter carries only machine fields.

Read-only on the DB. Only :func:`write_tree` touches the filesystem.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

# The export owns *.md under the tree; deletion reconciliation is scoped to this
# suffix so pointing --out at a populated dir can never nuke unrelated files.
MANAGED_SUFFIX = ".md"

# THE registry of projected kinds — one definition, both directions. The export
# and the import each used to declare their own copy of this list (a frozenset
# there, a tuple here), with nothing comparing them: a kind added to one side and
# forgotten on the other would be written and never read back, or read and never
# written, and the round-trip gate would only notice once real data hit it.
# Order is load-bearing for the importer (parents before children), so the
# canonical form is the tuple; the export derives its set from it.
ENTITY_DIRS: tuple[str, ...] = ("epics", "stories", "tasks", "decisions", "memory")

# A string safe to emit as a YAML *plain* scalar: starts with a letter, then only
# letters/digits/`_.-`. Everything else (leading digit, spaces, punctuation,
# Cyrillic, YAML indicators) is double-quoted. Slugs and enum statuses match;
# titles, dates and slug-like `2026-01` do not — exactly the contract's intent.
_PLAIN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")

# YAML 1.1 reads these as bool/null/float even unquoted, so a string equal to one
# (case-insensitively) MUST be quoted or a round-trip would change its type. The
# signed/dotted float specials (-inf, .nan, ...) already fail _PLAIN_RE (no
# leading letter), so only bare letter-initial tokens need listing: y/n are
# YAML-1.1 core-schema bools; inf/nan are floats — a strict 1.1 parser reads a
# bare `- n` list item as False and `inf`/`nan` as numbers.
_RESERVED = frozenset(
    {"true", "false", "yes", "no", "on", "off", "y", "n", "null", "none", "~", "inf", "nan"}
)


# --- normalization -----------------------------------------------------------


def normalize_ts(raw: Any) -> str | None:
    """ISO-8601 UTC with a `Z` suffix and no microseconds, or None when empty.

    Accepts the canonical `utcnow_iso()` form (`YYYY-MM-DDTHH:MM:SSZ`, passes
    through unchanged), a space-separated SQLite datetime, an offset form, or a
    microsecond form. An unparseable value is returned stripped-but-verbatim —
    still deterministic (the DB value is identical on every machine), just not
    reformatted.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    iso = s.replace(" ", "T", 1)
    iso = iso[:-1] + "+00:00" if iso.endswith(("Z", "z")) else iso
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return s
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_body(text: Any) -> str:
    """LF-only, leading/trailing-whitespace-stripped prose for a file body."""
    if text is None:
        return ""
    return str(text).replace("\r\n", "\n").replace("\r", "\n").strip()


def flatten_line(text: Any) -> str:
    """Collapse all whitespace runs to single spaces — for one-line journal rows.

    A journal entry is `- <ts> [<phase>] — <message>` on ONE line so two branches
    merge as added lines; a multi-line message would break that, so it is
    flattened (deterministic, and the message stays readable).
    """
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


# --- YAML scalar / list emission ---------------------------------------------


def _needs_quote(s: str) -> bool:
    return s == "" or s != s.strip() or _PLAIN_RE.match(s) is None or s.lower() in _RESERVED


def _dq(s: str) -> str:
    """Double-quoted YAML scalar with minimal, round-trippable escaping."""
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{s}"'


def scalar(value: Any) -> str:
    """Render a scalar frontmatter value: None→`null`, int→bare, str→plain/quoted."""
    if value is None:
        return "null"
    if isinstance(value, bool):  # guard: bool is an int subclass
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    s = str(value)
    return s if not _needs_quote(s) else _dq(s)


def _emit(key: str, value: Any, out: list[str]) -> None:
    """Append `key: <value>` line(s) to `out` for a frontmatter pair.

    Lists render block-style (`key:` then `  - item`), an empty list as `key: []`.
    A list of dicts (edges) renders each item as an indented mapping whose own
    keys keep their given order. Scalars use :func:`scalar`.
    """
    if isinstance(value, list):
        if not value:
            out.append(f"{key}: []\n")
            return
        out.append(f"{key}:\n")
        for item in value:
            if isinstance(item, list) and item and isinstance(item[0], tuple):
                # ordered mapping: list[(k, v)] — first key on the `- ` line
                first_k, first_v = item[0]
                out.append(f"  - {first_k}: {scalar(first_v)}\n")
                for k, v in item[1:]:
                    out.append(f"    {k}: {scalar(v)}\n")
            else:
                out.append(f"  - {scalar(item)}\n")
        return
    out.append(f"{key}: {scalar(value)}\n")


def frontmatter(pairs: list[tuple[str, Any]]) -> str:
    """Emit an ordered frontmatter block body (no `---` fences).

    `pairs` is an ordered list of (key, value); the ORDER is the contract, so it
    is preserved exactly (never sorted). Values: None, int, str, list[str] or
    list of ordered mappings (each a `list[(k, v)]`).
    """
    out: list[str] = []
    for key, value in pairs:
        _emit(key, value, out)
    return "".join(out)


def render_file(pairs: list[tuple[str, Any]], body: str | None) -> str:
    """Assemble a full entity file: `---` frontmatter `---` + optional body.

    Exactly one trailing `\\n`; LF throughout. An empty body yields just the
    fenced frontmatter (no dangling blank lines) so absence stays byte-stable.
    """
    parts = ["---\n", frontmatter(pairs), "---\n"]
    body_norm = normalize_body(body)
    if body_norm:
        parts.append("\n")
        parts.append(body_norm)
        parts.append("\n")
    return "".join(parts)


def section(title: str, content: Any) -> list[str]:
    """A `## title` block; empty content leaves the header with no body lines."""
    body = normalize_body(content)
    if not body:
        return [f"## {title}", ""]
    return [f"## {title}", "", body]


def join_sections(*blocks: list[str]) -> str:
    """Join `## section` blocks with one blank line before each heading."""
    return "\n\n".join("\n".join(b).rstrip() for b in blocks).strip()


# --- filesystem write / check / target guard ---------------------------------


def assert_export_target(out: str, project_root: str) -> str:
    """Refuse an --out that escapes `project_root`; return its abspath.

    write_tree reconciles deletions (removes managed *.md not in the tree), so a
    stray target could delete unrelated markdown. The target must be a directory
    STRICTLY INSIDE the project root — never the root itself, never outside.
    """
    out_abs = os.path.abspath(out)
    root_abs = os.path.abspath(project_root)
    # normcase for the COMPARISON only (return the real-cased path): on
    # case-insensitive filesystems (Windows/macOS) a legitimate --out that differs
    # only in casing (d:\ vs D:\) must not be refused as "outside" — over-refusal
    # is a usability bug, so fold case before comparing but never for the result.
    out_cmp = os.path.normcase(out_abs)
    root_cmp = os.path.normcase(root_abs)
    try:
        inside = os.path.commonpath([out_cmp, root_cmp]) == root_cmp
    except ValueError:  # different drive on Windows → not inside
        inside = False
    if not inside or out_cmp == root_cmp:
        raise ValueError(
            f"refusing --out {out_abs!r}: the export target must be a directory "
            f"strictly inside the project root {root_abs!r} — write reconciles "
            "deletions of *.md and must never touch files elsewhere"
        )
    return out_abs


def _managed_on_disk(root: str, managed_dirs: set[str] | None = None) -> set[str]:
    """Relative '/'-normalized paths of managed (*.md) files under `root`.

    When `managed_dirs` is given, only files whose FIRST path segment is in that
    set are considered exporter-owned — so a hand-written `tausik/README.md` (or
    files under any non-entity dir) are invisible to deletion reconciliation and
    can never be swept. `None` means "every *.md" (generic/back-compat).
    """
    found: set[str] = set()
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(MANAGED_SUFFIX):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            if managed_dirs is not None and rel.split("/", 1)[0] not in managed_dirs:
                continue
            found.add(rel)
    return found


def write_tree(
    root: str, tree: dict[str, str], managed_dirs: set[str] | None = None
) -> dict[str, Any]:
    """Write `tree` under `root`, reconciling managed-file deletions.

    Managed (*.md) files on disk absent from `tree` are removed (a deleted entity
    drops its file); `managed_dirs` scopes what "managed" means so non-exporter
    files are never touched. Files are written with LF newlines. Returns
    {written, deleted, deleted_paths} — deleted_paths is returned (not swallowed)
    so the caller can announce every removal (no silent data loss).
    """
    deleted_paths = sorted(_managed_on_disk(root, managed_dirs) - set(tree))
    for rel in deleted_paths:
        os.remove(os.path.join(root, rel.replace("/", os.sep)))
    written = 0
    for rel in sorted(tree):
        path = os.path.join(root, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(tree[rel])
        written += 1
    _prune_empty_dirs(root)
    return {"written": written, "deleted": len(deleted_paths), "deleted_paths": deleted_paths}


def _prune_empty_dirs(root: str) -> None:
    """Remove now-empty subdirectories left after deletion reconciliation.

    `topdown=False` yields children before parents so a nested empty subtree
    prunes bottom-up in one pass. rmdir is best-effort (a concurrent write or
    permission error is swallowed, not propagated).
    """
    for dirpath, _dirs, _files in os.walk(root, topdown=False):
        if os.path.abspath(dirpath) == os.path.abspath(root):
            continue
        if not os.listdir(dirpath):
            try:
                os.rmdir(dirpath)
            except OSError:
                pass


def check_tree(root: str, tree: dict[str, str], managed_dirs: set[str] | None = None) -> list[str]:
    """Drift messages comparing the on-disk tree to `tree` ([] = clean).

    Files are read with `newline=""` so text-mode universal-newline translation
    can NOT hide a CRLF/CR corruption: contract rule #1 is LF-only *including on
    Windows*, and a byte comparison against the LF-only `tree` is the only way
    `--check` catches a teammate's editor (or `core.autocrlf=true`) re-saving a
    file with CRLF — the exact silent byte-nonidentity this gate exists to flag.
    """
    if not os.path.isdir(root):
        return [f"missing tree: {root} does not exist (run `tausik state export`)"]
    drift: list[str] = []
    on_disk = _managed_on_disk(root, managed_dirs)
    for rel in sorted(set(tree) - on_disk):
        drift.append(f"missing: {rel} (entity in DB has no exported file)")
    for rel in sorted(on_disk - set(tree)):
        drift.append(f"stale: {rel} (no matching entity in DB — should be removed)")
    for rel in sorted(set(tree) & on_disk):
        path = os.path.join(root, rel.replace("/", os.sep))
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                current = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            # An unreadable/mis-encoded tracked file is drift, not a CLI crash:
            # project.py's dispatcher does not catch these, so surface them here.
            drift.append(f"unreadable: {rel} ({e})")
            continue
        if current != tree[rel]:
            drift.append(f"changed: {rel} (exported file differs from DB state)")
    return drift
