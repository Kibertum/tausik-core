"""Tests for the Kilo Code bootstrap generator (Decision #119/#120)."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

import bootstrap_kilo as bk  # noqa: E402


def _make_lib(tmp_path):
    """Create a fake lib tree with a canonical project server.py."""
    lib = tmp_path / "lib"
    server = lib / "harness" / "claude" / "mcp" / "project" / "server.py"
    server.parent.mkdir(parents=True)
    server.write_text("# fake server\n", encoding="utf-8")
    return str(lib)


def test_config_written_to_both_paths(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    written = bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    assert len(written) == 2
    assert (project / ".kilo" / "kilo.jsonc").is_file()
    assert (project / ".kilocode" / "mcp.json").is_file()


def test_config_schema_is_kilo_native(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    data = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))
    assert "mcp" in data
    srv = data["mcp"]["tausik-project"]
    assert srv["type"] == "local"
    assert srv["enabled"] is True
    assert isinstance(srv["command"], list)  # command is an ARRAY (Decision #120)
    assert srv["command"][0] == "py"
    assert "--project" in srv["command"]


def test_prefers_copied_server_over_lib(tmp_path):
    project = tmp_path / "proj"
    ide_dir = project / ".kilo"
    copied = ide_dir / "mcp" / "project" / "server.py"
    copied.parent.mkdir(parents=True)
    copied.write_text("# copied\n", encoding="utf-8")
    lib = _make_lib(tmp_path)
    bk.generate_kilo_config(str(project), str(ide_dir), "py", lib)
    data = json.loads((ide_dir / "kilo.jsonc").read_text(encoding="utf-8"))
    cmd_path = data["mcp"]["tausik-project"]["command"][1]
    assert ".kilo/mcp/project/server.py" in cmd_path


def test_in_project_server_is_rename_proof(tmp_path):
    # An in-project server must use ${workspaceFolder}, never an absolute path
    # that embeds the (renamable) folder name. --project is always portable.
    project = tmp_path / "proj"
    ide_dir = project / ".kilo"
    copied = ide_dir / "mcp" / "project" / "server.py"
    copied.parent.mkdir(parents=True)
    copied.write_text("# copied\n", encoding="utf-8")
    bk.generate_kilo_config(str(project), str(ide_dir), "py", _make_lib(tmp_path))
    cmd = json.loads((ide_dir / "kilo.jsonc").read_text(encoding="utf-8"))["mcp"]["tausik-project"][
        "command"
    ]
    assert cmd[1] == "${workspaceFolder}/.kilo/mcp/project/server.py"
    # The absolute project path is NOT embedded → survives a folder rename.
    assert str(project).replace("\\", "/") not in cmd[1]
    assert cmd[3] == "${workspaceFolder}"


def test_in_project_venv_python_is_portable(tmp_path):
    # Regression (dogfood): an in-project venv python must be ${workspaceFolder}-
    # relative, not absolute — else a folder rename breaks the interpreter path.
    project = tmp_path / "proj"
    ide_dir = project / ".kilo"
    (ide_dir / "mcp" / "project").mkdir(parents=True)
    (ide_dir / "mcp" / "project" / "server.py").write_text("# x\n", encoding="utf-8")
    venv_py = project / ".tausik" / "venv" / "Scripts" / "python.exe"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text("", encoding="utf-8")
    bk.generate_kilo_config(str(project), str(ide_dir), str(venv_py), _make_lib(tmp_path))
    cmd = json.loads((ide_dir / "kilo.jsonc").read_text(encoding="utf-8"))["mcp"]["tausik-project"][
        "command"
    ]
    assert cmd[0] == "${workspaceFolder}/.tausik/venv/Scripts/python.exe"
    assert str(project).replace("\\", "/") not in json.dumps(cmd)


def test_bare_python_stays_bare(tmp_path):
    # No venv → 'python' on PATH must not be rewritten into a workspace path.
    project = tmp_path / "proj"
    project.mkdir()
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "python", _make_lib(tmp_path))
    cmd = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))["mcp"][
        "tausik-project"
    ]["command"]
    assert cmd[0] == "python"


def test_external_lib_server_stays_absolute(tmp_path):
    # A server resolved from an external lib (outside the project) keeps its
    # absolute path — a project rename doesn't move it. No ${workspaceFolder}.
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)  # tmp_path/lib is OUTSIDE tmp_path/proj
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    cmd = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))["mcp"][
        "tausik-project"
    ]["command"]
    assert "${workspaceFolder}" not in cmd[1]
    assert cmd[1].endswith("harness/claude/mcp/project/server.py")
    assert cmd[3] == "${workspaceFolder}"  # --project is portable regardless


def test_merge_preserves_user_servers(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    kilo_dir = project / ".kilo"
    kilo_dir.mkdir()
    pre = {
        "mcp": {"my-server": {"type": "local", "command": ["x"], "enabled": True}},
        "theme": "dark",
    }
    (kilo_dir / "kilo.jsonc").write_text(json.dumps(pre), encoding="utf-8")
    lib = _make_lib(tmp_path)
    bk.generate_kilo_config(str(project), str(kilo_dir), "py", lib)
    data = json.loads((kilo_dir / "kilo.jsonc").read_text(encoding="utf-8"))
    assert data["mcp"]["my-server"]["command"] == ["x"]  # user server preserved
    assert data["theme"] == "dark"  # other keys preserved
    assert "tausik-project" in data["mcp"]  # ours added


def test_idempotent(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    first = (project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8")
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    second = (project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8")
    assert first == second


def test_malformed_existing_is_replaced(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    kilo_dir = project / ".kilo"
    kilo_dir.mkdir()
    (kilo_dir / "kilo.jsonc").write_text("{ this is not valid json", encoding="utf-8")
    lib = _make_lib(tmp_path)
    # Must not raise; rewrites a valid file.
    bk.generate_kilo_config(str(project), str(kilo_dir), "py", lib)
    data = json.loads((kilo_dir / "kilo.jsonc").read_text(encoding="utf-8"))
    assert "tausik-project" in data["mcp"]


def test_no_server_returns_empty(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    # No copied server, no lib → nothing to write.
    written = bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", None)
    assert written == []
    assert not (project / ".kilo").exists()


def test_config_paths_override(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    cfg = {"kilo": {"config_paths": ["custom/kilo.json"]}}
    written = bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib, cfg)
    assert len(written) == 1
    assert (project / "custom" / "kilo.json").is_file()


def test_commands_written(tmp_path):
    target = tmp_path / ".kilo"
    n = bk.generate_kilo_commands(str(target))
    assert n == len(bk._COMMAND_STUBS)
    assert (target / "commands" / "start.md").is_file()
    # Idempotent: existing files are not recreated.
    assert bk.generate_kilo_commands(str(target)) == 0
