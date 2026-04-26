"""Tests for service_roles — hybrid SQLite + markdown CRUD."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import service_roles as _r
from project_backend import SQLiteBackend
from tausik_utils import ServiceError


@pytest.fixture
def be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "roles.db"))
    yield b
    b.close()


@pytest.fixture
def isolate_profiles(tmp_path, monkeypatch):
    """Redirect _profile_path_source to tmp so tests don't touch real agents/."""
    fake_repo = tmp_path / "repo"
    (fake_repo / "agents" / "roles").mkdir(parents=True)
    monkeypatch.setattr(_r, "_repo_root", lambda: str(fake_repo))
    monkeypatch.chdir(tmp_path)
    return fake_repo


class TestRoleCRUD:
    def test_create_inserts_row_and_creates_skeleton(self, be, isolate_profiles):
        row = _r.role_create(be, "developer", "Developer")
        assert row["slug"] == "developer"
        assert row["title"] == "Developer"
        user_path = _r._profile_path_user("developer")
        assert os.path.isfile(user_path)
        with open(user_path) as f:
            assert "Developer" in f.read()

    def test_create_duplicate_raises(self, be, isolate_profiles):
        _r.role_create(be, "qa", "QA")
        with pytest.raises(ServiceError):
            _r.role_create(be, "qa", "QA again")

    def test_create_with_extends_clones_profile(self, be, isolate_profiles):
        _r.role_create(be, "dev", "Developer")
        with open(_r._profile_path_user("dev"), "w", encoding="utf-8") as f:
            f.write("# Role: Developer\n\nFancy parent body.\n")
        _r.role_create(be, "dev2", "Developer Jr", extends="dev")
        with open(_r._profile_path_user("dev2")) as f:
            assert "Fancy parent body" in f.read()

    def test_show_returns_metadata_and_profile(self, be, isolate_profiles):
        _r.role_create(be, "qa", "QA")
        row = _r.role_show(be, "qa")
        assert row["title"] == "QA"
        assert row["task_count"] == 0
        assert row["profile"] is not None

    def test_show_unknown_raises(self, be, isolate_profiles):
        with pytest.raises(ServiceError):
            _r.role_show(be, "ghost")

    def test_update_changes_metadata(self, be, isolate_profiles):
        _r.role_create(be, "qa", "QA")
        _r.role_update(be, "qa", title="Quality Assurance", description="QA tier")
        row = _r.role_show(be, "qa")
        assert row["title"] == "Quality Assurance"
        assert row["description"] == "QA tier"

    def test_update_unknown_raises(self, be, isolate_profiles):
        with pytest.raises(ServiceError):
            _r.role_update(be, "ghost", title="X")

    def test_list_includes_task_count(self, be, isolate_profiles):
        _r.role_create(be, "developer", "Developer")
        be.epic_add("e", "Epic")
        be.story_add("e", "s", "Story")
        be.task_add("s", "t1", "T", goal="g", role="developer")
        rows = _r.role_list(be)
        assert rows[0]["task_count"] == 1


class TestRoleDelete:
    def test_delete_unused_succeeds(self, be, isolate_profiles):
        _r.role_create(be, "tmp", "Tmp")
        msg = _r.role_delete(be, "tmp")
        assert "deleted" in msg
        with pytest.raises(ServiceError):
            _r.role_show(be, "tmp")

    def test_delete_with_refs_raises_without_force(self, be, isolate_profiles):
        _r.role_create(be, "developer", "Developer")
        be.epic_add("e", "Epic")
        be.story_add("e", "s", "Story")
        be.task_add("s", "t1", "T", goal="g", role="developer")
        with pytest.raises(ServiceError) as exc:
            _r.role_delete(be, "developer")
        assert "referenced by" in str(exc.value)

    def test_delete_with_force_removes_anyway(self, be, isolate_profiles):
        _r.role_create(be, "developer", "Developer")
        be.epic_add("e", "Epic")
        be.story_add("e", "s", "Story")
        be.task_add("s", "t1", "T", goal="g", role="developer")
        msg = _r.role_delete(be, "developer", force=True)
        assert "deleted" in msg

    def test_delete_unknown_raises(self, be, isolate_profiles):
        with pytest.raises(ServiceError):
            _r.role_delete(be, "ghost")


class TestSeed:
    def test_seed_from_files(self, be, isolate_profiles):
        roles_dir = os.path.join(_r._repo_root(), "agents", "roles")
        for slug in ("developer", "qa"):
            path = os.path.join(roles_dir, f"{slug}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# Role: {slug.title()}\n\nProfile.\n")
        out = _r.seed_existing_roles(be)
        assert out["scanned"] == 2
        assert out["inserted"] == 2
        assert out["from_files"] == 2

    def test_seed_idempotent(self, be, isolate_profiles):
        roles_dir = os.path.join(_r._repo_root(), "agents", "roles")
        with open(os.path.join(roles_dir, "developer.md"), "w", encoding="utf-8") as f:
            f.write("# Role: Developer\n")
        _r.seed_existing_roles(be)
        out2 = _r.seed_existing_roles(be)
        assert out2["inserted"] == 0
        assert out2["skipped"] >= 1

    def test_seed_picks_up_distinct_task_roles(self, be, isolate_profiles):
        be.epic_add("e", "Epic")
        be.story_add("e", "s", "Story")
        be.task_add("s", "t1", "T", goal="g", role="dev-from-task")
        out = _r.seed_existing_roles(be)
        assert out["from_tasks"] == 1
        assert out["inserted"] == 1
