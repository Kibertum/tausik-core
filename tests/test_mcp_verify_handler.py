"""r14-mcp-verify + r14-mcp-verify-private-attr — verify MCP contract upgrade.

- task_slug now optional (matches CLI parity).
- scope and trigger now accepted as optional params.
- _handle_verify uses public service method, not svc.be._conn.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


@pytest.fixture
def svc(tmp_path):
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    return ProjectService(SQLiteBackend(str(tmp_path / "t.db")))


@pytest.fixture
def task_with_files(svc):
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "Task", goal="g", role="developer")
    svc.task_update(
        "t",
        acceptance_criteria="1. Works\n2. Returns error on bad input",
    )
    svc.task_start("t")
    return svc


class TestPublicServiceVerifyMethod:
    """ProjectService.run_verify_for_task is the canonical entry point."""

    def test_unknown_task_raises_service_error(self, svc):
        from tausik_utils import ServiceError

        with pytest.raises(ServiceError, match="not found"):
            svc.run_verify_for_task("does-not-exist")

    def test_with_task_returns_structured_dict(self, task_with_files):
        result = task_with_files.run_verify_for_task("t")
        assert "passed" in result
        assert "status" in result
        assert "trigger" in result
        assert result["task_slug"] == "t"
        assert result["trigger"] == "verify"

    def test_without_task_runs_full_suite_no_db_row(self, svc):
        result = svc.run_verify_for_task(None)
        assert "passed" in result
        assert result["task_slug"] is None
        # No verification_runs row written when task_slug is None.
        rows = svc.be._conn.execute(
            "SELECT COUNT(*) AS n FROM verification_runs"
        ).fetchone()
        assert rows["n"] == 0


class TestMcpHandlerSchemaContract:
    """tausik_verify schema reflects the v1.4 contract: no required keys,
    task_slug + scope + trigger all optional with sensible defaults."""

    def test_tools_extra_schema_says_task_slug_optional(self):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "harness",
                "claude",
                "mcp",
                "project",
            ),
        )
        from tools_extra import TOOLS_EXTRA

        verify = next(t for t in TOOLS_EXTRA if t["name"] == "tausik_verify")
        # No "required" key (or empty) — v1.4 made task_slug optional.
        required = verify["inputSchema"].get("required", [])
        assert "task_slug" not in required, (
            "tausik_verify must accept calls without task_slug after v1.4"
        )

    def test_tools_extra_schema_lists_scope_and_trigger(self):
        sys.path.insert(
            0,
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "harness",
                "claude",
                "mcp",
                "project",
            ),
        )
        from tools_extra import TOOLS_EXTRA

        verify = next(t for t in TOOLS_EXTRA if t["name"] == "tausik_verify")
        props = verify["inputSchema"]["properties"]
        assert "scope" in props
        assert "trigger" in props
        # scope must constrain to the SENAR Rule 5 enum.
        assert "manual" in props["scope"]["enum"]
        assert "verify" in props["trigger"]["enum"]


class TestMcpHandlerNoPrivateAttrAccess:
    """Static check: handlers no longer touch `svc.be._conn`. Catches the
    layering regression that used to happen in `_handle_verify`."""

    def test_no_be_conn_in_handle_verify_source(self):
        for ide in ("claude", "cursor"):
            path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "harness",
                ide,
                "mcp",
                "project",
                "handlers.py",
            )
            with open(path, encoding="utf-8") as f:
                src = f.read()
            # Find `_handle_verify` body — terminate at next top-level def.
            start = src.index("def _handle_verify(")
            end = src.find("\ndef ", start + 1)
            body = src[start: end if end != -1 else len(src)]
            assert "svc.be._conn" not in body, (
                f"_handle_verify in {ide} still touches svc.be._conn — "
                "must use ProjectService.run_verify_for_task instead."
            )
