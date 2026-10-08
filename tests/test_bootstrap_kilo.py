"""Tests for the Kilo Code bootstrap generator (Decision #119/#120)."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

import bootstrap_kilo as bk


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


def test_in_project_server_is_absolute(tmp_path):
    # Kilo 7.8.3 does not expand ${workspaceFolder} in MCP commands (measured:
    # zero literals in kilo.exe), so an in-project server must be an ABSOLUTE
    # path. The historical "rename-proof" claim died with that measurement.
    project = tmp_path / "proj"
    ide_dir = project / ".kilo"
    copied = ide_dir / "mcp" / "project" / "server.py"
    copied.parent.mkdir(parents=True)
    copied.write_text("# copied\n", encoding="utf-8")
    bk.generate_kilo_config(str(project), str(ide_dir), "py", _make_lib(tmp_path))
    cmd = json.loads((ide_dir / "kilo.jsonc").read_text(encoding="utf-8"))["mcp"]["tausik-project"][
        "command"
    ]
    dumped = json.dumps(cmd)
    assert "${workspaceFolder}" not in dumped
    assert cmd[1] == (ide_dir / "mcp" / "project" / "server.py").resolve().as_posix()
    assert cmd[3] == project.resolve().as_posix()  # --project is absolute too


def test_in_project_venv_python_is_absolute(tmp_path):
    # Regression (1.11.2): the venv interpreter path must resolve on disk —
    # a ${workspaceFolder}-relative path never spawns under Kilo 7.8.3.
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
    assert cmd[0] == venv_py.resolve().as_posix()
    assert "${workspaceFolder}" not in json.dumps(cmd)


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
    # absolute path — a project rename doesn't move it. Everything is absolute
    # now, including --project.
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)  # tmp_path/lib is OUTSIDE tmp_path/proj
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    cmd = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))["mcp"][
        "tausik-project"
    ]["command"]
    assert "${workspaceFolder}" not in cmd[1]
    assert cmd[1].endswith("harness/claude/mcp/project/server.py")
    assert cmd[3] == project.resolve().as_posix()


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


def test_a_retired_managed_server_is_removed_from_the_kilo_config(tmp_path):
    import json

    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    kilo_dir = project / ".kilocode"
    kilo_dir.mkdir()
    (kilo_dir / "mcp.json").write_text(
        json.dumps({"mcp": {"mine": {"command": "node"}, "tausik-brain": {"command": "python"}}}),
        encoding="utf-8",
    )
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    cfg = json.loads((kilo_dir / "mcp.json").read_text(encoding="utf-8"))
    assert "tausik-brain" not in cfg["mcp"]
    assert "mine" in cfg["mcp"]


# --- Permission policy (the SECOND Kilo extension point) ---------


def _generated(tmp_path, config=None):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    written = bk.generate_kilo_config(
        str(project), str(project / ".kilo"), "py", lib, config=config
    )
    data = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))
    return project, data, written


def test_permission_policy_written_by_default(tmp_path):
    _, data, _ = _generated(tmp_path)
    perm = data["permission"]
    assert perm["edit"][".tausik/tausik.db"] == "deny"
    assert perm["edit"][".kilo/plugins/*"] == "deny"
    assert perm["bash"]["git push*"] == "ask"
    assert perm["bash"]["sqlite3*"] == "ask"
    assert perm["external_directory"] == "deny"


def test_permission_policy_managed_rules_win_user_values_do_not_leak(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    (project / ".kilo").mkdir()
    (project / ".kilo" / "kilo.jsonc").write_text(
        json.dumps(
            {
                "mcp": {},
                "permission": {
                    "edit": {".tausik/tausik.db": "allow", "own/file.txt": "deny"},
                    "webfetch": "ask",
                },
            }
        ),
        encoding="utf-8",
    )
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    perm = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))["permission"]
    assert perm["edit"][".tausik/tausik.db"] == "deny"  # governance wins
    assert perm["edit"]["own/file.txt"] == "deny"  # user rule preserved
    assert perm["webfetch"] == "ask"  # user's own op preserved
    assert perm["edit"][".kilo/plugins/*"] == "deny"  # managed key added


def test_permission_policy_opt_out(tmp_path):
    _, data, _ = _generated(tmp_path, config={"kilo": {"permission_policy": False}})
    assert "permission" not in data


def test_global_string_permission_is_the_users_word(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    (project / ".kilo").mkdir()
    (project / ".kilo" / "kilo.jsonc").write_text(
        json.dumps({"mcp": {}, "permission": "ask"}), encoding="utf-8"
    )
    bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    data = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))
    assert data["permission"] == "ask"  # a global action is left exactly as set


def test_permission_policy_idempotent(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    lib = _make_lib(tmp_path)
    for _ in range(2):
        bk.generate_kilo_config(str(project), str(project / ".kilo"), "py", lib)
    perm = json.loads((project / ".kilo" / "kilo.jsonc").read_text(encoding="utf-8"))["permission"]
    assert len(perm["edit"]) == 2 and len(perm["bash"]) == 2
