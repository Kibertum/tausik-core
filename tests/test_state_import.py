"""state-git-import: idempotent DB-cache rebuild from the git-native tree.

The strongest round-trip pin (AC-1): re-exporting the DB that `import_tree` built
from a tree must yield a tree byte-identical to the original. Because `state_export`
is deterministic and emits exactly the durable fields, tree-equality proves the
import preserved every entity, durable field, edge and journal line. Plus:
idempotency (AC-2), delta (AC-3), git-wins-but-loud (AC-4), FTS reindex (AC-5),
malformed-file whole-batch abort (AC-6), body-heading grammar (AC-7), CLI (AC-8).
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import ENTITY_DIRS, build_tree  # noqa: E402
from state_import import import_tree  # noqa: E402
from state_parse import (  # noqa: E402
    ParseError,
    parse_frontmatter,
    parse_journal,
    parse_sections,
    split_file,
)
from state_serialize import write_tree  # noqa: E402


def _svc(path):
    return ProjectService(SQLiteBackend(str(path)))


def _seed_rich(svc):
    """A DB exercising every entity type, all field kinds, edges and a journal."""
    svc.epic_add("team-state", "Состояние в git")
    svc.story_add("team-state", "mvp", "MVP в ветке")
    svc.task_add(
        "mvp",
        "exp",
        "Экспорт: сериализатор",
        stack="python",
        complexity="complex",
        goal="Цель",
        role="developer",
    )
    svc.be.task_update(
        "exp",
        plan="План\n\nмного строк",
        acceptance_criteria="AC",
        rollback_plan="revert",
        scope="scripts/x.py",
        scope_exclude="tests/",
        scope_paths='["b.py", "a.py"]',
        scope_tools='["Write"]',
        relevant_files='["scripts/x.py"]',
        call_budget=120,
        tier="substantial",
        completed_at="2026-07-24T15:00:00Z",
        status="done",
    )
    svc.be._ex(
        "INSERT INTO task_logs(task_slug, message, phase, created_at) VALUES(?,?,?,?)",
        ("exp", "первый шаг", "implementation", "2026-07-24T15:10:00Z"),
    )
    svc.be._ex(
        "INSERT INTO task_logs(task_slug, message, phase, created_at) VALUES(?,?,?,?)",
        ("exp", "без фазы", None, "2026-07-24T15:20:00Z"),
    )
    a = svc.be.memory_add("pattern", "Память альфа", "тело A", ["git", "state"], "exp")
    b = svc.be.memory_add("gotcha", "Память бета", "тело B", None, "exp")
    d = svc.be.decision_add("Решение первое", "exp", "обоснование")
    svc.be.edge_add("memory", a, "memory", b, "relates_to")
    svc.be.edge_add("memory", a, "decision", d, "caused_by")
    return svc


def test_round_trip_reexport_is_byte_identical(tmp_path):
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))

    dst = _svc(tmp_path / "dst.db")
    try:
        report = import_tree(dst, out)
        assert report["added"], "import should have inserted entities"
        # THE PIN: re-export the imported DB → identical tree (durable fields,
        # edges and journal all preserved).
        tree2, _ = build_tree(dst)
        assert tree2 == tree
    finally:
        dst.be.close()


def test_duplicate_journal_lines_roundtrip_as_multiset(tmp_path):
    """Two genuinely-identical log rows (same ts+msg+phase) must BOTH survive."""
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        for _ in range(2):  # a real DB can hold two identical log lines
            src.be._ex(
                "INSERT INTO task_logs(task_slug, message, phase, created_at) VALUES(?,?,?,?)",
                ("exp", "same line", "review", "2026-07-24T16:00:00Z"),
            )
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    dst = _svc(tmp_path / "dst.db")
    try:
        import_tree(dst, out)
        n = dst.be._q1(
            "SELECT COUNT(*) c FROM task_logs WHERE task_slug='exp' AND message='same line'"
        )["c"]
        assert n == 2  # multiset preserved, not collapsed to 1
        # and re-export is byte-identical (both lines present)
        tree2, _ = build_tree(dst)
        assert tree2 == tree
    finally:
        dst.be.close()


def test_import_is_idempotent(tmp_path):
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    dst = _svc(tmp_path / "dst.db")
    try:
        import_tree(dst, out)
        second = import_tree(dst, out)  # no file changed
        assert second["added"] == []
        assert second["updated"] == []
        assert second["journal"] == []
        assert second.get("edges", []) == []
    finally:
        dst.be.close()


def test_delta_only_changed_entity_written(tmp_path):
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    dst = _svc(tmp_path / "dst.db")
    try:
        import_tree(dst, out)
        # edit ONE file on disk (title of the epic)
        p = os.path.join(out, "epics", "team-state.md")
        with open(p, encoding="utf-8", newline="") as fh:
            content = fh.read()
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content.replace("Состояние в git", "Состояние в git (edited)"))
        report = import_tree(dst, out)
        assert report["updated"] == ["epics/team-state"]
        assert report["added"] == []
    finally:
        dst.be.close()


def test_git_wins_but_reports_overwrite(tmp_path):
    """A locally-diverged DB row is overwritten by the file, and REPORTED."""
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    dst = _svc(tmp_path / "dst.db")
    try:
        import_tree(dst, out)
        dst.be.task_update("exp", goal="LOCAL uncommitted edit")  # diverge DB from file
        report = import_tree(dst, out)  # file wins
        assert "tasks/exp" in report["updated"]
        row = dst.be._q1("SELECT goal FROM tasks WHERE slug='exp'")
        assert row["goal"] == "Цель"  # file value restored, not silently kept
    finally:
        dst.be.close()


def test_dry_run_writes_nothing(tmp_path):
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    dst = _svc(tmp_path / "dst.db")
    try:
        report = import_tree(dst, out, dry=True)
        assert report["added"], "dry-run still computes the plan"
        assert dst.be._q1("SELECT COUNT(*) c FROM tasks")["c"] == 0  # but wrote nothing
    finally:
        dst.be.close()


def test_malformed_file_aborts_whole_batch(tmp_path):
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    # corrupt one file: strip the closing fence
    p = os.path.join(out, "memory", os.listdir(os.path.join(out, "memory"))[0])
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("---\nslug: broken\n(no closing fence)\n")
    dst = _svc(tmp_path / "dst.db")
    try:
        with pytest.raises(ParseError):
            import_tree(dst, out)
        # transactional: nothing partially written
        assert dst.be._q1("SELECT COUNT(*) c FROM epics")["c"] == 0
    finally:
        dst.be.close()


def test_fts_reindexed_after_import(tmp_path):
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    out = str(tmp_path / "tausik")
    write_tree(out, tree, managed_dirs=set(ENTITY_DIRS))
    dst = _svc(tmp_path / "dst.db")
    try:
        import_tree(dst, out)
        hits = dst.be.memory_search("альфа")
        assert any("альфа" in (h.get("title", "") + h.get("content", "")).lower() for h in hits)
    finally:
        dst.be.close()


def test_body_heading_in_prose_does_not_forge_journal(tmp_path):
    """A `## Journal` inside Plan prose is NOT parsed as a journal entry (AC-7)."""
    src = _seed_rich(_svc(tmp_path / "src.db"))
    try:
        src.be.task_update(
            "exp",
            plan="normal plan text\n\n## Journal\n\n- 2020-01-01T00:00:00Z — FORGED entry",
        )
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    doc = tree["tasks/exp.md"]
    _fm, body = split_file(doc)
    secs = parse_sections(body, ["Goal", "Acceptance Criteria", "Plan", "Rollback", "Journal"])
    # the forged line lives in Plan, not the real Journal
    assert "FORGED" in secs["Plan"]
    real = parse_journal(secs["Journal"])
    assert all("FORGED" not in r["message"] for r in real)
    assert any(r["message"] == "первый шаг" for r in real)


# --- state_parse units -------------------------------------------------------


def test_parse_scalar_and_frontmatter_roundtrip():
    from state_serialize import frontmatter

    fm = frontmatter(
        [
            ("slug", "s1"),
            ("title", "Тест: два — тире"),
            ("call_budget", 120),
            ("defect_of", None),
            ("tags", ["b", "a"]),
            ("scope_tools", []),
            (
                "edges",
                [[("relation", "relates_to"), ("target_type", "decision"), ("target", "x-y")]],
            ),
        ]
    )
    d = parse_frontmatter(fm)
    assert d["slug"] == "s1"
    assert d["title"] == "Тест: два — тире"
    assert d["call_budget"] == 120 and isinstance(d["call_budget"], int)
    assert d["defect_of"] is None
    assert d["tags"] == ["b", "a"]
    assert d["scope_tools"] == []
    assert d["edges"] == [{"relation": "relates_to", "target_type": "decision", "target": "x-y"}]


# --- AC-8 CLI ----------------------------------------------------------------


def test_cli_state_import_roundtrip(tmp_path):
    proj = tmp_path / "proj"
    (proj / ".tausik").mkdir(parents=True)
    src = _svc(proj / ".tausik" / "tausik.db")
    try:
        _seed_rich(src)
        tree, _ = build_tree(src)
    finally:
        src.be.close()
    write_tree(str(proj / "tausik"), tree, managed_dirs=set(ENTITY_DIRS))
    # wipe the DB, then rebuild it from the tree via the CLI
    os.remove(proj / ".tausik" / "tausik.db")
    scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    env = {**os.environ, "TAUSIK_SKIP_HOOKS": "1"}
    proc = subprocess.run(
        [sys.executable, os.path.join(scripts, "project.py"), "state", "import"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(proj),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    chk = _svc(proj / ".tausik" / "tausik.db")
    try:
        assert chk.be._q1("SELECT COUNT(*) c FROM tasks")["c"] == 1
        assert chk.be._q1("SELECT slug FROM tasks WHERE slug='exp'") is not None
    finally:
        chk.be.close()
