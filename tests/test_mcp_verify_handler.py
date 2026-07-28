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
        rows = svc.be._conn.execute("SELECT COUNT(*) AS n FROM verification_runs").fetchone()
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


def _handler_module():
    """Import the verification handlers module (one tree, copied per IDE).

    `_handle_verify` moved out of the 1345-line handlers.py into the domain
    module that owns doctor/verify/gates (mcp-handlers-god-module-split).
    """
    mcp_dir = os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
    sys.path.insert(0, mcp_dir)
    import handlers_verification  # noqa: PLC0415 — path must be set first

    return handlers_verification


class TestMcpVerifyReportsGateVerdicts:
    """mcp-verify-hides-gate-skip: the MCP answer must say what RAN.

    It used to answer `gates=['hadolint', 'pytest']` — names with no verdicts —
    so a SKIP read exactly like a PASS. On a task with no declared scope every
    scoped gate skips, which made "verify passed=True … pytest" the report of a
    run in which pytest never executed. CLAUDE.md tells the agent to prefer MCP
    over the CLI, so this was the surface the agent actually read.
    """

    @staticmethod
    def _svc_returning(report):
        """Service stub — these tests are about SERIALISING a report, not
        producing one. The gate engine already records `skipped` correctly; the
        defect was that this layer threw it away."""

        class _Stub:
            def run_verify_for_task(self, **_kwargs):
                return report

        return _Stub()

    def _report(self, **over):
        base = {
            "passed": True,
            "status": "miss",
            "trigger": "verify",
            "results": [
                {"name": "hadolint", "passed": True, "skipped": False},
                {"name": "pytest", "passed": True, "skipped": True},
            ],
            "relevant_files": ["scripts/foo.py"],
        }
        base.update(over)
        return base

    def test_skipped_gate_is_named_as_skipped(self):
        handlers = _handler_module()

        out = handlers._handle_verify(self._svc_returning(self._report()), "t")

        assert "SKIP" in out, f"no SKIP verdict in MCP verify output:\n{out}"
        assert "did NOT execute" in out, f"skip not called out in prose:\n{out}"
        # The bare-name format that hid the skip must not come back.
        assert "gates=['" not in out, f"MCP verify regressed to name-only gates:\n{out}"

    def test_all_passed_run_carries_no_skip_note(self):
        handlers = _handler_module()
        report = self._report(
            results=[
                {"name": "hadolint", "passed": True, "skipped": False},
                {"name": "pytest", "passed": True, "skipped": False},
            ]
        )

        out = handlers._handle_verify(self._svc_returning(report), "t")

        assert "SKIP" not in out
        assert "did NOT execute" not in out

    def test_empty_scope_is_called_out_with_an_action(self):
        handlers = _handler_module()

        out = handlers._handle_verify(self._svc_returning(self._report(relevant_files=[])), "t")

        assert "relevant_files" in out, (
            f"empty scope not surfaced — agent cannot tell this green is hollow:\n{out}"
        )

    def test_declared_scope_answer_differs_from_empty_scope_answer(self):
        handlers = _handler_module()

        empty = handlers._handle_verify(self._svc_returning(self._report(relevant_files=[])), "t")
        declared = handlers._handle_verify(self._svc_returning(self._report()), "t")

        assert empty != declared, (
            "verify answers identically with and without a declared scope — "
            "the caller cannot distinguish a verified run from an empty one"
        )

    def test_real_service_empty_scope_run_is_not_reported_as_verified(self, task_with_files):
        """End-to-end through the real service: a task with no declared scope."""
        handlers = _handler_module()

        out = handlers._handle_verify(task_with_files, "t")

        assert "relevant_files" in out, f"hollow run not flagged:\n{out}"
        assert "gates=['" not in out

    # verify-surfaces-skip-notes-residue: the empty-scope NOTE is a SCOPED-run
    # message; on the full-suite (taskless) path the service returns files=[] by
    # design, and the old unconditional NOTE scolded the widest verification the
    # tool offers with a literal "<slug>" that named no task.
    def test_taskless_full_suite_has_no_scoped_scolding(self):
        handlers = _handler_module()

        out = handlers._handle_verify(self._svc_returning(self._report(relevant_files=[])), None)

        assert "<slug>" not in out, f"unactionable literal <slug> on taskless run:\n{out}"
        assert "so every scoped gate" not in out, f"scoped scolding on full-suite run:\n{out}"
        assert "full-suite" in out, f"taskless path not distinguished:\n{out}"

    def test_scoped_empty_names_the_real_task(self):
        handlers = _handler_module()

        out = handlers._handle_verify(self._svc_returning(self._report(relevant_files=[])), "t")

        assert "<slug>" not in out, f"placeholder not substituted:\n{out}"
        assert "tausik task update t --relevant-files" in out, f"real slug not named:\n{out}"


class TestMcpHandlerNoPrivateAttrAccess:
    """Static check: handlers no longer touch `svc.be._conn`. Catches the
    layering regression that used to happen in `_handle_verify`."""

    def test_no_be_conn_in_handle_verify_source(self):
        # One canonical MCP tree. The `cursor` copy this loop used to also read was a
        # byte-identical hand-maintained mirror and has been deleted — copy_mcp hands
        # harness/claude/mcp to every IDE (see tests/test_mcp_single_canonical_tree.py).
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "harness",
            "claude",
            "mcp",
            "project",
            "handlers_verification.py",
        )
        with open(path, encoding="utf-8") as f:
            src = f.read()
        # Find `_handle_verify` body — terminate at next top-level def.
        start = src.index("def _handle_verify(")
        end = src.find("\ndef ", start + 1)
        body = src[start : end if end != -1 else len(src)]
        assert "svc.be._conn" not in body, (
            "_handle_verify still touches svc.be._conn — "
            "must use ProjectService.run_verify_for_task instead."
        )
