"""Tests for bootstrap/bootstrap_opencode.py (task opencode-bootstrap-generator).

Every assertion here is a scar. OpenCode killed a user's host with
ConfigInvalidError because an agent invented a `tools` object; it silently
ignored rules because AGENTS.md is first-file-wins; and Kilo's
`${workspaceFolder}` — which OpenCode does not expand — is one careless
copy-paste away. See gotcha #201.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "bootstrap"))

from bootstrap_opencode import (  # noqa: E402
    generate_opencode_commands,
    generate_opencode_config,
    generate_opencode_plugin,
    generate_opencode_rules,
    scaffold_opencode,
)

CONFIG = "opencode.json"


def _mk_servers(target_dir: str, names: tuple[str, ...] = ("project", "codebase-rag", "brain")):
    """Create fake server.py files inside <target_dir>/mcp/<name>/server.py."""
    for name in names:
        d = os.path.join(target_dir, "mcp", name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "server.py"), "w", encoding="utf-8") as f:
            f.write("# fake server\n")


def _read(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def project(tmp_path):
    project_dir = tmp_path / "proj"
    target_dir = project_dir / ".opencode"
    target_dir.mkdir(parents=True)
    _mk_servers(str(target_dir))
    return str(project_dir), str(target_dir)


class TestMcpStanzas:
    def test_writes_config_at_project_root_not_in_opencode_dir(self, project):
        project_dir, target_dir = project
        path = generate_opencode_config(project_dir, target_dir, venv_python="/v/bin/python")
        assert path == os.path.join(project_dir, CONFIG)
        assert os.path.isfile(path)
        assert not os.path.exists(os.path.join(target_dir, CONFIG))

    def test_three_servers_local_and_enabled(self, project):
        project_dir, target_dir = project
        cfg = _read(generate_opencode_config(project_dir, target_dir, venv_python="/v/bin/python"))
        assert set(cfg["mcp"]) == {"tausik-project", "codebase-rag", "tausik-brain"}
        for stanza in cfg["mcp"].values():
            assert stanza["type"] == "local"
            assert stanza["enabled"] is True
            assert stanza["command"][2] == "--project"

    def test_missing_server_is_skipped_not_emitted_dead(self, tmp_path):
        """A server.py that exists nowhere must not become a command that fails at launch."""
        project_dir = tmp_path / "proj"
        target_dir = project_dir / ".opencode"
        target_dir.mkdir(parents=True)
        _mk_servers(str(target_dir), names=("project",))  # rag + brain absent
        cfg = _read(generate_opencode_config(str(project_dir), str(target_dir)))
        assert set(cfg["mcp"]) == {"tausik-project"}

    def test_falls_back_to_lib_dir_canonical(self, tmp_path):
        project_dir = tmp_path / "proj"
        target_dir = project_dir / ".opencode"
        target_dir.mkdir(parents=True)
        lib = tmp_path / "lib"
        canonical = lib / "harness" / "claude" / "mcp" / "project"
        canonical.mkdir(parents=True)
        (canonical / "server.py").write_text("# canonical\n", encoding="utf-8")
        cfg = _read(generate_opencode_config(str(project_dir), str(target_dir), lib_dir=str(lib)))
        assert "tausik-project" in cfg["mcp"]
        assert cfg["mcp"]["tausik-project"]["command"][1] == str(canonical / "server.py")

    def test_no_servers_anywhere_still_writes_instructions(self, tmp_path):
        """Rules delivery must not hinge on MCP discovery — they are separate promises."""
        project_dir = tmp_path / "proj"
        target_dir = project_dir / ".opencode"
        target_dir.mkdir(parents=True)
        cfg = _read(generate_opencode_config(str(project_dir), str(target_dir)))
        assert cfg.get("mcp", {}) == {}
        assert cfg["instructions"] == [".opencode/tausik-rules.md"]


class TestPathsAreAbsolute:
    def test_no_workspacefolder_anywhere(self, project):
        """OpenCode expands only {env:} and {file:} — ${workspaceFolder} stays literal."""
        project_dir, target_dir = project
        raw = open(
            generate_opencode_config(project_dir, target_dir, venv_python="/v/bin/python"),
            encoding="utf-8",
        ).read()
        assert "${workspaceFolder}" not in raw

    def test_command_entries_are_absolute(self, project):
        project_dir, target_dir = project
        cfg = _read(generate_opencode_config(project_dir, target_dir, venv_python="/v/bin/python"))
        cmd = cfg["mcp"]["tausik-project"]["command"]
        assert os.path.isabs(cmd[1])  # server.py
        assert os.path.isabs(cmd[3])  # --project value
        assert cmd[3] == os.path.abspath(project_dir)

    def test_fallback_interpreter_is_resolved_absolutely(self, project):
        """Without a venv python we still must not emit a bare "python": OpenCode spawns
        MCP servers itself and a GUI-launched host may hand them no shell PATH, leaving
        a dead server and no explanation. The bare name survives only if PATH has no
        interpreter at all — which cannot happen in a run of this very test."""
        project_dir, target_dir = project
        cfg = _read(generate_opencode_config(project_dir, target_dir, venv_python=None))
        exe = cfg["mcp"]["tausik-project"]["command"][0]
        assert os.path.isabs(exe), f"interpreter {exe!r} is not absolute"
        assert os.path.isfile(exe)


class TestToolsKeyIsNeverWritten:
    def test_generator_never_emits_tools(self, project):
        """`tools` is boolean-only in OpenCode; an object there = ConfigInvalidError,
        which is precisely what killed the user's host."""
        project_dir, target_dir = project
        cfg = _read(generate_opencode_config(project_dir, target_dir, venv_python="/v/bin/python"))
        assert "tools" not in cfg

    def test_users_boolean_tools_survives_untouched(self, project):
        """Do not create our own — but do not delete theirs either."""
        project_dir, target_dir = project
        path = os.path.join(project_dir, CONFIG)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"tools": {"bash": False, "write": True}}, f)
        cfg = _read(generate_opencode_config(project_dir, target_dir))
        assert cfg["tools"] == {"bash": False, "write": True}


class TestIdempotence:
    def test_instructions_does_not_grow_on_rerun(self, project):
        project_dir, target_dir = project
        for _ in range(3):
            cfg = _read(generate_opencode_config(project_dir, target_dir))
        assert cfg["instructions"] == [".opencode/tausik-rules.md"]

    def test_rerun_preserves_foreign_keys_and_servers(self, project):
        project_dir, target_dir = project
        path = os.path.join(project_dir, CONFIG)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "model": "anthropic/claude-opus-4-8",
                    "provider": {"anthropic": {"options": {}}},
                    "agent": {"build": {"mode": "primary"}},
                    "permission": {"bash": "ask"},
                    "instructions": ["CONTRIBUTING.md"],
                    "mcp": {"user-server": {"type": "local", "command": ["node", "x.js"]}},
                },
                f,
            )
        generate_opencode_config(project_dir, target_dir)
        cfg = _read(generate_opencode_config(project_dir, target_dir))

        assert cfg["model"] == "anthropic/claude-opus-4-8"
        assert cfg["provider"] == {"anthropic": {"options": {}}}
        assert cfg["agent"] == {"build": {"mode": "primary"}}
        assert cfg["permission"] == {"bash": "ask"}
        assert cfg["mcp"]["user-server"] == {"type": "local", "command": ["node", "x.js"]}
        assert cfg["instructions"] == ["CONTRIBUTING.md", ".opencode/tausik-rules.md"]

    def test_rules_body_not_rewritten_on_rerun(self, project):
        project_dir, target_dir = project
        first = generate_opencode_rules(project_dir, "proj", ["python"])
        with open(first, "a", encoding="utf-8") as f:
            f.write("\n<!-- user edit -->\n")
        again = generate_opencode_rules(project_dir, "proj", ["python"])
        assert again == first
        assert "<!-- user edit -->" in open(first, encoding="utf-8").read()


class TestMalformedConfig:
    def test_broken_json_does_not_crash_bootstrap(self, project):
        project_dir, target_dir = project
        path = os.path.join(project_dir, CONFIG)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ this is not json ,,, ")
        cfg = _read(generate_opencode_config(project_dir, target_dir))
        assert set(cfg["mcp"]) == {"tausik-project", "codebase-rag", "tausik-brain"}
        assert cfg["instructions"] == [".opencode/tausik-rules.md"]

    def test_replacing_a_broken_config_is_announced(self, project, capsys):
        """The unreadable file may have held the user's model/provider/permission keys.
        Losing them is sometimes unavoidable; losing them silently is not."""
        project_dir, target_dir = project
        with open(os.path.join(project_dir, CONFIG), "w", encoding="utf-8") as f:
            f.write('{ "model": "anthropic/claude-opus-4-8", ,, ')
        generate_opencode_config(project_dir, target_dir)
        out = capsys.readouterr().out
        assert "WARNING" in out and "unreadable" in out

    def test_non_dict_json_is_replaced(self, project):
        project_dir, target_dir = project
        path = os.path.join(project_dir, CONFIG)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(["not", "an", "object"], f)
        cfg = _read(generate_opencode_config(project_dir, target_dir))
        assert isinstance(cfg, dict)
        assert "mcp" in cfg


class TestRulesFile:
    def test_rules_file_carries_the_shared_body(self, project):
        project_dir, _ = project
        path = generate_opencode_rules(project_dir, "myproj", ["python"])
        assert path == os.path.join(project_dir, ".opencode", "tausik-rules.md")
        body = open(path, encoding="utf-8").read()
        assert "myproj" in body
        assert "task start" in body  # hard constraint from the shared template

    def test_config_and_rules_agree_on_the_path(self, project):
        """The `instructions` entry must point at the file we actually wrote."""
        project_dir, target_dir = project
        cfg = _read(generate_opencode_config(project_dir, target_dir))
        rules = generate_opencode_rules(project_dir, "myproj", ["python"])
        referenced = os.path.join(project_dir, *cfg["instructions"][0].split("/"))
        assert os.path.abspath(referenced) == os.path.abspath(rules)

    def test_custom_rules_path_from_config(self, project):
        project_dir, target_dir = project
        conf = {"opencode": {"rules_path": "docs/tausik.md"}}
        cfg = _read(generate_opencode_config(project_dir, target_dir, config=conf))
        rules = generate_opencode_rules(project_dir, "p", ["python"], config=conf)
        assert cfg["instructions"] == ["docs/tausik.md"]
        assert rules == os.path.join(project_dir, "docs", "tausik.md")
        assert os.path.isfile(rules)


class TestVictimUpgradePath:
    """The project this whole release exists to repair still holds the config that killed it.

    Bootstrap merges beside it and used to print a cheerful success — while OpenCode still
    refused to boot for exactly the same reason as before.
    """

    def test_fatal_tools_object_is_called_out(self, project, capsys):
        project_dir, target_dir = project
        with open(os.path.join(project_dir, CONFIG), "w", encoding="utf-8") as f:
            json.dump({"tools": {"qg0": {"module": "./.opencode/tools/qg0.ts"}}}, f)

        generate_opencode_config(project_dir, target_dir)

        out = capsys.readouterr().out
        assert "CANNOT START" in out
        assert "ConfigInvalidError" in out
        # We report it; we do not silently rewrite the user's file.
        assert _read(os.path.join(project_dir, CONFIG))["tools"] == {
            "qg0": {"module": "./.opencode/tools/qg0.ts"}
        }

    @pytest.mark.parametrize("fatal", [["qg0"], "qg0", 42])
    def test_non_object_tools_is_fatal_too(self, project, capsys, fatal):
        """A list is as fatal as an object — and an improvising agent reaches for one."""
        project_dir, target_dir = project
        with open(os.path.join(project_dir, CONFIG), "w", encoding="utf-8") as f:
            json.dump({"tools": fatal}, f)
        generate_opencode_config(project_dir, target_dir)
        assert "CANNOT START" in capsys.readouterr().out

    def test_boolean_tools_stays_silent(self, project, capsys):
        """No crying wolf: the legal form must not be reported as fatal."""
        project_dir, target_dir = project
        with open(os.path.join(project_dir, CONFIG), "w", encoding="utf-8") as f:
            json.dump({"tools": {"bash": False}}, f)
        generate_opencode_config(project_dir, target_dir)
        assert "CANNOT START" not in capsys.readouterr().out

    def test_singular_plugin_dir_is_called_out(self, project, capsys):
        """`.opencode/plugin/` never loads — and if it imports an npm package that isn't
        installed, it can take the host down at load. That is the incident, verbatim."""
        project_dir, _target = project
        os.makedirs(os.path.join(project_dir, ".opencode", "plugin"), exist_ok=True)
        generate_opencode_config(project_dir, os.path.join(project_dir, ".opencode"))
        out = capsys.readouterr().out
        assert "SINGULAR" in out


class TestPluginUpgradeReachesExistingInstalls:
    def test_library_copy_beats_the_installed_one(self, tmp_path):
        """If the installed plugin won, a user upgrading TAUSIK to get a FIXED gate would
        run bootstrap, see it succeed, and keep running the broken one — the enforcement
        artifact would be the single file an upgrade could never reach."""
        lib = tmp_path / "lib"
        src_dir = lib / "harness" / "opencode" / "plugins"
        src_dir.mkdir(parents=True)
        (src_dir / "tausik-qg0.js").write_text("// v1 gate\n", encoding="utf-8")

        target = tmp_path / "proj" / ".opencode"
        target.mkdir(parents=True)
        installed = generate_opencode_plugin(str(target), lib_dir=str(lib))
        assert open(installed, encoding="utf-8").read() == "// v1 gate\n"

        # TAUSIK is upgraded: the library ships a fixed gate.
        (src_dir / "tausik-qg0.js").write_text("// v2 gate — security fix\n", encoding="utf-8")
        generate_opencode_plugin(str(target), lib_dir=str(lib))

        assert open(installed, encoding="utf-8").read() == "// v2 gate — security fix\n", (
            "the upgraded plugin never reached the project"
        )

    def test_installed_copy_is_the_fallback_without_a_lib(self, tmp_path):
        target = tmp_path / "proj" / ".opencode"
        (target / "plugins").mkdir(parents=True)
        (target / "plugins" / "tausik-qg0.js").write_text("// installed\n", encoding="utf-8")
        assert generate_opencode_plugin(str(target)) == str(target / "plugins" / "tausik-qg0.js")


class TestCommandStubs:
    def test_stubs_land_in_commands_plural(self, project):
        project_dir, target_dir = project
        n = generate_opencode_commands(target_dir)
        assert n == 11
        commands = os.path.join(target_dir, "commands")
        assert os.path.isfile(os.path.join(commands, "start.md"))
        assert not os.path.exists(os.path.join(target_dir, "command"))
        body = open(os.path.join(commands, "start.md"), encoding="utf-8").read()
        assert body.startswith("---\ndescription:")

    def test_existing_stub_is_not_overwritten(self, project):
        project_dir, target_dir = project
        commands = os.path.join(target_dir, "commands")
        os.makedirs(commands, exist_ok=True)
        with open(os.path.join(commands, "start.md"), "w", encoding="utf-8") as f:
            f.write("MY OWN COMMAND\n")
        generate_opencode_commands(target_dir)
        assert open(os.path.join(commands, "start.md"), encoding="utf-8").read() == (
            "MY OWN COMMAND\n"
        )


class TestScaffoldOrchestrator:
    """scaffold_opencode is the path a real user actually invokes; it had no test at all."""

    def test_produces_config_rules_plugin_and_commands(self, tmp_path):
        lib = tmp_path / "lib"
        src_dir = lib / "harness" / "opencode" / "plugins"
        src_dir.mkdir(parents=True)
        (src_dir / "tausik-qg0.js").write_text("// gate\n", encoding="utf-8")

        project_dir = tmp_path / "proj"
        target = project_dir / ".opencode"
        _mk_servers(str(target))

        scaffold_opencode(
            str(project_dir), str(target), None, str(lib), {"project": "demo"}, ["python"]
        )

        assert os.path.isfile(project_dir / "opencode.json")
        assert os.path.isfile(project_dir / ".opencode" / "tausik-rules.md")
        assert os.path.isfile(project_dir / ".opencode" / "plugins" / "tausik-qg0.js")
        assert os.path.isfile(project_dir / ".opencode" / "commands" / "start.md")

    def test_scaffold_writes_no_agents_md(self, tmp_path):
        """OpenCode MERGES `instructions` into AGENTS.md, so shipping both would put the
        same rules in the context twice — and context bloat is one of the pains this work
        exists to fix."""
        lib = tmp_path / "lib"
        src_dir = lib / "harness" / "opencode" / "plugins"
        src_dir.mkdir(parents=True)
        (src_dir / "tausik-qg0.js").write_text("// gate\n", encoding="utf-8")

        project_dir = tmp_path / "proj"
        target = project_dir / ".opencode"
        _mk_servers(str(target))

        scaffold_opencode(
            str(project_dir), str(target), None, str(lib), {"project": "demo"}, ["python"]
        )
        assert not os.path.exists(project_dir / "AGENTS.md")


class TestRulesPathIsUntrusted:
    """`.tausik/config.json` travels with the repo. A tampered one (malicious PR, cloned
    template) must not turn `bootstrap --ide opencode` into an arbitrary-file-write."""

    @pytest.mark.parametrize(
        "evil",
        [
            "../../../../evil.md",
            "..\\..\\evil.md",
            "docs/../../evil.md",
            # Drive-qualified. `C:evil.md` is drive-RELATIVE: os.path.isabs calls it False
            # even on Windows. And on a project sitting on another drive, os.path.commonpath
            # RAISES ValueError — so the containment test used to crash bootstrap with a raw
            # traceback instead of refusing the input. A crash is not a guard.
            "C:/Windows/Temp/evil.md",
            "C:evil.md",
            "//server/share/evil.md",
            ".",
            "..",
        ],
    )
    def test_traversal_is_refused_and_falls_back(self, project, evil, capsys):
        project_dir, target_dir = project
        conf = {"opencode": {"rules_path": evil}}

        cfg = _read(generate_opencode_config(project_dir, target_dir, config=conf))
        rules = generate_opencode_rules(project_dir, "p", ["python"], config=conf)

        assert cfg["instructions"] == [".opencode/tausik-rules.md"]
        assert rules == os.path.join(project_dir, ".opencode", "tausik-rules.md")
        assert "WARNING" in capsys.readouterr().out, "the refusal must be announced"

        escaped = os.path.abspath(os.path.join(project_dir, "..", "evil.md"))
        assert not os.path.exists(escaped)
        assert not os.path.exists(
            os.path.abspath(os.path.join(project_dir, "..", "..", "..", "..", "evil.md"))
        )

    def test_absolute_rules_path_is_refused(self, project, tmp_path):
        project_dir, target_dir = project
        outside = tmp_path / "outside.md"
        conf = {"opencode": {"rules_path": str(outside).replace("\\", "/")}}

        rules = generate_opencode_rules(project_dir, "p", ["python"], config=conf)

        assert not outside.exists(), "an absolute rules_path wrote outside the project"
        assert rules == os.path.join(project_dir, ".opencode", "tausik-rules.md")

    def test_a_legitimate_nested_path_still_works(self, project):
        """The guard must not break the honest use of the override."""
        project_dir, target_dir = project
        conf = {"opencode": {"rules_path": "docs/rules/tausik.md"}}
        rules = generate_opencode_rules(project_dir, "p", ["python"], config=conf)
        assert rules == os.path.join(project_dir, "docs", "rules", "tausik.md")
        assert os.path.isfile(rules)
