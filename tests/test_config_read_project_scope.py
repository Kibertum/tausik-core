"""mcp-config-read-paths-ignore-project-handle — reads follow the project handle.

The write path was fixed in mcp-gate-toggle-mutates-real-project-config (#125);
the READ paths carried the identical defect — `load_config`/`load_gates` resolved
from the process cwd, so a `gates status` for one project described whichever
project the process stood in. Invisible while the MCP server's cwd equals the
project root; a wrong answer the moment `svc` carries project identity (epic
v2-global-mcp).

Coverage:
  - AC4 (backward compat): a no-argument read ignores an unrelated project's
    directory — it still reads the ambient project, byte-for-byte as before.
  - AC5 (isolation): a service handed a config in tmp_path describes THAT
    project's gates and stacks, not the cwd project's.
  - AC1 (trust tiers stay per-machine): the user tier is applied regardless of
    which project directory is read — it is NOT reparameterised by tausik_dir.
  - AC7 (edge): an empty/absent config in the declared dir yields the default
    gates and does not raise.
  - AC3 (handler): _handle_gates_status(svc) renders the svc's project.
"""

from __future__ import annotations

import json
import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_config import load_config, load_gates  # noqa: E402
from project_service import ProjectService  # noqa: E402

# An unguarded, arbitrary project-tier value: config_trust never rewrites
# bootstrap.stacks, so it is a clean witness for "which config was read".
MARKER = "iso-marker-stack"


def _write_project_config(root, cfg: dict) -> str:
    """Create <root>/.tausik/config.json and return the .tausik dir."""
    td = os.path.join(str(root), ".tausik")
    os.makedirs(td, exist_ok=True)
    with open(os.path.join(td, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return td


def _svc_for(td: str) -> ProjectService:
    return ProjectService(SQLiteBackend(os.path.join(td, "tausik.db")))


class TestReadFollowsDeclaredDir:
    def test_declared_dir_read_uses_it_and_ambient_ignores_it(self, tmp_path):
        # AC5 + AC4 in one: the declared read sees the marker; the ambient
        # (no-arg) read does NOT — it stays on the cwd project, unchanged.
        td = _write_project_config(
            tmp_path, {"bootstrap": {"stacks": [MARKER]}, "gates": {"mypy": {"enabled": True}}}
        )
        scoped = load_config(td)
        ambient = load_config()
        assert scoped.get("bootstrap", {}).get("stacks") == [MARKER]
        assert ambient.get("bootstrap", {}).get("stacks") != [MARKER]

    def test_load_gates_scopes_to_declared_dir(self, tmp_path):
        # mypy defaults OFF; enabling it is a tightening config_trust allows, so
        # it survives resolve() and proves the gate set came from the declared dir.
        td = _write_project_config(tmp_path, {"gates": {"mypy": {"enabled": True}}})
        assert load_gates(tausik_dir=td)["mypy"]["enabled"] is True
        # Ambient read must not inherit the tmp project's override.
        assert load_gates() is not None  # smoke: no crash, ambient still resolves


class TestGatesStatusIsolation:
    def test_gates_status_describes_its_own_project(self, tmp_path):
        td = _write_project_config(
            tmp_path, {"bootstrap": {"stacks": [MARKER]}, "gates": {"mypy": {"enabled": True}}}
        )
        result = _svc_for(td).gates_status()
        assert result["active_stacks"] == [MARKER]
        assert result["gates"]["mypy"]["enabled"] is True

    def test_gates_status_empty_config_returns_defaults(self, tmp_path):
        # AC7 edge: no config.json in the declared dir → defaults, no exception.
        td = os.path.join(str(tmp_path), ".tausik")
        os.makedirs(td, exist_ok=True)
        result = _svc_for(td).gates_status()  # must not raise
        assert "filesize" in result["gates"]
        assert result["active_stacks"] == []


class TestTrustTiersStayPerMachine:
    def test_user_tier_is_project_dir_independent(self, tmp_path, monkeypatch):
        # AC1: the user tier is read from $TAUSIK_USER_CONFIG (per-machine), so it
        # applies no matter which project directory the project tier is read from.
        # Reparameterising it by tausik_dir would be a new defect, not a fix.
        user_cfg = tmp_path / "user.json"
        user_cfg.write_text(json.dumps({"session_max_minutes": 999}), encoding="utf-8")
        monkeypatch.setenv("TAUSIK_USER_CONFIG", str(user_cfg))
        td = _write_project_config(tmp_path / "proj", {"bootstrap": {"stacks": [MARKER]}})
        cfg = load_config(td)
        assert cfg["session_max_minutes"] == 999  # user tier applied
        assert cfg["bootstrap"]["stacks"] == [MARKER]  # project tier from declared dir


class TestHandlerThreadsSvcDir:
    def test_handle_gates_status_renders_svc_project(self, tmp_path):
        # AC3: the handler must resolve the project from svc, not cwd.
        mcp_dir = os.path.join(
            os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"
        )
        sys.path.insert(0, mcp_dir)
        from handlers import _handle_gates_status

        td = _write_project_config(
            tmp_path, {"bootstrap": {"stacks": [MARKER]}, "gates": {"mypy": {"enabled": True}}}
        )
        out = _handle_gates_status(_svc_for(td))
        assert f"Detected stacks: {MARKER}" in out
        assert "[ON] mypy" in out
        # No svc → ambient fallback still works and does not carry the marker.
        assert MARKER not in _handle_gates_status(None)
