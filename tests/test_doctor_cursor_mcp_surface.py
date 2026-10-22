"""doctor warns when Cursor mcp.json lists non-TAUSIK servers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from service_doctor_cursor import check_cursor_mcp_surface  # noqa: E402


def test_silent_without_cursor_mcp(tmp_path: Path):
    assert check_cursor_mcp_surface(str(tmp_path)) == []


def test_ok_when_only_tausik_servers(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"tausik-project": {}, "codebase-rag": {}}}),
        encoding="utf-8",
    )
    rows = check_cursor_mcp_surface(str(tmp_path))
    assert len(rows) == 1 and rows[0][0] == "ok"
    assert "no extra MCP" in rows[0][2]


def test_warns_on_extra_servers_without_metering_claim(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "tausik-project": {},
                    "plugin-office": {},
                    "browser": {},
                }
            }
        ),
        encoding="utf-8",
    )
    rows = check_cursor_mcp_surface(str(tmp_path))
    assert len(rows) == 1 and rows[0][0] == "warn"
    detail = rows[0][2]
    assert "plugin-office" in detail and "browser" in detail
    assert "same Cursor plan" in detail
    assert ".cursor/mcp.json" in detail
    assert "cannot meter" in detail
    assert "only `~/.cursor/mcp.json`" in detail or "not only" in detail.lower()
