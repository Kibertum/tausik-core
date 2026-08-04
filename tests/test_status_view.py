"""status-cli-mcp-divergence: one status model, two renderers that agree.

Regression guard for the defect where `cmd_status` (CLI) and `_handle_status`
(MCP) each surfaced a DIFFERENT subset of signals: the CLI showed risk / RENAR /
epics / calibration / capacity and HID open explorations + audit-overdue, while
the MCP handler did the exact opposite. The two channels now render from the
same `build_status_view`, so any signal present on one is present on the other.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from status_view import (  # noqa: E402
    build_status_view,
    render_status_cli,
    render_status_mcp,
)
from tausik_utils import format_status_compact_json  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(os.path.join(str(tmp_path), "tausik.db"))
    return ProjectService(be)


def _make_audit_overdue(svc):
    """Three sessions since the last recorded audit (mirrors test_project_mcp)."""
    svc.be.session_start()
    first_id = svc.be.session_current()["id"]
    svc.be.meta_set("last_audit_session", str(first_id))
    svc.be.session_start()
    svc.be.session_start()
    svc.be.session_start()


class TestSignalSetsMatch:
    """Neither channel may show a signal the other hides."""

    def test_cli_now_surfaces_exploration_and_audit(self, svc):
        # These two were CLI blind spots — the MCP handler showed them, cmd_status
        # did not. Both must now appear in the CLI render.
        svc.exploration_start("research auth flow")
        _make_audit_overdue(svc)
        cli = render_status_cli(build_status_view(svc))
        assert "Open exploration" in cli
        assert "research auth flow" in cli
        assert "Rule 9.5" in cli

    def test_mcp_now_surfaces_epics(self, svc):
        # Epics was an MCP blind spot — cmd_status showed "Epics: N", the MCP
        # handler did not. It must now appear in the MCP render.
        svc.epic_add("e1", "Epic 1")
        mcp = render_status_mcp(build_status_view(svc))
        assert "Epics: 1" in mcp

    def test_both_channels_render_identical_signal_set(self, svc):
        # With every signal live, the two renders must carry the same set of
        # signal labels (formatting differs, the signals do not).
        svc.epic_add("e1", "Epic 1")
        svc.exploration_start("dig into caching")
        _make_audit_overdue(svc)
        view = build_status_view(svc)
        cli, mcp = render_status_cli(view), render_status_mcp(view)
        for label in ("Tasks:", "Session:", "Epics:", "Open exploration", "Rule 9.5"):
            assert label in cli, (label, cli)
            assert label in mcp, (label, mcp)


class TestConfigReadOnce:
    """The CLI's copy of mcp-config-read-paths-ignore-project-handle: config was
    resolved three times off the process cwd, never scoped to the project."""

    def test_load_config_called_once_and_scoped_to_project(self, svc, monkeypatch):
        import project_config

        calls: list = []
        real = project_config.load_config

        def _spy(tausik_dir=None, *a, **k):
            calls.append(tausik_dir)
            return real(tausik_dir, *a, **k)

        monkeypatch.setattr(project_config, "load_config", _spy)
        build_status_view(svc)
        # status_view's OWN read is the first one and is scoped to the project.
        # (Nested subsystem reads — session_check_duration, capacity, metrics —
        # pass None; those are their own concern, not cmd_status's former three
        # redundant cwd reads, which this replaces.)
        assert calls, "build_status_view never read config"
        assert calls[0] == svc.tausik_dir(), "status config not scoped to the svc project dir"
        assert calls.count(svc.tausik_dir()) == 1, "status re-read its own config (was 3x)"


class TestCompactParity:
    """The compact JSON path is now enriched identically for both channels — the
    CLI compact used to drop exploration + audit that the MCP compact carried."""

    def test_compact_view_enriches_exploration_and_audit(self, svc):
        svc.exploration_start("trace a leak")
        _make_audit_overdue(svc)
        view = build_status_view(svc, include_rich=False)
        payload = json.loads(format_status_compact_json(view["data"], view["duration_warning"]))
        assert payload["exploration_open"] is True
        assert payload["audit_overdue_sessions"] >= 3

    def test_compact_skips_rich_signals(self, svc):
        # include_rich=False must not pay for the rich-only DB/FS work.
        svc.epic_add("e1", "Epic 1")
        view = build_status_view(svc, include_rich=False)
        assert view["risk_line"] is None
        assert view["capacity"] is None
        assert view["skill_warning"] is None
        # but `data` is still enriched for the compact formatter
        assert view["data"]["session_max_minutes"] > 0

    def test_clean_project_omits_optional_signals(self, svc):
        # No exploration, no overdue audit → neither channel invents them.
        cli = render_status_cli(build_status_view(svc))
        assert "Open exploration" not in cli
        assert "Rule 9.5" not in cli
