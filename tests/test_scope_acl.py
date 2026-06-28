"""Tests for scripts/scope_acl.py + scope ACL plumbing (v15-scope-declare).

AC coverage: canonical normalization, lenient parsing of corrupt rows,
service-level CRUD through task_update, ServiceError on invalid input.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from scope_acl import normalize_acl_json, parse_task_acl  # noqa: E402


class TestNormalize:
    def test_list_becomes_canonical_json(self):
        assert normalize_acl_json(["scripts/*.py", "docs/"], "scope_paths") == json.dumps(
            ["scripts/*.py", "docs/"], ensure_ascii=False
        )

    def test_json_string_accepted(self):
        assert normalize_acl_json('["a.py"]', "scope_paths") == '["a.py"]'

    def test_entries_stripped(self):
        assert normalize_acl_json(["  a.py  "], "scope_paths") == '["a.py"]'

    def test_none_clears(self):
        assert normalize_acl_json(None, "scope_paths") is None

    def test_empty_list_is_explicit_nothing(self):
        assert normalize_acl_json([], "scope_paths") == "[]"

    def test_non_list_rejected(self):
        with pytest.raises(ValueError, match="scope_paths"):
            normalize_acl_json('{"a": 1}', "scope_paths")

    def test_empty_entry_rejected(self):
        with pytest.raises(ValueError, match=r"scope_tools\[1\]"):
            normalize_acl_json(["Edit", "  "], "scope_tools")

    def test_non_string_entry_rejected(self):
        with pytest.raises(ValueError, match=r"scope_paths\[0\]"):
            normalize_acl_json([42], "scope_paths")

    def test_invalid_json_string_rejected(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            normalize_acl_json("[broken", "scope_paths")


class TestParse:
    def test_round_trip(self):
        task = {"scope_paths": '["src/*.py"]', "scope_tools": '["Edit", "Write"]'}
        assert parse_task_acl(task) == {"paths": ["src/*.py"], "tools": ["Edit", "Write"]}

    def test_missing_fields_empty(self):
        assert parse_task_acl({}) == {"paths": [], "tools": []}

    def test_corrupt_json_degrades_to_empty(self):
        assert parse_task_acl({"scope_paths": "{nope"}) == {"paths": [], "tools": []}

    def test_non_list_json_degrades_to_empty(self):
        assert parse_task_acl({"scope_paths": '"a string"'}) == {"paths": [], "tools": []}

    def test_non_string_entries_dropped(self):
        assert parse_task_acl({"scope_paths": '["ok.py", 13, ""]'})["paths"] == ["ok.py"]


@pytest.fixture
def svc(tmp_path):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    service = ProjectService(SQLiteBackend(str(tmp_path / "t.db")))
    service.task_add(None, "acl-task", "ACL task")
    return service


class TestServiceCrud:
    def test_update_stores_canonical_json(self, svc):
        svc.task_update("acl-task", scope_paths=["scripts/*.py"], scope_tools=["Edit"])
        task = svc.be.task_get("acl-task")
        assert json.loads(task["scope_paths"]) == ["scripts/*.py"]
        assert json.loads(task["scope_tools"]) == ["Edit"]
        assert parse_task_acl(task) == {"paths": ["scripts/*.py"], "tools": ["Edit"]}

    def test_update_accepts_json_string(self, svc):
        svc.task_update("acl-task", scope_paths='["docs/**"]')
        assert json.loads(svc.be.task_get("acl-task")["scope_paths"]) == ["docs/**"]

    def test_invalid_input_raises_service_error_and_keeps_row(self, svc):
        from tausik_utils import ServiceError

        svc.task_update("acl-task", scope_paths=["good.py"])
        with pytest.raises(ServiceError, match="scope_paths"):
            svc.task_update("acl-task", scope_paths=["", "bad"])
        # prior value untouched
        assert json.loads(svc.be.task_get("acl-task")["scope_paths"]) == ["good.py"]
