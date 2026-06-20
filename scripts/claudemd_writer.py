"""Apply the DYNAMIC:START/END section into agent-instruction files.

Shared by `tausik update-claudemd` so CLAUDE.md and AGENTS.md (and any future
sibling) stay in sync from one dynamic-content source. (v15p-agents-md-bootstrap)
"""

from __future__ import annotations

import difflib
import os
import sys

_MARKER_START = "<!-- DYNAMIC:START -->"
_MARKER_END = "<!-- DYNAMIC:END -->"


def apply_dynamic_section(path: str, dynamic_content: str, dry_run: bool) -> tuple[str, bool]:
    """Replace the DYNAMIC section of `path` with `dynamic_content`.

    Returns (message, changed). `changed` is False when the marker is absent or
    the file is already up-to-date. On dry_run a unified diff is printed and
    `changed` reflects whether the file would change (no write performed).
    """
    dry_run = bool(dry_run)
    name = os.path.basename(path)
    try:
        with open(path, encoding="utf-8") as f:
            original = f.read()
    except OSError as e:
        return f"Error reading {name}: {e}", False

    if _MARKER_START not in original:
        return f"Warning: {_MARKER_START} marker not found in {name} — skipped", False

    start_at = original.index(_MARKER_START)
    before = original[: start_at + len(_MARKER_START)]
    # Locate END strictly AFTER START so a marker mentioned earlier in body text,
    # or a second marker pair, cannot mis-slice and drop content.
    end_at = original.find(_MARKER_END, start_at + len(_MARKER_START))
    if end_at != -1:
        after = original[end_at:]
        new_content = f"{before}\n{dynamic_content}\n{after}"
    else:
        new_content = f"{before}\n{dynamic_content}\n{_MARKER_END}\n"

    if new_content == original:
        return f"{name} already up-to-date ({path})", False

    if dry_run:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"{name} (current)",
            tofile=f"{name} (would write)",
            lineterm="",
        )
        sys.stdout.write("".join(diff))
        sys.stdout.write("\n")
        return f"{name} would change ({path})", True

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return f"{name} updated ({path})", True


def resolve_sibling_targets(primary: str) -> list[str]:
    """Return [primary] plus an existing AGENTS.md sibling in the SAME directory
    as `primary`, de-duplicated. The sibling is resolved relative to primary's
    dir (never a bare cwd-relative 'AGENTS.md', which under an MCP server's cwd
    could hit an unrelated file)."""
    targets = [primary]
    sibling = os.path.join(os.path.dirname(primary) or ".", "AGENTS.md")
    if os.path.exists(sibling) and os.path.abspath(sibling) != os.path.abspath(primary):
        targets.append(sibling)
    return targets
