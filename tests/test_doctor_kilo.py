"""Tests for the Kilo MCP-config doctor check (v156 P3, probed since 1.11.2).

Two layers: structural validation of the stanza bootstrap_kilo writes, and a
LIVE initialize handshake against the configured command — parse-only ✓ is the
overclaim the probe exists to refuse (Kilo 7.8.3 never expands
${workspaceFolder}, so a parsing stanza could not spawn).

Run: pytest tests/test_doctor_kilo.py -v
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_doctor_kilo import check_kilo_config, is_kilo_project, probe_mcp_server


def _server_py(tmp_path):
    """Create a fake server.py under .kilo/mcp/project/ and return its abs path."""
    d = tmp_path / ".kilo" / "mcp" / "project"
    d.mkdir(parents=True)
    f = d / "server.py"
    f.write_text("# stub\n")
    return f


def _stub_server(tmp_path, name: str = "tausik-project"):
    """Write an MCP stub that answers one initialize handshake, then exits."""
    d = tmp_path / ".kilo" / "mcp" / "project"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "server.py"
    f.write_text(
        "import json, sys\n"
        "req = json.loads(sys.stdin.readline())\n"
        "resp = {'jsonrpc': '2.0', 'id': req.get('id', 1), 'result': {\n"
        f"    'protocolVersion': '2024-11-05', 'capabilities': {{}},\n"
        f"    'serverInfo': {{'name': {name!r}, 'version': '0.0-test'}}}}}}\n"
        "print(json.dumps(resp), flush=True)\n",
        encoding="utf-8",
    )
    return f


def _write_kilo_config(tmp_path, rel, stanza):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(stanza, indent=2))
    return p


def _valid_stanza(server_py_abs, project_dir):
    return {
        "mcp": {
            "tausik-project": {
                "type": "local",
                "command": ["python", str(server_py_abs), "--project", str(project_dir)],
                "enabled": True,
            }
        }
    }


# --- gating ------------------------------------------------------------------


def test_non_kilo_project_skipped(tmp_path):
    assert not is_kilo_project(str(tmp_path))
    assert check_kilo_config(str(tmp_path)) == []


def test_kilo_dir_without_config_warns(tmp_path):
    (tmp_path / ".kilo").mkdir()
    findings = check_kilo_config(str(tmp_path))
    assert len(findings) == 1
    assert findings[0][0] == "warn"
    assert "bootstrap --ide kilo" in findings[0][2]


# --- valid config ------------------------------------------------------------


def test_valid_config_ok(tmp_path):
    sp = _stub_server(tmp_path)
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), _valid_stanza(sp, tmp_path))
    findings = check_kilo_config(str(tmp_path))
    assert findings and all(f[0] == "ok" for f in findings), findings
    # The live probe is part of the verdict, not an optional extra.
    assert any("handshake OK" in f[2] for f in findings), findings


def test_jsonc_with_comments_parses(tmp_path):
    """Kilo tolerates // comments; the check must too (best-effort fallback)."""
    sp = _stub_server(tmp_path)
    p = tmp_path / ".kilo" / "kilo.jsonc"
    p.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(_valid_stanza(sp, tmp_path), indent=2)
    p.write_text("// TAUSIK Kilo MCP config\n" + body + "\n")
    findings = check_kilo_config(str(tmp_path))
    assert findings and findings[0][0] == "ok", findings


# --- failures / warnings -----------------------------------------------------


def test_invalid_json_fails(tmp_path):
    """NEGATIVE: a broken config is reported FAIL, not a traceback."""
    p = tmp_path / ".kilo" / "kilo.jsonc"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ this is not valid json :::}")
    findings = check_kilo_config(str(tmp_path))
    assert findings and findings[0][0] == "fail"
    assert "invalid JSON" in findings[0][2]


def test_missing_mcp_stanza_warns(tmp_path):
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), {"other": {}})
    findings = check_kilo_config(str(tmp_path))
    assert findings[0][0] == "warn"
    assert "mcp" in findings[0][2]


def test_missing_project_server_warns(tmp_path):
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), {"mcp": {"other-server": {}}})
    findings = check_kilo_config(str(tmp_path))
    assert findings[0][0] == "warn"
    assert "tausik-project" in findings[0][2]


def test_command_not_array_fails(tmp_path):
    stanza = {"mcp": {"tausik-project": {"command": "python server.py", "enabled": True}}}
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), stanza)
    findings = check_kilo_config(str(tmp_path))
    assert findings[0][0] == "fail"
    assert "command" in findings[0][2]


def test_server_py_missing_warns(tmp_path):
    stanza = _valid_stanza(str(tmp_path / ".kilo" / "mcp" / "project" / "server.py"), tmp_path)
    # do NOT create server.py
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), stanza)
    findings = check_kilo_config(str(tmp_path))
    assert findings[0][0] == "warn"
    assert "server.py not found" in findings[0][2]


def test_disabled_server_warns(tmp_path):
    sp = _server_py(tmp_path)
    stanza = _valid_stanza(sp, tmp_path)
    stanza["mcp"]["tausik-project"]["enabled"] = False
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), stanza)
    findings = check_kilo_config(str(tmp_path))
    assert findings[0][0] == "warn"
    assert "disabled" in findings[0][2]


def test_workspacefolder_command_warns(tmp_path):
    """NEGATIVE: ${workspaceFolder} parses but Kilo 7.8.3 never expands it —
    the stanza is dead at spawn and doctor must say so instead of ✓."""
    sp_dir = tmp_path / ".kilo" / "mcp" / "project"
    sp_dir.mkdir(parents=True)
    (sp_dir / "server.py").write_text("# stub\n")
    stanza = {
        "mcp": {
            "tausik-project": {
                "command": [
                    "python",
                    "${workspaceFolder}/.kilo/mcp/project/server.py",
                    "--project",
                    "${workspaceFolder}",
                ],
                "enabled": True,
            }
        }
    }
    _write_kilo_config(tmp_path, os.path.join(".kilocode", "mcp.json"), stanza)
    findings = check_kilo_config(str(tmp_path))
    assert findings and findings[0][0] == "warn", findings
    assert "does not expand" in findings[0][2]
    assert "bootstrap --ide kilo" in findings[0][2]
    # A dead-at-spawn config must not earn a probe ✓.
    assert not any("handshake OK" in f[2] for f in findings)


# --- live probe --------------------------------------------------------------


def test_probe_answers_when_server_speaks(tmp_path):
    sp = _stub_server(tmp_path)
    ok, detail = probe_mcp_server(
        [sys.executable, str(sp), "--project", str(tmp_path)], str(tmp_path), timeout=15
    )
    assert ok, detail
    assert "initialize handshake OK" in detail
    assert "tausik-project" in detail


def test_probe_reports_silence(tmp_path):
    # NEGATIVE: a process that never answers is a finding, not a hang.
    ok, detail = probe_mcp_server(
        [sys.executable, "-c", "import time; time.sleep(30)"], str(tmp_path), timeout=2
    )
    assert not ok
    assert "no initialize response" in detail


def test_probe_reports_spawn_failure(tmp_path):
    # NEGATIVE: an interpreter that does not exist fails at spawn.
    dead = str(tmp_path / "no-such-python.exe")
    ok, detail = probe_mcp_server([dead, "x.py"], str(tmp_path), timeout=5)
    assert not ok
    assert "spawn failed" in detail


def test_probe_rejects_unexpected_server(tmp_path):
    sp = _stub_server(tmp_path, name="someone-elses-server")
    ok, detail = probe_mcp_server([sys.executable, str(sp)], str(tmp_path), timeout=15)
    assert not ok
    assert "unexpected server name" in detail


def test_probe_finding_appended_only_for_clean_config(tmp_path):
    # A structurally-warned config gets no probe ✓ appended — the structural
    # finding is the actionable one.
    sp = _stub_server(tmp_path)
    stanza = _valid_stanza(sp, tmp_path)
    stanza["mcp"]["tausik-project"]["enabled"] = False
    _write_kilo_config(tmp_path, os.path.join(".kilo", "kilo.jsonc"), stanza)
    findings = check_kilo_config(str(tmp_path))
    assert len(findings) == 1
    assert findings[0][0] == "warn"
