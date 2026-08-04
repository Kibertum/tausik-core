"""The shared store's directory must not look like a project to `find_tausik_dir`.

This is the guard for a defect that actually happened rather than a precaution.
The shared knowledge store was first placed at `~/.tausik/knowledge.db`, and
`find_tausik_dir` locates a project by walking UP looking for a directory named
exactly `.tausik`. From the moment that directory existed, every path under the
user's home resolved to the HOME as its project: commands run from temp
directories wrote a stray project database there, six tests turned red by
silently sharing one "project", and any of the user's own projects living under
their home without a `.tausik` of its own would have resolved the same way.

An earlier test in `test_knowledge_db.py` guarded ONE direction — that
`TAUSIK_DIR` must not move the shared store. The reverse was never asked, and
the reverse is where the damage was. A one-way guarantee reads like a two-way
one, which is the whole reason this file states the property both ways.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import project_config  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_db.py", "scripts/project_config.py"]


class TestTheTwoNamesCannotCollide:
    """Compared as CONSTANTS, never as literals — a literal survives a rename."""

    def test_the_shared_home_is_not_the_project_marker(self):
        assert knowledge_db._HOME_DIRNAME != project_config.TAUSIK_DIR, (
            "the shared store's directory has the same name as the project marker, so "
            "every path under the user's home now resolves to the home as its project"
        )

    def test_neither_name_is_a_path_prefix_of_the_other(self):
        """`.tausik` and `.tausik/x` would collide just as badly as equality."""
        shared = knowledge_db._HOME_DIRNAME.strip("/\\")
        marker = project_config.TAUSIK_DIR.strip("/\\")
        assert not shared.startswith(marker + "/") and not shared.startswith(marker + "\\")
        assert not marker.startswith(shared + "/") and not marker.startswith(shared + "\\")

    def test_the_legacy_name_is_remembered_as_legacy_only(self):
        """The old name must survive as a MIGRATION SOURCE, not as the home."""
        assert knowledge_db._LEGACY_HOME_DIRNAME == project_config.TAUSIK_DIR, (
            "the legacy constant no longer names the directory the store used to "
            "live in, so an existing store would never be found"
        )
        assert knowledge_db._LEGACY_HOME_DIRNAME != knowledge_db._HOME_DIRNAME


class TestProjectDiscoveryDoesNotFindTheSharedStore:
    """The behavioural half: walk up from below and see what is found."""

    def test_walking_up_past_a_shared_store_does_not_treat_it_as_a_project(
        self, tmp_path, monkeypatch
    ):
        """Reproduces the exact shape of the incident: a shared store above, a
        working directory below, and no project of its own anywhere between."""
        fake_home = tmp_path / "home"
        shared = fake_home / knowledge_db._HOME_DIRNAME
        shared.mkdir(parents=True)
        (shared / "knowledge.db").write_bytes(b"")

        deep = fake_home / "some" / "work" / "dir"
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)
        monkeypatch.delenv("TAUSIK_DIR", raising=False)

        found = project_config.find_tausik_dir()
        assert os.path.normcase(str(shared)) != os.path.normcase(os.path.abspath(found)), (
            "project discovery walked up and adopted the shared knowledge store as a "
            "project — the exact failure this file exists for"
        )

    def test_a_real_project_below_the_shared_store_still_wins(self, tmp_path, monkeypatch):
        """The guard must not break the ordinary case it sits next to."""
        fake_home = tmp_path / "home"
        (fake_home / knowledge_db._HOME_DIRNAME).mkdir(parents=True)

        project = fake_home / "repo"
        (project / project_config.TAUSIK_DIR).mkdir(parents=True)
        monkeypatch.chdir(project)
        monkeypatch.delenv("TAUSIK_DIR", raising=False)

        found = os.path.normcase(os.path.abspath(project_config.find_tausik_dir()))
        expected = os.path.normcase(str(project / project_config.TAUSIK_DIR))
        assert found == expected


class TestAnExistingStoreIsCarriedAcross:
    """AC5: nobody loses a knowledge base to a rename, and nobody is told it is empty."""

    @pytest.fixture(autouse=True)
    def isolated_home(self, monkeypatch, tmp_path):
        monkeypatch.delenv("TAUSIK_HOME", raising=False)
        monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path) if p == "~" else p)
        return tmp_path

    def _seed_legacy(self, home) -> int:
        import sqlite3

        legacy_dir = home / knowledge_db._LEGACY_HOME_DIRNAME
        legacy_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(legacy_dir / "knowledge.db")
        knowledge_db.init_knowledge_schema(conn)
        conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, created_at, updated_at) "
            "VALUES ('u1', 'pattern', 'из старого места', 'тело', '2026-08-03', '2026-08-03')"
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        conn.close()
        return count

    def test_a_store_at_the_old_address_is_found_and_kept_whole(self, isolated_home):
        before = self._seed_legacy(isolated_home)
        assert before == 1

        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None, "the store at the old address was reported as absent"
        try:
            assert conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0] == before
        finally:
            conn.close()

    def test_exists_and_read_agree_about_the_old_address(self, isolated_home):
        """Two functions disagreeing on existence is how a backup reports 'nothing'."""
        self._seed_legacy(isolated_home)
        assert knowledge_db.knowledge_db_exists() is True

    def test_the_old_copy_is_left_in_place_not_deleted(self, isolated_home):
        """Deleting inside a user's home is theirs to decide."""
        self._seed_legacy(isolated_home)
        knowledge_db.connect_knowledge_db(create=False)
        assert (isolated_home / knowledge_db._LEGACY_HOME_DIRNAME / "knowledge.db").is_file()

    def test_an_existing_new_store_is_never_overwritten(self, isolated_home):
        """Adoption must not clobber a store that is already here."""
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.execute(
            "INSERT INTO memory (entry_uuid, type, title, content, created_at, updated_at) "
            "VALUES ('new', 'pattern', 'уже здесь', 'тело', '2026-08-03', '2026-08-03')"
        )
        conn.commit()
        conn.close()

        self._seed_legacy(isolated_home)
        conn = knowledge_db.connect_knowledge_db(create=False)
        assert conn is not None
        try:
            titles = {r[0] for r in conn.execute("SELECT title FROM memory")}
        finally:
            conn.close()
        assert titles == {"уже здесь"}, "adoption overwrote a store that already existed"

    def test_an_explicit_home_is_never_silently_redirected(self, isolated_home, monkeypatch):
        """`TAUSIK_HOME` names a place; adopting into it would reach for data
        the caller did not point at."""
        self._seed_legacy(isolated_home)
        elsewhere = isolated_home / "elsewhere"
        monkeypatch.setenv("TAUSIK_HOME", str(elsewhere))

        assert knowledge_db.connect_knowledge_db(create=False) is None
        assert not (elsewhere / "knowledge.db").exists()
