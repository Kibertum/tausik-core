"""Security policy for custom gate commands declared in ``.tausik/config.json``.

A custom gate is a shell command the framework runs on the developer's machine,
declared in a file that travels with the repository. The policy here is the
only thing standing between that and arbitrary execution: the executable must
be on an allow-list, and shell chaining/substitution is refused outright.

Split out of ``project_config`` when that module crossed the 400-line cap; the
public names are re-exported there, so existing imports keep working.
"""

from __future__ import annotations

import os
import re

VALID_GATE_SEVERITIES = frozenset({"warn", "block"})
# v1.4: "verify" is the Verify-First Contract trigger — slow subprocess gates
# (pytest, tsc, cargo, phpstan, etc.) live here, not on "task-done". The CLI
# `tausik verify --task <slug>` runs them and records a green into
# verification_runs; subsequent `task done` checks for a fresh cache hit and
# closes in milliseconds. This decouples task closure from heavy verification
# — fixes "task_done hangs in VS Code Claude Extension" UX.
VALID_GATE_TRIGGERS = frozenset({"task-done", "verify", "commit", "review"})

# --- Security: allowed executables for custom gates ---
ALLOWED_GATE_EXECUTABLES = frozenset(
    {
        "pytest",
        "ruff",
        "mypy",
        "bandit",
        "tsc",
        "eslint",
        "go",
        "golangci-lint",
        "cargo",
        "clippy",
        "phpstan",
        "phpcs",
        "javac",
        "ktlint",
        "npm",
        "npx",
        "pnpm",
        "yarn",
        "make",
        "python",
        "ruby",
        "php",
        # IaC tooling — added when stack-iac-vertical introduced default gates
        # (HIGH-1 review fix: without this, user overrides like
        # vendor/bin/ansible-lint silently fail _validate_custom_gate).
        "ansible-lint",
        "ansible",
        "terraform",
        "tflint",
        "tofu",
        "helm",
        "kubeval",
        "kube-score",
        "hadolint",
    }
)

# Shell operators forbidden in commands that use {files} placeholder
# (broader rule because file paths are user-controlled in {files}).
_SHELL_INJECTION_PATTERN = re.compile(r"\||\&\&|\|\||;|\$\(|`")

# Shell chain/substitution operators that are NEVER acceptable in custom
# gates regardless of {files} — legitimate static gates may pipe stdout
# to head/tail (single `|`), but command chaining (&&, ||, ;) and
# command-substitution ($(, backtick) signal an attempt to escape the
# allowed-executable whitelist. HIGH-2 review fix.
_SHELL_CHAIN_PATTERN = re.compile(r"&&|\|\||;|\$\(|`")


def _validate_custom_gate(name: str, gate: dict) -> str | None:
    """Validate a custom gate command for security.

    Returns None if valid, or an error message string if invalid.
    HIGH-2 review fix: shell metachars are blocked unconditionally now —
    previously the guard required `{files}` placeholder, which let a
    custom gate run pipelines under shell=True without scrutiny.
    """
    command = gate.get("command")
    if not command or command is None:
        return None  # no command = built-in gate like filesize, OK

    # Extract first token (the executable)
    first_token = command.split()[0] if command.strip() else ""
    # Strip path prefixes (e.g. "vendor/bin/phpstan" -> "phpstan")
    exe = first_token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    exe = exe[:-4] if os.name == "nt" and exe.lower().endswith(".exe") else exe

    if exe not in ALLOWED_GATE_EXECUTABLES:
        return (
            f"Custom gate '{name}': executable '{exe}' not in allowed list. "
            f"Allowed: {sorted(ALLOWED_GATE_EXECUTABLES)}"
        )

    # Always reject command chaining / substitution — these escape the
    # allowed-executable whitelist regardless of placeholder usage.
    if _SHELL_CHAIN_PATTERN.search(command):
        return (
            f"Custom gate '{name}': command contains shell operators "
            f"(&&/||/;/$(/`) — refused. Use a wrapper script or split "
            f"into multiple gates."
        )

    # Stricter rule when the user-controlled {files} placeholder is in
    # play: block bare pipes too, since they let user input redirect
    # to an arbitrary downstream command.
    if "{files}" in command and _SHELL_INJECTION_PATTERN.search(command):
        return (
            f"Custom gate '{name}': command contains shell operators "
            f"with {{files}} placeholder — potential injection risk."
        )

    return None
