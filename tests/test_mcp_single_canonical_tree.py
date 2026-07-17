"""Guard: harness/claude/mcp is the ONE canonical MCP tree — no byte-copy mirrors.

There used to be a `harness/cursor/mcp/` holding 19 files that were byte-for-byte
identical to their `harness/claude/mcp/` counterparts, save one word in one docstring.
Nothing generated it; it was maintained by hand. `tausik memory` even carried a
convention for the chore ("adding an MCP tool requires syncing 3 mirrors").

A hand-maintained copy is not redundancy, it is a slow leak: `copy_mcp` prefers
`harness/<ide>/mcp/` when it exists, so the day someone patched only the claude copy,
Cursor users would silently keep running the old server — and no test would notice,
because each mirror passed its own checks in isolation.

The fix was deletion, not a sync test: `copy_mcp` already falls back to
`harness/claude/mcp` for every IDE without a tree of its own (kilo, qwen and opencode
have always relied on exactly that). This guard keeps the mirror from growing back.

An IDE that genuinely needs a different server may still ship one — it just may not be
a *copy*. Identical content is the signature of an unmanaged mirror.

Run: pytest tests/test_mcp_single_canonical_tree.py -v
"""

from __future__ import annotations

import hashlib
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_HARNESS = os.path.join(_ROOT, "harness")
_CANONICAL_IDE = "claude"


def _digest(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _canonical_files() -> dict[str, str]:
    """{relative path under mcp/: sha256} for the canonical tree."""
    root = os.path.join(_HARNESS, _CANONICAL_IDE, "mcp")
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            full = os.path.join(dirpath, name)
            out[os.path.relpath(full, root).replace("\\", "/")] = _digest(full)
    return out


def _other_ide_mcp_files() -> list[tuple[str, str, str]]:
    """(ide, rel_path, sha256) for every .py under harness/<ide>/mcp, ide != claude."""
    found: list[tuple[str, str, str]] = []
    if not os.path.isdir(_HARNESS):
        return found
    for ide in sorted(os.listdir(_HARNESS)):
        if ide == _CANONICAL_IDE:
            continue
        root = os.path.join(_HARNESS, ide, "mcp")
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace("\\", "/")
                found.append((ide, rel, _digest(full)))
    return found


def test_canonical_tree_exists():
    """If this glob ever comes back empty, every other test here is vacuous."""
    canonical = _canonical_files()
    assert canonical, "harness/claude/mcp holds no .py files — the canonical tree is gone"
    assert "project/server.py" in canonical


def test_no_ide_ships_a_byte_copy_of_the_canonical_tree():
    """The load-bearing one. A duplicate mirror WILL drift; copy_mcp prefers it over the
    canonical tree, so the drift ships silently to that IDE's users."""
    canonical = _canonical_files()
    duplicates = [
        f"harness/{ide}/mcp/{rel}"
        for ide, rel, sha in _other_ide_mcp_files()
        if canonical.get(rel) == sha
    ]
    assert not duplicates, (
        "these files duplicate harness/claude/mcp byte-for-byte:\n  "
        + "\n  ".join(duplicates)
        + "\nDelete them: copy_mcp already falls back to harness/claude/mcp for any IDE "
        "without its own tree. A hand-synced mirror is a silent-divergence bug waiting "
        "to happen."
    )


def test_guard_bites_on_a_planted_duplicate(tmp_path, monkeypatch):
    """Negative scenario: plant a byte-identical mirror and the guard must go red.

    Without this, the test above would keep passing if _other_ide_mcp_files() quietly
    stopped finding anything.
    """
    import shutil

    harness = tmp_path / "harness"
    (harness / "claude" / "mcp" / "project").mkdir(parents=True)
    src = harness / "claude" / "mcp" / "project" / "server.py"
    src.write_text("print('canonical')\n", encoding="utf-8")

    mirror = harness / "someide" / "mcp" / "project"
    mirror.mkdir(parents=True)
    shutil.copyfile(src, mirror / "server.py")

    monkeypatch.setattr(__import__(__name__), "_HARNESS", str(harness))

    canonical = _canonical_files()
    dupes = [rel for _ide, rel, sha in _other_ide_mcp_files() if canonical.get(rel) == sha]
    assert dupes == ["project/server.py"], "the guard failed to see a planted copy"


def test_a_genuinely_different_server_is_allowed(tmp_path, monkeypatch):
    """An IDE may ship its own server — it just may not ship a copy of ours."""
    harness = tmp_path / "harness"
    (harness / "claude" / "mcp" / "project").mkdir(parents=True)
    (harness / "claude" / "mcp" / "project" / "server.py").write_text("A\n", encoding="utf-8")

    other = harness / "someide" / "mcp" / "project"
    other.mkdir(parents=True)
    (other / "server.py").write_text("B — genuinely different\n", encoding="utf-8")

    monkeypatch.setattr(__import__(__name__), "_HARNESS", str(harness))

    canonical = _canonical_files()
    dupes = [rel for _ide, rel, sha in _other_ide_mcp_files() if canonical.get(rel) == sha]
    assert dupes == []
