"""Tests for bootstrap_paths.portable_path + rename-proof MCP/hook generation."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from bootstrap_paths import portable_path  # noqa: E402


def test_in_project_becomes_var_relative():
    proj = os.path.normpath("/work/proj")
    inside = os.path.join(proj, ".claude", "mcp", "project", "server.py")
    out = portable_path(inside, proj, "${workspaceFolder}")
    assert out == "${workspaceFolder}/.claude/mcp/project/server.py"


def test_outside_project_stays_absolute():
    proj = os.path.normpath("/work/proj")
    outside = os.path.normpath("/usr/bin/python")
    out = portable_path(outside, proj, "${workspaceFolder}")
    assert out == "/usr/bin/python"
    assert "${workspaceFolder}" not in out


def test_bare_executable_not_portablized():
    # Regression (review HIGH): a bare 'python'/'py' is a PATH lookup, not a file
    # path — must stay unchanged even when CWD == project_dir on the same drive
    # (where relpath would otherwise yield 'python' → '${var}/python').
    proj = os.getcwd()
    assert portable_path("python", proj, "${workspaceFolder}") == "python"
    assert portable_path("py", proj, "${CLAUDE_PROJECT_DIR:-.}") == "py"


def test_project_root_itself_maps_to_var():
    proj = os.path.normpath("/work/proj")
    assert portable_path(proj, proj, "${workspaceFolder}") == "${workspaceFolder}"


def test_no_backslashes_in_output():
    proj = os.path.normpath("/work/proj")
    inside = os.path.join(proj, "scripts", "hooks", "x.py")
    out = portable_path(inside, proj, "${CLAUDE_PROJECT_DIR}")
    assert "\\" not in out


def _touch(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("# x\n")


def test_claude_mcp_is_rename_proof(tmp_path):
    from bootstrap_generate import generate_mcp_json

    project = tmp_path / "proj"
    ide_dir = project / ".claude"
    _touch(str(ide_dir / "mcp" / "project" / "server.py"))
    # venv python INSIDE the project → must also become var-relative.
    venv_py = project / ".venv" / "Scripts" / "python.exe"
    _touch(str(venv_py))
    generate_mcp_json(str(project), str(ide_dir), venv_python=str(venv_py))
    cfg = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))
    srv = cfg["mcpServers"]["tausik-project"]
    assert srv["command"] == "${CLAUDE_PROJECT_DIR:-.}/.venv/Scripts/python.exe"
    assert srv["args"][0] == "${CLAUDE_PROJECT_DIR:-.}/.claude/mcp/project/server.py"
    assert srv["args"][2] == "${CLAUDE_PROJECT_DIR:-.}"
    assert str(project).replace("\\", "/") not in json.dumps(srv)  # folder name not embedded


def test_claude_mcp_external_python_stays_absolute(tmp_path):
    from bootstrap_generate import generate_mcp_json

    project = tmp_path / "proj"
    ide_dir = project / ".claude"
    _touch(str(ide_dir / "mcp" / "project" / "server.py"))
    generate_mcp_json(str(project), str(ide_dir), venv_python="C:/sys/python.exe")
    srv = json.loads((project / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][
        "tausik-project"
    ]
    assert srv["command"] == "C:/sys/python.exe"  # external python kept absolute
    assert srv["args"][0] == "${CLAUDE_PROJECT_DIR:-.}/.claude/mcp/project/server.py"


def test_cursor_mcp_uses_workspacefolder(tmp_path):
    from bootstrap_generate import generate_cursor_mcp_json

    project = tmp_path / "proj"
    ide_dir = project / ".cursor"
    _touch(str(ide_dir / "mcp" / "project" / "server.py"))
    generate_cursor_mcp_json(str(project), str(ide_dir), venv_python="C:/sys/python.exe")
    srv = json.loads((project / ".cursor" / "mcp.json").read_text(encoding="utf-8"))["mcpServers"][
        "tausik-project"
    ]
    assert srv["args"][0] == "${workspaceFolder}/.cursor/mcp/project/server.py"
    assert srv["args"][2] == "${workspaceFolder}"


def test_claude_hooks_are_rename_proof(tmp_path):
    from bootstrap_generate import generate_settings_claude

    project = tmp_path / "proj"
    target = project / ".claude"
    target.mkdir(parents=True)
    # lib INSIDE the project (submodule layout) → hooks become var-relative.
    lib = project / ".tausik-lib"
    (lib / "scripts" / "hooks").mkdir(parents=True)
    generate_settings_claude(str(target), str(project), lib_dir=str(lib))
    settings = json.loads((target / "settings.json").read_text(encoding="utf-8"))
    cmds = [
        h["command"]
        for entries in settings["hooks"].values()
        for entry in entries
        for h in entry["hooks"]
    ]
    assert cmds, "no hooks generated"
    assert all("${CLAUDE_PROJECT_DIR}/.tausik-lib/scripts/hooks/" in c for c in cmds)
    # No quotes around the path — else the hooks-parity tokenizer (splits on
    # whitespace, matches *.py) would fail to extract script basenames.
    assert all('"' not in c for c in cmds)
    assert all(any(t.endswith(".py") for t in c.split()) for c in cmds)
