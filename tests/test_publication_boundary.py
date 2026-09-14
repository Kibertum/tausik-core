"""One boundary for content that leaves the machine, and the property that keeps it one.

Decision #358 took the Notion transport and, with it, the four places that each
decided "may this leave?" on their own. What remains is `tausik knowledge
export`, and this file pins two things about it: that its `--redacted` form
loses none of the four detectors the old checks relied on (one input per
detector, each redacted ALONE), and that no other module reads the shared store
and writes it somewhere without importing the boundary (convention #354: a
property over the tree, not a list of call sites that rots silently).
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import knowledge_db  # noqa: E402
import knowledge_export as kx  # noqa: E402
import publication_boundary as pb  # noqa: E402

# The property walk reads these trees; a change under either must select this file.
CROSSCUTTING_SCOPE = ["scripts/", "harness/"]

_TS = "2026-09-12T10:00:00Z"


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


# --- redact: one input per detector, each on its own -------------------------


@pytest.mark.parametrize(
    ("content", "kwargs", "detector", "survivor"),
    [
        # the Windows detector lets a filename carry spaces, so the sentence must
        # end the path with punctuation the way real prose does
        ("see C:\\Users\\ann\\secrets\\notes.txt; details follow", {}, "path", "details follow"),
        ("lives at /home/ann/clients/acme/plan.md today", {}, "path", "today"),
        ("ping ann.lee@example.com about it", {}, "email", "ping"),
        (
            "wiki at https://intranet.acme.internal/page/1 says so",
            {"private_url_patterns": [r"acme\.internal"]},
            "url",
            "says so",
        ),
        (
            "built for Acme Corp last spring",
            {"project_names": ["acme corp"]},
            "project",
            "last spring",
        ),
    ],
    ids=["windows-path", "posix-path", "email", "private-url", "project-name"],
)
def test_each_detector_redacts_on_its_own(content, kwargs, detector, survivor):
    result = pb.redact(content, **kwargs)
    assert pb.PLACEHOLDERS[detector] in result.text
    assert survivor in result.text, "the surrounding prose is not collateral"
    assert result.counts[detector] == 1
    assert result.total == 1, f"only the {detector} detector should fire: {result.counts}"


def test_clean_text_is_returned_untouched():
    text = "a plain note about retries and back-off"
    result = pb.redact(text, project_names=["acme"], private_url_patterns=[r"corp\.internal"])
    assert result.text == text
    assert result.total == 0


def test_a_public_url_is_not_a_private_one():
    text = "docs at https://docs.python.org/3/ are public"
    assert pb.redact(text, private_url_patterns=[r"acme\.internal"]).text == text


def test_redact_refuses_a_non_string():
    with pytest.raises(TypeError):
        pb.redact(None)  # type: ignore[arg-type]


# --- export --redacted, and the faithful default ------------------------------


_PRIVATE = (
    "see /home/ann/acme/plan.md, mail ann@example.com, Acme wiki https://wiki.acme.internal/x"
)


def _seed() -> None:
    conn = knowledge_db.connect_knowledge_db(create=True)
    assert conn is not None
    try:
        conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, tags, origin_project, "
            "origin_slug, created_at, updated_at) VALUES (?, 'pattern', ?, ?, ?, ?, ?, ?, ?)",
            ("m1", "retries", _PRIVATE, "a", "proj@0000", "task-x", _TS, _TS),
        )
        conn.execute(
            "INSERT INTO decisions (entry_uuid, decision, rationale, origin_project, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("d1", "keep Acme on SQLite", _PRIVATE, "proj@0000", _TS),
        )
        conn.commit()
    finally:
        conn.close()


def _read(out: Path, rel: str) -> str:
    return (out / rel).read_text(encoding="utf-8")


def test_a_plain_backup_stays_faithful(tmp_path):
    _seed()
    out = tmp_path / "plain"
    counts = kx.export_shared_knowledge(str(out))
    assert "redacted_path" not in counts
    assert _PRIVATE in _read(out, "memory/m1.md")
    assert "redacted: false" in _read(out, "manifest.md").lower()


def test_a_redacted_backup_carries_placeholders_and_says_so(tmp_path):
    _seed()
    out = tmp_path / "travel"
    counts = kx.export_shared_knowledge(
        str(out), redacted=True, project_names=["Acme"], private_url_patterns=[r"acme\.internal"]
    )
    body = _read(out, "memory/m1.md")
    assert (
        "/home/ann" not in body
        and "ann@example.com" not in body
        and "wiki.acme.internal" not in body
    )
    for token in ("path", "email", "url", "project"):
        assert pb.PLACEHOLDERS[token] in body, token
    manifest = _read(out, "manifest.md").lower()
    assert "redacted: true" in manifest
    assert counts["redacted_path"] >= 2 and counts["redacted_email"] >= 2
    assert "m1" in body, "identity is not text to redact"


def test_restoring_a_redacted_backup_never_overwrites_a_live_row(tmp_path):
    _seed()
    out = tmp_path / "travel"
    kx.export_shared_knowledge(str(out), redacted=True, project_names=["Acme"])
    kx.restore_shared_knowledge(str(out))  # same uuids already present
    conn = knowledge_db.connect_knowledge_db(create=False)
    assert conn is not None
    try:
        (content,) = conn.execute("SELECT content FROM memory WHERE entry_uuid='m1'").fetchone()
    finally:
        conn.close()
    assert content == _PRIVATE, "ON CONFLICT DO NOTHING must keep the faithful row"


def test_restoring_a_redacted_backup_into_an_empty_store_keeps_the_placeholders(
    tmp_path, monkeypatch
):
    _seed()
    out = tmp_path / "travel"
    kx.export_shared_knowledge(str(out), redacted=True, project_names=["Acme"])
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "other-home"))
    kx.restore_shared_knowledge(str(out))
    conn = knowledge_db.connect_knowledge_db(create=False)
    assert conn is not None
    try:
        (content,) = conn.execute("SELECT content FROM memory WHERE entry_uuid='m1'").fetchone()
    finally:
        conn.close()
    assert pb.PLACEHOLDERS["path"] in content and "/home/ann" not in content


# --- the property: every store reader that writes outward imports the boundary --


_STORE_READERS = {"knowledge_db", "connect_knowledge_db"}
_OUTWARD_WRITE_ATTRS = {"write_text", "write_bytes", "urlopen", "copy", "copy2", "copyfile", "move"}
_OUTWARD_WRITE_NAMES = {"open"}

# Every exception carries its reason, and every entry must be EXERCISED: an
# allowlisted module that no longer trips the walk is a hole waiting for the day
# it writes outward again, so a stale entry fails the suite (test below).
# Empty today — the only store reader that writes files is the exporter, and it
# imports the boundary.
ALLOWLIST: dict[str, str] = {}


def _writes_outward(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id in _OUTWARD_WRITE_NAMES:
            modes = [a for a in node.args[1:2]] + [
                k.value for k in node.keywords if k.arg == "mode"
            ]
            for m in modes:
                if (
                    isinstance(m, ast.Constant)
                    and isinstance(m.value, str)
                    and any(c in m.value for c in "wax")
                ):
                    return True
        if isinstance(fn, ast.Attribute) and fn.attr in _OUTWARD_WRITE_ATTRS:
            return True
    return False


def _reads_store(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name.split(".")[0] in _STORE_READERS for a in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in _STORE_READERS:
            return True
        if isinstance(node, ast.ImportFrom) and any(a.name in _STORE_READERS for a in node.names):
            return True
    return False


def _imports_boundary(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name == "publication_boundary" for a in node.names
        ):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == "publication_boundary":
            return True
    return False


def _modules():
    for root in (_SCRIPTS, _REPO / "harness"):
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


def _walk() -> tuple[int, list[str], set[str]]:
    """(store readers scanned, offenders, allowlist entries that were needed)."""
    scanned = 0
    offenders: list[str] = []
    exercised: set[str] = set()
    for path in _modules():
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        if not _reads_store(tree):
            continue
        scanned += 1
        if not _writes_outward(tree) or _imports_boundary(tree):
            continue
        if path.stem in ALLOWLIST:
            exercised.add(path.stem)
            continue
        offenders.append(os.path.relpath(path, _REPO))
    return scanned, offenders, exercised


def test_every_store_reader_that_writes_outward_passes_the_boundary():
    scanned, offenders, _ = _walk()
    assert scanned >= 5, f"the walk found only {scanned} store readers — vacuous"
    assert not offenders, (
        f"these modules read the shared store and write files or the network without "
        f"publication_boundary: {offenders}. Route the write through the boundary, or add "
        f"the module to ALLOWLIST with its reason."
    )


def test_every_allowlist_entry_is_still_needed():
    _, _, exercised = _walk()
    stale = sorted(set(ALLOWLIST) - exercised)
    assert not stale, f"ALLOWLIST entries no longer needed — remove them, they hide the next leak: {stale}"


def test_the_exporter_itself_imports_the_boundary():
    tree = ast.parse((_SCRIPTS / "knowledge_export.py").read_text(encoding="utf-8"))
    assert _imports_boundary(tree)
