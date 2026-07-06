"""renar-file-export (Phase 0): one-way sqlite → renar/ derived tree.

Covers determinism / no-spurious-churn (AC-1), stable slug ordering + frontmatter
keys (AC-2), `--check` drift on add/edit/remove (AC-3), deletion reconciliation
(AC-4), and read-only-on-DB + date-free conformance view (AC-5).
"""

from __future__ import annotations

import os
import re
import sys

import pytest

# PyYAML is an OPTIONAL RENAR dependency (see test_no_hard_yaml_import). A clean
# checkout without it should SKIP these tests, not error at collection.
yaml = pytest.importorskip("yaml")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from renar_export import (  # noqa: E402
    assert_export_target,
    build_tree,
    check_tree,
    write_tree,
)


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "export.db")))
    yield s
    s.be.close()


def _seed(svc):
    """Two specs (out-of-order slugs) + one adapt with a body and a link."""
    svc.spec_add("zeta-api", "API", "Zeta API", "1", status="active")
    svc.spec_add("alpha-data", "DATA", "Alpha Data", "2")
    svc.adapt_create("adapt-one", "First ADAPT", "TZ-2026-001")
    svc.adapt_interpret(
        "adapt-one",
        "TZ-2026-001 §1",
        "the system shall authenticate",
        "implement email+password login",
        "login flow",
        "SSO",
    )
    svc.adapt_finding("adapt-one", "gap", "no password-reset described", tz_ref="TZ-2026-001 §1")
    svc.adapt_sign("adapt-one", "client", "Client Rep")
    svc.adapt_link("adapt-one", "spec", "zeta-api")


# --- AC-1 determinism --------------------------------------------------------


def test_build_is_deterministic(svc):
    _seed(svc)
    assert build_tree(svc) == build_tree(svc)


def test_write_then_check_clean(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    assert check_tree(out, build_tree(svc)) == []


def test_rewrite_is_byte_identical(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    spec_path = os.path.join(out, "specs", "zeta-api.md")
    with open(spec_path, encoding="utf-8") as fh:
        first = fh.read()
    write_tree(out, build_tree(svc))  # no DB change
    with open(spec_path, encoding="utf-8") as fh:
        assert fh.read() == first


# --- AC-2 ordering + stable frontmatter --------------------------------------


def test_expected_paths_and_slug_order(svc):
    _seed(svc)
    tree = build_tree(svc)
    assert "README.md" in tree
    assert "conformance.md" in tree
    assert "specs/alpha-data.md" in tree
    assert "specs/zeta-api.md" in tree
    assert "adapts/adapt-one.md" in tree


def test_frontmatter_keys_sorted(svc):
    _seed(svc)
    doc = build_tree(svc)["specs/zeta-api.md"]
    block = doc.split("---\n")[1]
    front = yaml.safe_load(block)
    assert front["artifact"] == "spec"
    assert front["type"] == "API"
    # safe_dump(sort_keys=True): top-level keys appear alphabetically. Match only
    # real key lines (`key:` at column 0) so block-list items (`- x`) and nested
    # mapping lines never pollute the comparison.
    keys = [
        m.group(1) for line in block.splitlines() if (m := re.match(r"^([A-Za-z_][\w-]*):", line))
    ]
    assert keys == sorted(keys)
    assert "type" in keys and "version" in keys


# --- AC-3 --check drift ------------------------------------------------------


def test_check_missing_when_artifact_added(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    svc.spec_add("new-spec", "UI", "New UI", "1")
    drift = check_tree(out, build_tree(svc))
    assert any("missing" in d and "new-spec" in d for d in drift)


def test_check_changed_when_artifact_edited(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    svc.spec_update("zeta-api", status="deprecated")
    drift = check_tree(out, build_tree(svc))
    assert any("changed" in d and "zeta-api" in d for d in drift)


def test_check_stale_when_extra_file(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    with open(os.path.join(out, "specs", "orphan.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nartifact: spec\n---\n")
    drift = check_tree(out, build_tree(svc))
    assert any("stale" in d and "orphan" in d for d in drift)


def test_check_reports_missing_tree(svc, tmp_path):
    _seed(svc)
    drift = check_tree(str(tmp_path / "nope"), build_tree(svc))
    assert drift and "missing tree" in drift[0]


# --- AC-4 deletion reconciliation --------------------------------------------


def test_delete_reconciles_file(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    assert os.path.isfile(os.path.join(out, "specs", "alpha-data.md"))
    svc.spec_delete("alpha-data")
    counts = write_tree(out, build_tree(svc))
    assert counts["deleted"] == 1
    assert not os.path.isfile(os.path.join(out, "specs", "alpha-data.md"))
    assert check_tree(out, build_tree(svc)) == []


# --- AC-5 read-only + date-free conformance ----------------------------------


def test_build_does_not_mutate_db(svc):
    _seed(svc)
    before = (len(svc.spec_list()), len(svc.adapt_list()))
    build_tree(svc)
    build_tree(svc)
    assert (len(svc.spec_list()), len(svc.adapt_list())) == before


def test_conformance_is_date_free(svc):
    _seed(svc)
    doc = build_tree(svc)["conformance.md"]
    front = yaml.safe_load(doc.split("---\n")[1])
    assert front["artifact"] == "conformance"
    assert "assessment-date" not in front
    assert "next-assessment-due" not in front
    assert "manifest-id" not in front
    # adapt-per-tz now satisfied (1 ADAPT) — clause confirmed in the derived view
    assert front["mandatory-clauses-confirmed"]["adapt-per-tz"] is True


def test_adapt_body_rendered(svc):
    _seed(svc)
    doc = build_tree(svc)["adapts/adapt-one.md"]
    assert "## Forward interpretations" in doc
    assert "## Backward findings" in doc
    assert "[gap]" in doc
    front = yaml.safe_load(doc.split("---\n")[1])
    assert front["signatures"][0]["role"] == "client"
    assert front["links"][0]["target_slug"] == "zeta-api"
    # symmetry with spec frontmatter: adapt carries DB timestamps too
    assert "created_at" in front and "updated_at" in front


# --- review fixes: --out guard, empty DB, nested prune -----------------------


def test_empty_db_yields_only_base_files(svc, tmp_path):
    tree = build_tree(svc)  # no specs/adapts seeded
    assert set(tree) == {"README.md", "conformance.md"}
    out = str(tmp_path / "renar")
    write_tree(out, tree)
    assert check_tree(out, build_tree(svc)) == []


def test_out_guard_rejects_outside_root(tmp_path):
    root = str(tmp_path / "proj")
    os.makedirs(root)
    outside = str(tmp_path / "elsewhere")
    with pytest.raises(ValueError):
        assert_export_target(outside, root)


def test_out_guard_rejects_root_itself(tmp_path):
    root = str(tmp_path / "proj")
    os.makedirs(root)
    with pytest.raises(ValueError):
        assert_export_target(root, root)


def test_out_guard_accepts_subdir(tmp_path):
    root = str(tmp_path / "proj")
    os.makedirs(root)
    out = assert_export_target(os.path.join(root, "renar"), root)
    assert out == os.path.abspath(os.path.join(root, "renar"))


def test_out_guard_does_not_delete_on_reject(tmp_path):
    # A rejected target must never reach write_tree's deletion loop.
    root = str(tmp_path / "proj")
    os.makedirs(root)
    victim = tmp_path / "keep.md"
    victim.write_text("important", encoding="utf-8")
    with pytest.raises(ValueError):
        assert_export_target(str(tmp_path), root)
    assert victim.exists()


def test_conformance_excludes_volatile_counts(svc):
    _seed(svc)
    doc = build_tree(svc)["conformance.md"]
    # raw operational counters must NOT leak into the derived view
    assert "raw-counts" not in doc
    assert "verification_runs_count" not in doc
    assert "memory_edges_count" not in doc


def test_operational_activity_does_not_change_conformance(svc):
    """A verify run (unrelated to RENAR artifacts) must not churn the tree."""
    _seed(svc)
    before = build_tree(svc)["conformance.md"]
    # simulate operational activity that bumps a raw counter gather_signals reads
    svc.be._conn.execute(
        "INSERT INTO verification_runs"
        "(task_slug, scope, command, exit_code, files_hash, ran_at)"
        " VALUES (?,?,?,?,?,?)",
        ("zeta-api", "manual", "noop", 0, "deadbeef", "2026-06-14T00:00:00Z"),
    )
    svc.be._conn.commit()
    after = build_tree(svc)["conformance.md"]
    assert after == before


def test_prune_removes_nested_empty_dirs(svc, tmp_path):
    _seed(svc)
    out = str(tmp_path / "renar")
    write_tree(out, build_tree(svc))
    nested = os.path.join(out, "specs", "sub", "deep")
    os.makedirs(nested)
    write_tree(out, build_tree(svc))  # prune pass runs after write
    assert not os.path.exists(os.path.join(out, "specs", "sub"))
    assert os.path.isdir(os.path.join(out, "specs"))  # non-empty dir kept
