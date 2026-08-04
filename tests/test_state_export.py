"""state-git-export: deterministic DB → tausik/ git-native projection.

Covers the eight acceptance criteria: byte-determinism + normalization (LF, one
trailing \\n, fixed frontmatter key order, tags alphabetical, edges by
(relation,target_type,target), ordered-list dedup, ISO-8601 Z dates, explicit
null, YAML-quoting of ambiguous scalars), completeness (every durable field
serialized, runtime/telemetry fields excluded), idempotency (re-export is a
no-op), stable-slug filenames + edge keys, the slug-less refusal, machine-order
invariance (shuffled DB rows → identical bytes), and the CLI writing under
tausik/.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from state_export import ENTITY_DIRS, ExportError, build_tree  # noqa: E402
from state_serialize import (  # noqa: E402
    check_tree,
    normalize_ts,
    render_file,
    scalar,
    write_tree,
)


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "state.db")))
    yield s
    s.be.close()


# --- seeding helpers ---------------------------------------------------------


def _seed_hierarchy(svc):
    svc.epic_add("team-state", "Team state in git")
    svc.story_add("team-state", "mvp", "State in branch MVP")
    svc.task_add("mvp", "exp", "Export task", stack="python", complexity="complex", goal="g")


def _log(svc, slug, msg, ts, phase=None):
    svc.be._ex(
        "INSERT INTO task_logs(task_slug, message, phase, created_at) VALUES(?,?,?,?)",
        (slug, msg, phase, ts),
    )


# --- AC-1 / AC-3: determinism + idempotency ----------------------------------


def test_export_is_deterministic_across_two_builds(svc):
    _seed_hierarchy(svc)
    tree_a, _ = build_tree(svc)
    tree_b, _ = build_tree(svc)
    assert tree_a == tree_b


def test_export_idempotent_write_then_check_clean(svc, tmp_path):
    _seed_hierarchy(svc)
    out = str(tmp_path / "tausik")
    tree, _ = build_tree(svc)
    write_tree(out, tree)
    assert check_tree(out, tree) == []  # second look sees no drift
    # re-write must not change a single byte
    before = _read_all(out)
    write_tree(out, tree)
    assert _read_all(out) == before


def _read_all(root):
    snap = {}
    for dp, _d, files in os.walk(root):
        for f in files:
            p = os.path.join(dp, f)
            with open(p, "rb") as fh:
                snap[os.path.relpath(p, root)] = fh.read()
    return snap


# --- AC-1 normalization details ----------------------------------------------


def test_lf_only_and_single_trailing_newline(svc):
    _seed_hierarchy(svc)
    tree, _ = build_tree(svc)
    for path, content in tree.items():
        assert "\r" not in content, f"{path} has CR"
        assert content.endswith("\n") and not content.endswith("\n\n"), path


def test_fixed_frontmatter_key_order_for_task(svc):
    _seed_hierarchy(svc)
    tree, _ = build_tree(svc)
    fm = tree["tasks/exp.md"].split("---\n")[1]
    keys = [ln.split(":", 1)[0] for ln in fm.splitlines() if ln and not ln.startswith(" ")]
    assert keys == [
        "slug",
        "title",
        "status",
        "epic",
        "story",
        "complexity",
        "role",
        "stack",
        "tier",
        "call_budget",
        "defect_of",
        "scope",
        "scope_exclude",
        "relevant_files",
        "scope_paths",
        "scope_tools",
        "completed_at",
    ]


def test_tags_sorted_alphabetically(svc):
    _seed_hierarchy(svc)
    svc.be.memory_add("pattern", "Mem one", "body", ["zeta", "alpha", "mu"], "exp")
    tree, _ = build_tree(svc)
    mem = next(v for k, v in tree.items() if k.startswith("memory/"))
    tags_block = mem.split("tags:\n", 1)[1]
    order = [ln.strip("- ").strip() for ln in tags_block.splitlines() if ln.startswith("  - ")]
    assert order == ["alpha", "mu", "zeta"]


def test_edges_sorted_and_target_is_slug(svc):
    _seed_hierarchy(svc)
    a = svc.be.memory_add("pattern", "Aaa mem", "a", None, "exp")
    b = svc.be.memory_add("gotcha", "Bbb mem", "b", None, "exp")
    d = svc.be.decision_add("Ddd decision", "exp", "why")
    # two outgoing edges from A, deliberately added out of sorted order
    svc.be.edge_add("memory", a, "decision", d, "relates_to")
    svc.be.edge_add("memory", a, "memory", b, "caused_by")
    tree, warnings = build_tree(svc)
    assert warnings == []
    a_slug = next(k for k in tree if k.startswith("memory/aaa"))
    block = tree[a_slug].split("edges:\n", 1)[1]
    rels = [ln.split(":", 1)[1].strip() for ln in block.splitlines() if "relation:" in ln]
    assert rels == ["caused_by", "relates_to"]  # sorted by (relation, ...)
    assert "target: bbb-mem" in tree[a_slug]
    assert "target: ddd-decision" in tree[a_slug]


def test_dates_normalized_to_z_without_micros(svc):
    _seed_hierarchy(svc)
    svc.be.task_update("exp", completed_at="2026-07-24 15:00:00.123456")
    tree, _ = build_tree(svc)
    # A date string is quoted (contract point 6) so YAML never coerces it to a
    # timestamp type — normalized to Z, microseconds dropped.
    assert 'completed_at: "2026-07-24T15:00:00Z"' in tree["tasks/exp.md"]


def test_null_fields_explicit(svc):
    _seed_hierarchy(svc)
    tree, _ = build_tree(svc)
    assert "defect_of: null" in tree["tasks/exp.md"]
    assert "completed_at: null" in tree["tasks/exp.md"]


def test_ambiguous_scalars_quoted():
    assert scalar("2026-01") == '"2026-01"'  # would parse as a date
    assert scalar("on") == '"on"'  # YAML bool
    assert scalar("true") == '"true"'
    assert scalar("123") == '"123"'  # leading digit → not a plain token
    assert scalar("state-git-export") == "state-git-export"  # clean slug → plain
    assert scalar("planning") == "planning"
    assert scalar(None) == "null"
    assert scalar(42) == "42"


def test_ordered_list_dedup_preserves_declared_order(svc):
    _seed_hierarchy(svc)
    svc.be.task_update("exp", scope_paths='["b.py", "a.py", "b.py", "c.py"]')
    tree, _ = build_tree(svc)
    block = tree["tasks/exp.md"].split("scope_paths:\n", 1)[1]
    order = [ln.strip("- ").strip() for ln in block.splitlines() if ln.startswith("  - ")]
    assert order == ["b.py", "a.py", "c.py"]  # order kept, duplicate 'b.py' removed


# --- AC-2: completeness ------------------------------------------------------


def test_all_durable_fields_serialized_runtime_excluded(svc):
    _seed_hierarchy(svc)
    svc.be.task_update(
        "exp",
        plan="the plan",
        acceptance_criteria="the ac",
        rollback_plan="git revert",
        scope="scripts/x.py",
        scope_exclude="tests/",
        scope_paths='["scripts/x.py"]',
        scope_tools='["Write"]',
        relevant_files='["scripts/x.py"]',
        call_budget=120,
        tier="substantial",
        completed_at="2026-07-24T15:00:00Z",
        # runtime/telemetry — must NOT appear in the file:
        risk_score=0.9,
        attempts=3,
        started_at="2026-07-01T00:00:00Z",
        claimed_by="agent-x",
    )
    _log(svc, "exp", "did a thing", "2026-07-24T15:10:00Z", phase="implementation")
    tree, _ = build_tree(svc)
    doc = tree["tasks/exp.md"]
    for durable in (
        "the plan",
        "the ac",
        "git revert",
        "scripts/x.py",
        "Write",
        "120",
        "substantial",
    ):
        assert durable in doc, durable
    assert "## Journal" in doc and "did a thing" in doc and "[implementation]" in doc
    for runtime in ("risk_score", "attempts", "claimed_by", "started_at", "agent-x", "0.9"):
        assert runtime not in doc, runtime


def test_journal_line_format(svc):
    _seed_hierarchy(svc)
    _log(svc, "exp", "no phase entry", "2026-07-24T15:00:00Z")
    _log(svc, "exp", "phased entry", "2026-07-24T15:05:00Z", phase="review")
    tree, _ = build_tree(svc)
    doc = tree["tasks/exp.md"]
    assert "- 2026-07-24T15:00:00Z — no phase entry" in doc
    assert "- 2026-07-24T15:05:00Z [review] — phased entry" in doc


# --- AC-4 layout -------------------------------------------------------------


def test_layout_paths_use_slugs(svc):
    _seed_hierarchy(svc)
    svc.be.memory_add("pattern", "Some mem", "x", None, "exp")
    svc.be.decision_add("A decision", "exp", None)
    tree, _ = build_tree(svc)
    assert "epics/team-state.md" in tree
    assert "stories/mvp.md" in tree
    assert "tasks/exp.md" in tree
    assert "memory/some-mem.md" in tree
    assert "decisions/a-decision.md" in tree


# --- AC-5 negative: slug-less refusal ----------------------------------------


def test_slugless_decision_refuses_with_migration_hint(svc):
    _seed_hierarchy(svc)
    svc.be._ex(
        "INSERT INTO decisions(decision, created_at, slug) VALUES(?,?,NULL)",
        ("orphan decision", "2026-01-01T00:00:00Z"),
    )
    with pytest.raises(ExportError) as exc:
        build_tree(svc)
    assert "state-git-stable-ids" in str(exc.value)


def test_slugless_memory_refuses(svc):
    _seed_hierarchy(svc)
    svc.be._ex(
        "INSERT INTO memory(type, title, content, created_at, updated_at, slug) "
        "VALUES('pattern','t','c','2026-01-01T00:00:00Z','2026-01-01T00:00:00Z',NULL)",
    )
    with pytest.raises(ExportError):
        build_tree(svc)


# --- AC-6 negative/boundary: machine-order invariance ------------------------


def _seed_variant(svc, mem_titles, log_order):
    """Same logical content, inserted in a caller-chosen order (→ different ids)."""
    _seed_hierarchy(svc)
    ids = {}
    for t in mem_titles:
        ids[t] = svc.be.memory_add("pattern", t, f"body-{t}", None, "exp")
    # a stable edge regardless of insertion order: Aaa → Bbb
    svc.be.edge_add("memory", ids["Aaa"], "memory", ids["Bbb"], "relates_to")
    for msg, ts, phase in log_order:
        _log(svc, "exp", msg, ts, phase)


def test_shuffled_row_order_yields_identical_bytes(tmp_path):
    s1 = ProjectService(SQLiteBackend(str(tmp_path / "a.db")))
    s2 = ProjectService(SQLiteBackend(str(tmp_path / "b.db")))
    try:
        # same two logs on the SAME timestamp — the content tiebreak must be
        # machine-independent, so insertion order cannot change the bytes.
        logs = [
            ("bbb log", "2026-07-24T15:00:00Z", None),
            ("aaa log", "2026-07-24T15:00:00Z", None),
        ]
        _seed_variant(s1, ["Aaa", "Bbb", "Ccc"], logs)
        _seed_variant(s2, ["Ccc", "Bbb", "Aaa"], list(reversed(logs)))
        t1, _ = build_tree(s1)
        t2, _ = build_tree(s2)
        assert t1 == t2
    finally:
        s1.be.close()
        s2.be.close()


# --- edge integrity ----------------------------------------------------------


def test_dangling_edge_dropped_with_warning_not_silently(svc):
    _seed_hierarchy(svc)
    a = svc.be.memory_add("pattern", "Aaa mem", "a", None, "exp")
    svc.be.edge_add("memory", a, "memory", 9999, "relates_to")  # target does not exist
    tree, warnings = build_tree(svc)
    assert any("dangling edge" in w for w in warnings)
    a_doc = next(v for k, v in tree.items() if k.startswith("memory/aaa"))
    assert "edges: []" in a_doc  # dropped, not fabricated


def test_invalidated_edge_excluded(svc):
    _seed_hierarchy(svc)
    a = svc.be.memory_add("pattern", "Aaa mem", "a", None, "exp")
    b = svc.be.memory_add("gotcha", "Bbb mem", "b", None, "exp")
    eid = svc.be.edge_add("memory", a, "memory", b, "relates_to")
    svc.be.edge_invalidate(eid)
    tree, _ = build_tree(svc)
    a_doc = next(v for k, v in tree.items() if k.startswith("memory/aaa"))
    assert "edges: []" in a_doc


def test_archived_memory_excluded(svc):
    _seed_hierarchy(svc)
    svc.be.memory_add("pattern", "Live mem", "x", None, "exp")
    arch = svc.be.memory_add("pattern", "Dead mem", "y", None, "exp")
    svc.be.memory_archive_ids([arch])
    tree, _ = build_tree(svc)
    assert any(k.startswith("memory/live-mem") for k in tree)
    assert not any(k.startswith("memory/dead-mem") for k in tree)


# --- normalize_ts unit -------------------------------------------------------


def test_normalize_ts_forms():
    assert normalize_ts("2026-07-24T15:00:00Z") == "2026-07-24T15:00:00Z"
    assert normalize_ts("2026-07-24 15:00:00") == "2026-07-24T15:00:00Z"
    assert normalize_ts("2026-07-24T15:00:00.123456Z") == "2026-07-24T15:00:00Z"
    assert normalize_ts("2026-07-24T18:00:00+03:00") == "2026-07-24T15:00:00Z"
    assert normalize_ts(None) is None
    assert normalize_ts("") is None


def test_render_file_empty_body_no_trailing_blank():
    out = render_file([("slug", "x"), ("status", "done")], None)
    assert out == "---\nslug: x\nstatus: done\n---\n"


# --- adversarial: emitter robustness vs YAML injection / type coercion --------


def _frontmatter_of(doc: str) -> dict:
    """Parse the frontmatter block of an exported file with a real YAML parser."""
    import yaml

    fm = doc.split("---\n", 2)[1]
    return yaml.safe_load(fm)


def test_frontmatter_always_valid_yaml(svc):
    _seed_hierarchy(svc)
    svc.be.memory_add("pattern", "Mem: with colon", "c", ["b", "a"], "exp")
    svc.be.decision_add("Decision — with dash", "exp", "why")
    tree, _ = build_tree(svc)
    for path, doc in tree.items():
        fm = _frontmatter_of(doc)
        assert isinstance(fm, dict), f"{path} frontmatter is not a mapping"
        assert "slug" in fm


def test_adversarial_title_newline_and_fence_does_not_break_structure(svc):
    _seed_hierarchy(svc)
    # Directly poke unsanitized values into the DB (defense in depth): a title
    # with a newline + a fake `---` fence, a body with a fence and a fake heading.
    svc.be._ex(
        "UPDATE tasks SET title=?, goal=? WHERE slug='exp'",
        ("line1\nline2 --- x", "goal body\n---\nafter fence\n## Journal\nfake row"),
    )
    tree, _ = build_tree(svc)
    fm = _frontmatter_of(tree["tasks/exp.md"])
    # newline is escaped inside a quoted scalar → title survives verbatim, and the
    # frontmatter stays a single valid mapping (the embedded `---` did not split it)
    assert fm["title"] == "line1\nline2 --- x"
    assert fm["status"] == "planning"


def test_ambiguous_values_stay_strings_under_real_yaml(svc):
    _seed_hierarchy(svc)
    # tags a YAML parser would love to coerce: a date, a bool, a number.
    svc.be.memory_add("pattern", "Coercion mem", "c", ["2026-01", "on", "007"], "exp")
    svc.be.task_update("exp", completed_at="2026-07-24T15:00:00Z")
    tree, _ = build_tree(svc)
    mem = next(v for k, v in tree.items() if k.startswith("memory/coercion"))
    fm = _frontmatter_of(mem)
    assert fm["tags"] == ["007", "2026-01", "on"]  # alpha-sorted, all strings not date/bool/int
    assert all(isinstance(t, str) for t in fm["tags"])
    task_fm = _frontmatter_of(tree["tasks/exp.md"])
    assert task_fm["completed_at"] == "2026-07-24T15:00:00Z"  # str, not a datetime
    assert isinstance(task_fm["completed_at"], str)


# --- review fixes: CRLF drift, deletion scoping, memory title, YAML-1.1 --------


def test_check_tree_detects_crlf_corruption(svc, tmp_path):
    """A teammate re-saving a file with CRLF must NOT pass --check (contract #1)."""
    _seed_hierarchy(svc)
    out = str(tmp_path / "tausik")
    tree, _ = build_tree(svc)
    write_tree(out, tree, managed_dirs=ENTITY_DIRS)
    assert check_tree(out, tree, managed_dirs=ENTITY_DIRS) == []
    p = os.path.join(out, "tasks", "exp.md")
    with open(p, "rb") as fh:
        data = fh.read()
    with open(p, "wb") as fh:
        fh.write(data.replace(b"\n", b"\r\n"))  # CRLF corruption
    drift = check_tree(out, tree, managed_dirs=ENTITY_DIRS)
    assert any(d.startswith("changed: tasks/exp.md") for d in drift), drift


def test_write_tree_preserves_non_entity_files(svc, tmp_path):
    """A hand-written tausik/README.md (or a non-entity dir) is never swept."""
    _seed_hierarchy(svc)
    out = tmp_path / "tausik"
    tree, _ = build_tree(svc)
    write_tree(str(out), tree, managed_dirs=ENTITY_DIRS)
    readme = out / "README.md"
    readme.write_text("hand-written", encoding="utf-8")
    (out / "notes").mkdir()
    note = out / "notes" / "conventions.md"
    note.write_text("mine", encoding="utf-8")
    counts = write_tree(str(out), tree, managed_dirs=ENTITY_DIRS)
    assert readme.exists() and note.exists()
    assert counts["deleted"] == 0


def test_write_tree_reports_deleted_paths_not_silently(svc, tmp_path):
    """A stale file inside an owned dir is removed but RETURNED (announced)."""
    _seed_hierarchy(svc)
    out = tmp_path / "tausik"
    tree, _ = build_tree(svc)
    write_tree(str(out), tree, managed_dirs=ENTITY_DIRS)
    stale = out / "tasks" / "ghost.md"
    stale.write_text("---\nslug: ghost\n---\n", encoding="utf-8")
    counts = write_tree(str(out), tree, managed_dirs=ENTITY_DIRS)
    assert "tasks/ghost.md" in counts["deleted_paths"]
    assert not stale.exists()


def test_memory_title_serialized_and_roundtrippable(svc):
    _seed_hierarchy(svc)
    svc.be.memory_add("pattern", "Bug: DB locks (Windows)", "the body", None, "exp")
    tree, _ = build_tree(svc)
    mem = next(v for k, v in tree.items() if k.startswith("memory/"))
    fm = _frontmatter_of(mem)
    assert fm["title"] == "Bug: DB locks (Windows)"  # exact, not the lossy slug


def test_yaml11_reserved_tokens_quoted():
    import yaml

    for t in ("y", "n", "yes", "no", "on", "off", "inf", "nan", "true", "false"):
        assert scalar(t) == f'"{t}"', t
        assert yaml.safe_load(scalar(t)) == t  # stays a string under a real parser


def test_duplicate_edges_collapsed(svc):
    _seed_hierarchy(svc)
    a = svc.be.memory_add("pattern", "Aaa mem", "a", None, "exp")
    b = svc.be.memory_add("gotcha", "Bbb mem", "b", None, "exp")
    svc.be.edge_add("memory", a, "memory", b, "relates_to")
    svc.be.edge_add("memory", a, "memory", b, "relates_to")  # logical duplicate
    tree, _ = build_tree(svc)
    a_doc = next(v for k, v in tree.items() if k.startswith("memory/aaa"))
    assert a_doc.count("target: bbb-mem") == 1


# --- AC-7: CLI writes the tree under tausik/ ---------------------------------


def test_cli_state_export_writes_tree(tmp_path):
    """`tausik state export --out <dir>` end-to-end via subprocess."""
    db_dir = tmp_path / "proj"
    (db_dir / ".tausik").mkdir(parents=True)
    svc = ProjectService(SQLiteBackend(str(db_dir / ".tausik" / "tausik.db")))
    try:
        _seed_hierarchy(svc)
    finally:
        svc.be.close()

    scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    out_dir = db_dir / "tausik"
    env = {**os.environ, "TAUSIK_SKIP_HOOKS": "1"}
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(scripts, "project.py"),
            "state",
            "export",
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(db_dir),
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out_dir / "tasks" / "exp.md").is_file()
    assert (out_dir / "epics" / "team-state.md").is_file()
