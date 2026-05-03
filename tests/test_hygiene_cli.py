"""Tests for `tausik hygiene` (v14-hygiene-cli-stub).

Covers v1 of `docs/{en,ru}/task-archive-spec.md`:
- always dry-run
- disabled when `task_archive.enabled` is missing/false
- only `done` tasks older than `done_age_days` are listed
- `--confirm` is rejected (no destructive op exists in v1)
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
    (tmp_path / ".tausik").mkdir()
    be = SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db"))
    s = ProjectService(be)
    yield s
    be.close()


def _write_cfg(tmp_path, body: dict) -> None:
    cfg_dir = tmp_path / ".tausik"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "config.json").write_text(json.dumps(body))


def _seed_done_task(svc, slug: str, completed_iso: str) -> None:
    svc.task_add(None, slug, f"Title for {slug}")
    svc.be._conn.execute(
        "UPDATE tasks SET status = 'done', completed_at = ? WHERE slug = ?",
        (completed_iso, slug),
    )
    svc.be._conn.commit()


class TestArchiveCandidates:
    def test_disabled_when_no_block(self, svc):
        from project_cli_hygiene import _archive_config

        enabled, age = _archive_config({})
        assert enabled is False
        assert age == 90

    def test_disabled_when_enabled_false(self, svc):
        from project_cli_hygiene import _archive_config

        enabled, _ = _archive_config({"task_archive": {"enabled": False}})
        assert enabled is False

    def test_invalid_age_clamps_to_default_or_min(self, svc):
        from project_cli_hygiene import _archive_config

        _, a1 = _archive_config({"task_archive": {"enabled": True, "done_age_days": "junk"}})
        assert a1 == 90
        _, a2 = _archive_config({"task_archive": {"enabled": True, "done_age_days": 0}})
        assert a2 == 1

    def test_candidates_only_done_old(self, svc):
        from project_cli_hygiene import _archive_candidates

        _seed_done_task(svc, "old1", "2020-01-01T00:00:00Z")
        _seed_done_task(svc, "old2", "2020-06-01T00:00:00Z")
        # Active task — never included
        svc.task_add(None, "active1", "Active task")
        # Done but recent
        _seed_done_task(svc, "fresh", "2099-01-01T00:00:00Z")

        rows = _archive_candidates(svc, age_days=90)
        slugs = [r["slug"] for r in rows]
        assert "old1" in slugs
        assert "old2" in slugs
        assert "fresh" not in slugs
        assert "active1" not in slugs


class TestCmdHygieneArchive:
    def _run(self, svc, args_obj, capsys):
        from project_cli_hygiene import cmd_hygiene

        cmd_hygiene(svc, args_obj)
        return capsys.readouterr().out

    def test_no_subcmd_prints_usage(self, svc, capsys):
        class A:
            hygiene_cmd = None

        out = self._run(svc, A(), capsys)
        assert "Usage: tausik hygiene" in out
        assert "archive" in out

    def test_disabled_message(self, svc, tmp_path, capsys):
        # Point the config loader at our tmp_path via TAUSIK_DIR (set by fixture)
        _write_cfg(tmp_path, {})

        class A:
            hygiene_cmd = "archive"
            confirm = False

        out = self._run(svc, A(), capsys)
        assert "disabled" in out.lower()
        assert "task_archive.enabled" in out

    def test_dry_run_lists_candidates(self, svc, tmp_path, capsys):
        _write_cfg(tmp_path, {"task_archive": {"enabled": True, "done_age_days": 90}})
        _seed_done_task(svc, "old-x", "2020-01-01T00:00:00Z")

        class A:
            hygiene_cmd = "archive"
            confirm = False

        out = self._run(svc, A(), capsys)
        assert "old-x" in out
        assert "dry-run" in out.lower()
        assert "read-only" in out.lower()

    def test_no_candidates_message(self, svc, tmp_path, capsys):
        _write_cfg(tmp_path, {"task_archive": {"enabled": True, "done_age_days": 90}})

        class A:
            hygiene_cmd = "archive"
            confirm = False

        out = self._run(svc, A(), capsys)
        assert "no done tasks" in out.lower()


class TestNegativeConfirmRejected:
    def test_confirm_fails_fast(self, svc, tmp_path):
        from project_cli_hygiene import cmd_hygiene
        from tausik_utils import ServiceError

        _write_cfg(tmp_path, {"task_archive": {"enabled": True}})
        _seed_done_task(svc, "old-y", "2020-01-01T00:00:00Z")

        class A:
            hygiene_cmd = "archive"
            confirm = True

        with pytest.raises(ServiceError) as excinfo:
            cmd_hygiene(svc, A())
        assert "v1 is read-only" in str(excinfo.value)
