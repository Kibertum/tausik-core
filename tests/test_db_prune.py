"""Tests for v14b-junk-audit-pass — `tausik db prune` backup hygiene."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from cmd_db import list_backups, prune_backups  # noqa: E402


def _make_backups(tmp_path: Path, names: list[str]) -> list[Path]:
    """Create backup files with strictly increasing mtimes (newest = last in list)."""
    paths: list[Path] = []
    base = time.time() - 1_000_000
    for i, name in enumerate(names):
        p = tmp_path / name
        p.write_bytes(b"backup")
        # Stamp mtime so order is deterministic across filesystems.
        os.utime(p, (base + i, base + i))
        paths.append(p)
    return paths


class TestListBackups:
    def test_empty_dir_returns_empty(self, tmp_path):
        assert list_backups(str(tmp_path)) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path):
        # NEGATIVE: missing directory is tolerated.
        assert list_backups(str(tmp_path / "absent")) == []

    def test_only_matching_pattern_listed(self, tmp_path):
        _make_backups(tmp_path, ["tausik.db.bak.v1", "tausik.db", "other.txt"])
        result = list_backups(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("tausik.db.bak.v1")

    def test_sorted_newest_first(self, tmp_path):
        _make_backups(
            tmp_path,
            [
                "tausik.db.bak.v1",
                "tausik.db.bak.v2",
                "tausik.db.bak.v3",
            ],
        )
        result = list_backups(str(tmp_path))
        assert [os.path.basename(p) for p in result] == [
            "tausik.db.bak.v3",
            "tausik.db.bak.v2",
            "tausik.db.bak.v1",
        ]


class TestPruneBackups:
    def test_keep_n_drops_older(self, tmp_path):
        _make_backups(
            tmp_path,
            [
                "tausik.db.bak.v1",
                "tausik.db.bak.v2",
                "tausik.db.bak.v3",
                "tausik.db.bak.v4",
                "tausik.db.bak.v5",
            ],
        )
        result = prune_backups(str(tmp_path), keep=2)
        assert len(result["kept"]) == 2
        assert len(result["deleted"]) == 3
        # Kept = 2 newest (v5, v4)
        kept_names = sorted(os.path.basename(p) for p in result["kept"])
        assert kept_names == ["tausik.db.bak.v4", "tausik.db.bak.v5"]
        # Deleted files no longer on disk
        for p in result["deleted"]:
            assert not os.path.exists(p)
        # Kept files still on disk
        for p in result["kept"]:
            assert os.path.exists(p)

    def test_keep_zero_removes_all(self, tmp_path):
        # NEGATIVE: keep=0 deletes every backup.
        _make_backups(
            tmp_path,
            ["tausik.db.bak.v1", "tausik.db.bak.v2", "tausik.db.bak.v3"],
        )
        result = prune_backups(str(tmp_path), keep=0)
        assert result["kept"] == []
        assert len(result["deleted"]) == 3
        assert list_backups(str(tmp_path)) == []

    def test_keep_larger_than_count_is_noop(self, tmp_path):
        # NEGATIVE: --keep 10 with 2 backups → no deletions.
        _make_backups(tmp_path, ["tausik.db.bak.v1", "tausik.db.bak.v2"])
        result = prune_backups(str(tmp_path), keep=10)
        assert len(result["kept"]) == 2
        assert result["deleted"] == []

    def test_no_backups_returns_empty_lists(self, tmp_path):
        # NEGATIVE: empty workspace returns empty result, not error.
        result = prune_backups(str(tmp_path), keep=3)
        assert result == {"kept": [], "deleted": [], "errors": []}

    def test_negative_keep_clamped_to_zero(self, tmp_path):
        _make_backups(tmp_path, ["tausik.db.bak.v1"])
        result = prune_backups(str(tmp_path), keep=-5)
        assert result["kept"] == []
        assert len(result["deleted"]) == 1

    def test_kept_set_and_deleted_set_are_disjoint(self, tmp_path):
        _make_backups(
            tmp_path,
            ["tausik.db.bak.v1", "tausik.db.bak.v2", "tausik.db.bak.v3"],
        )
        result = prune_backups(str(tmp_path), keep=1)
        assert set(result["kept"]).isdisjoint(set(result["deleted"]))


class TestCmdDbCli:
    """End-to-end smoke through cmd_db with argparse-shaped namespace."""

    def test_prune_prints_kept_and_deleted(self, tmp_path, capsys, monkeypatch):
        from cmd_db import cmd_db

        _make_backups(
            tmp_path,
            [
                "tausik.db.bak.v1",
                "tausik.db.bak.v2",
                "tausik.db.bak.v3",
                "tausik.db.bak.v4",
            ],
        )
        # Point find_tausik_dir() at our tmp_path.
        import project_config

        monkeypatch.setattr(project_config, "find_tausik_dir", lambda: str(tmp_path))

        class Args:
            db_cmd = "prune"
            keep = 2

        cmd_db(svc=None, args=Args())
        out = capsys.readouterr().out
        assert "Kept (2)" in out
        assert "Deleted (2)" in out
        # Disk should reflect the prune
        assert len(list_backups(str(tmp_path))) == 2

    def test_prune_no_backups_message(self, tmp_path, capsys, monkeypatch):
        # NEGATIVE: no .bak files present → single-line message, exit 0.
        from cmd_db import cmd_db
        import project_config

        monkeypatch.setattr(project_config, "find_tausik_dir", lambda: str(tmp_path))

        class Args:
            db_cmd = "prune"
            keep = 3

        cmd_db(svc=None, args=Args())
        out = capsys.readouterr().out
        assert "No tausik.db.bak.* files found" in out

    def test_unknown_subcommand_raises(self, tmp_path, monkeypatch):
        # NEGATIVE: unknown 'db <foo>' surfaces a clear error.
        from cmd_db import cmd_db

        class Args:
            db_cmd = "nonsense"

        with pytest.raises(SystemExit, match="Unknown subcommand"):
            cmd_db(svc=None, args=Args())
