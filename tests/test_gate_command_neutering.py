"""Tests for the default-gate command guard (l26-gate-command-neutering).

The allow-list answers "is this executable tolerable at all?". It cannot
answer "is this still the gate it claims to be?" — every entry on the list
is legitimate, so `gates.ruff.command = "python -c pass"` passes it and
leaves a gate that is enabled, fires on its triggers, and is green forever.
Since `.tausik/config.json` travels with the repository, a clone could
neuter the framework's own supervision without tripping anything.

The guard here constrains the executable of a *default* gate to stay the
one the gate is named after, while leaving arguments and vendored paths
free (AC-2..AC-4, AC-7). Its documented blind spot — an inert call to the
*same* executable — is covered by TestResidualVectorIsDocumented, which
pins the honesty requirement rather than a code behaviour.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from gate_command_policy import (  # noqa: E402
    executable_basename,
    gate_command_identity,
    validate_default_gate_command,
)
from project_config import DEFAULT_GATES, load_gates  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


class TestExecutableBasename:
    """AC-1: one extractor, shared by the allow-list check and the guard."""

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("ruff check {files}", "ruff"),
            ("vendor/bin/phpstan analyse --level=8", "phpstan"),
            ("vendor\\bin\\phpstan.bat analyse", "phpstan.bat"),
            ("C:/tools/mypy {files}", "mypy"),
            ("pytest", "pytest"),
            ("", ""),
            ("   ", ""),
            (None, ""),
        ],
    )
    def test_extraction(self, command, expected):
        assert executable_basename(command) == expected

    @pytest.mark.skipif(os.name != "nt", reason=".exe stripping is Windows-only")
    def test_exe_suffix_stripped_on_windows(self):
        assert executable_basename("C:/tools/ruff.exe check") == "ruff"

    def test_logic_is_not_duplicated_in_scripts(self):
        """AC-1: a second copy would drift into a second security answer."""
        pattern = re.compile(r"rsplit\(\s*[\"']\\\\+[\"']\s*,\s*1\s*\)")
        hits = [
            p.relative_to(REPO).as_posix()
            for p in (REPO / "scripts").rglob("*.py")
            if pattern.search(p.read_text(encoding="utf-8"))
        ]
        assert hits == ["scripts/gate_command_policy.py"], (
            f"path-stripping logic must live in one place, found in: {hits}"
        )


class TestCommandIdentity:
    """Wrappers are transparent; a runner used directly is the tool itself."""

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("ruff check {files}", "ruff"),
            ("npx eslint {files}", "eslint"),
            ("eslint {files}", "eslint"),
            ("npx tsc --noEmit", "tsc"),
            ("python -m pytest -q", "pytest"),
            ("npm run lint", "lint"),
            ("yarn exec tsc --noEmit", "tsc"),
            ("vendor/bin/phpstan analyse", "phpstan"),
            # Runner + flag: the runner IS the tool — the neutering case.
            ("python -c pass", "python"),
            ("python", "python"),
            ("", ""),
            (None, ""),
        ],
    )
    def test_identity(self, command, expected):
        assert gate_command_identity(command) == expected

    def test_runner_chain_terminates(self):
        # Pathological input must not walk off the token list or loop.
        assert gate_command_identity("npx npx npx npx ruff") in {"npx", "ruff"}


class TestGuardUnit:
    def test_same_executable_accepted(self):
        assert (
            validate_default_gate_command("ruff", "ruff check --select=E", "ruff check {files}")
            is None
        )

    def test_vendored_path_accepted(self):
        assert (
            validate_default_gate_command(
                "phpstan", "vendor/bin/phpstan analyse --level=8", "phpstan analyse {files}"
            )
            is None
        )

    def test_swapped_executable_refused(self):
        error = validate_default_gate_command("ruff", "python -c pass", "ruff check {files}")
        assert error is not None
        assert "ruff" in error and "python" in error

    def test_builtin_gate_refuses_any_command(self):
        error = validate_default_gate_command("filesize", "python -c pass", None)
        assert error is not None
        assert "built-in" in error

    @pytest.mark.parametrize("bad", ["", "   ", None])
    def test_malformed_override_refused_without_raising(self, bad):
        # Negative AC: must return an error string, never raise.
        assert validate_default_gate_command("ruff", bad, "ruff check {files}") is not None


class TestLoadGatesIntegration:
    """The guard only matters if load_gates actually consults it."""

    def test_neutered_default_keeps_its_default_command(self):
        cfg = {"gates": {"ruff": {"command": "python -c pass"}}}
        gates = load_gates(cfg)
        assert gates["ruff"]["command"] == DEFAULT_GATES["ruff"]["command"]

    def test_neutering_does_not_silently_disable_the_gate(self):
        """Refusing the command must not leave a half-applied override."""
        cfg = {"gates": {"ruff": {"command": "python -c pass", "severity": "warn"}}}
        gates = load_gates(cfg)
        assert gates["ruff"]["command"] == DEFAULT_GATES["ruff"]["command"]
        # Non-command keys of the same override still apply — the guard is
        # scoped to the command, and trust tiers police the rest.
        assert gates["ruff"]["severity"] == "warn"

    def test_argument_change_still_accepted(self):
        cfg = {"gates": {"ruff": {"command": "ruff check --select=E {files}"}}}
        gates = load_gates(cfg)
        assert gates["ruff"]["command"] == "ruff check --select=E {files}"

    def test_vendored_path_still_accepted(self):
        cfg = {"gates": {"ruff": {"command": "vendor/bin/ruff check {files}"}}}
        gates = load_gates(cfg)
        assert gates["ruff"]["command"] == "vendor/bin/ruff check {files}"

    @pytest.mark.skipif("phpstan" not in DEFAULT_GATES, reason="php stack gates unavailable")
    def test_vendored_phpstan_accepted(self):
        cfg = {"gates": {"phpstan": {"command": "vendor/bin/phpstan analyse --level=8"}}}
        gates = load_gates(cfg)
        assert gates["phpstan"]["command"] == "vendor/bin/phpstan analyse --level=8"

    @pytest.mark.skipif("eslint" not in DEFAULT_GATES, reason="js stack gates unavailable")
    def test_dropping_the_npx_wrapper_is_accepted(self):
        """Regression: the first cut of this guard compared bare basenames
        and refused this, breaking a legitimate vendored-install setup."""
        cfg = {"gates": {"eslint": {"command": "eslint {files}"}}}
        gates = load_gates(cfg)
        assert gates["eslint"]["command"] == "eslint {files}"

    def test_builtin_gate_command_override_refused(self):
        cfg = {"gates": {"filesize": {"command": "python -c pass"}}}
        gates = load_gates(cfg)
        assert gates["filesize"]["command"] == DEFAULT_GATES["filesize"]["command"]

    def test_custom_gate_unaffected_by_guard(self):
        """AC-6: no default to compare against — allow-list only."""
        cfg = {
            "gates": {
                "my-lint": {
                    "enabled": True,
                    "severity": "warn",
                    "trigger": ["commit"],
                    "command": "npx my-lint {files}",
                    "description": "custom",
                }
            }
        }
        gates = load_gates(cfg)
        assert gates["my-lint"]["command"] == "npx my-lint {files}"

    @pytest.mark.parametrize(
        "override",
        [
            {"command": ""},
            {"command": "   "},
            {"command": None},
            {"severity": "warn"},  # no command key at all
        ],
    )
    def test_malformed_overrides_do_not_break_loading(self, override):
        gates = load_gates({"gates": {"ruff": override}})
        assert set(gates.keys()) == set(DEFAULT_GATES.keys())
        assert gates["ruff"]["command"] == DEFAULT_GATES["ruff"]["command"]


class TestResidualVectorIsDocumented:
    """AC-5: what the guard cannot see must be written down, not implied.

    Basename comparison is blind to arguments, so `ruff --version` stays
    green. That is a real residual vector; the project's rule is that a
    supervision hole is recorded honestly rather than left for the next
    reader to rediscover (same posture as decision #139).
    """

    @pytest.mark.parametrize("doc", ["docs/ru/security.md", "docs/en/security.md"])
    def test_threat_surface_names_the_inert_argument_vector(self, doc):
        path = REPO / doc
        assert path.is_file(), f"{doc} missing — threat surface must be documented"
        text = path.read_text(encoding="utf-8").lower()
        assert "--version" in text, (
            f"{doc} must name the inert-arguments residual vector explicitly"
        )
