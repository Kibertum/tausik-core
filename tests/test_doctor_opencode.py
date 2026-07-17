"""Tests for scripts/service_doctor_opencode.py — the doctor check for OpenCode.

Every negative case here is planted from a real failure: an object under `tools`
(ConfigInvalidError, host dead), a plugin dir in the singular (enforcement silently
absent), `instructions` pointing at nothing (rules silently never load). A doctor
that reports "All clean" on any of those is worse than no doctor at all.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))

from service_doctor_opencode import check_opencode_config  # noqa: E402

VALID_SERVER = {"type": "local", "command": ["python", None, "--project", "/proj"], "enabled": True}


def _mk(
    tmp_path,
    config: dict | str | None = None,
    *,
    plugin=True,
    singular=False,
    rules=True,
    cli=True,
):
    """Build an OpenCode-looking project. Returns its root."""
    root = tmp_path / "proj"
    (root / ".opencode").mkdir(parents=True)

    if cli:
        # The wrapper the plugin shells out to on every write. Windows needs the .cmd.
        wrapper = root / ".tausik" / ("tausik.cmd" if os.name == "nt" else "tausik")
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        wrapper.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    server = root / ".opencode" / "mcp" / "project" / "server.py"
    server.parent.mkdir(parents=True)
    server.write_text("# server\n", encoding="utf-8")

    if plugin:
        d = root / ".opencode" / ("plugin" if singular else "plugins")
        d.mkdir()
        (d / "tausik-qg0.js").write_text("// gate\n", encoding="utf-8")

    if rules:
        (root / ".opencode" / "tausik-rules.md").write_text("# rules\n", encoding="utf-8")

    if config is None:
        cmd = ["python", str(server), "--project", str(root)]
        config = {
            "mcp": {"tausik-project": {"type": "local", "command": cmd, "enabled": True}},
            "instructions": [".opencode/tausik-rules.md"],
        }
    if config != "SKIP":
        path = root / "opencode.json"
        if isinstance(config, str):
            path.write_text(config, encoding="utf-8")
        else:
            path.write_text(json.dumps(config), encoding="utf-8")
    return root


def _sev(findings, sev):
    return [f for f in findings if f[0] == sev]


def test_non_opencode_project_is_silent(tmp_path):
    """No .opencode/ -> no findings at all. The check must add zero noise elsewhere."""
    assert check_opencode_config(str(tmp_path)) == []


def test_healthy_install_is_all_ok(tmp_path):
    root = _mk(tmp_path)
    findings = check_opencode_config(str(root))
    assert findings, "a healthy OpenCode install must still report its status"
    assert not _sev(findings, "fail") and not _sev(findings, "warn")


class TestToolsObjectIsFatal:
    def test_object_under_tools_is_a_failure(self, tmp_path):
        """This is the exact shape that killed the user's host."""
        root = _mk(tmp_path)
        cfg = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        cfg["tools"] = {"qg0": {"module": "./.opencode/tools/qg0.ts"}}
        (root / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")

        fails = _sev(check_opencode_config(str(root)), "fail")
        assert fails, "an object under `tools` must fail loudly"
        assert "ConfigInvalidError" in fails[0][2]

    @pytest.mark.parametrize("fatal", [["qg0"], "qg0", 42])
    def test_tools_that_is_not_an_object_is_also_fatal(self, tmp_path, fatal):
        """A list is as fatal at startup as a nested object. The first version of this check
        only inspected dicts, so `"tools": ["qg0"]` walked past it and doctor reported
        'valid — no `tools` object': an OK affirming the exact thing that was broken."""
        root = _mk(tmp_path)
        cfg = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        cfg["tools"] = fatal
        (root / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")

        findings = check_opencode_config(str(root))
        fails = _sev(findings, "fail")
        assert fails, f"tools={fatal!r} must fail — the host will not boot"
        assert any("ConfigInvalidError" in f[2] for f in fails)
        assert not any("no `tools` object" in f[2] for f in findings)

    def test_boolean_tools_are_fine(self, tmp_path):
        """Booleans are the legal form — the check must not cry wolf on them."""
        root = _mk(tmp_path)
        cfg = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        cfg["tools"] = {"bash": False, "write": True}
        (root / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
        assert not _sev(check_opencode_config(str(root)), "fail")


class TestPluginEnforcement:
    def test_missing_plugin_is_a_failure(self, tmp_path):
        root = _mk(tmp_path, plugin=False)
        fails = _sev(check_opencode_config(str(root)), "fail")
        assert any("QG-0 is NOT enforced" in f[2] for f in fails)

    def test_singular_plugin_dir_is_caught(self, tmp_path):
        """`.opencode/plugin/` never loads and never complains — doctor must complain."""
        root = _mk(tmp_path, singular=True)
        fails = _sev(check_opencode_config(str(root)), "fail")
        assert any("singular" in f[2] for f in fails)

    def test_plugin_without_its_cli_is_not_called_enforcement(self, tmp_path):
        """The plugin asks the CLI wrapper, on every write, whether a task is active.
        No wrapper -> the query throws -> fail-open -> every write passes. Reporting
        'writes are refused' in that state is a promise doctor never verified."""
        root = _mk(tmp_path, cli=False)
        findings = check_opencode_config(str(root))
        fails = _sev(findings, "fail")
        assert any("fails OPEN" in f[2] for f in fails), "missing CLI wrapper went unnoticed"
        assert not any("are refused" in f[2] for f in findings), (
            "doctor still claims writes are refused while the gate cannot even query"
        )


class TestRulesWiring:
    def test_missing_instructions_key_warns(self, tmp_path):
        root = _mk(tmp_path)
        cfg = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        del cfg["instructions"]
        (root / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
        warns = _sev(check_opencode_config(str(root)), "warn")
        assert any("instructions" in w[2] for w in warns)

    def test_instructions_pointing_at_a_missing_file_warns(self, tmp_path):
        root = _mk(tmp_path, rules=False)
        warns = _sev(check_opencode_config(str(root)), "warn")
        assert any("never" in w[2] and "load" in w[2] for w in warns)


class TestMcpStanza:
    def test_workspacefolder_in_command_is_a_failure(self, tmp_path):
        """Copied from the Kilo config by mistake: OpenCode never expands it."""
        root = _mk(tmp_path)
        cfg = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        cfg["mcp"]["tausik-project"]["command"] = [
            "python",
            "${workspaceFolder}/.opencode/mcp/project/server.py",
            "--project",
            "${workspaceFolder}",
        ]
        (root / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
        fails = _sev(check_opencode_config(str(root)), "fail")
        assert any("workspaceFolder" in f[2] for f in fails)

    def test_missing_server_warns(self, tmp_path):
        root = _mk(tmp_path)
        cfg = json.loads((root / "opencode.json").read_text(encoding="utf-8"))
        cfg["mcp"] = {}
        (root / "opencode.json").write_text(json.dumps(cfg), encoding="utf-8")
        assert _sev(check_opencode_config(str(root)), "warn")


class TestBrokenInputs:
    def test_broken_json_fails_without_crashing(self, tmp_path):
        root = _mk(tmp_path, config="{ not json ,,")
        fails = _sev(check_opencode_config(str(root)), "fail")
        assert any("invalid JSON" in f[2] for f in fails)

    def test_opencode_dir_without_config_warns(self, tmp_path):
        root = _mk(tmp_path, config="SKIP")
        assert _sev(check_opencode_config(str(root)), "warn")

    def test_check_never_raises(self, tmp_path):
        """A doctor that crashes tells the user nothing. Findings, not exceptions."""
        root = _mk(tmp_path, config=json.dumps(["not", "an", "object"]))
        try:
            findings = check_opencode_config(str(root))
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"check raised instead of reporting: {e}")
        assert _sev(findings, "fail")
