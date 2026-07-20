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


def executable_basename(command: str | None) -> str:
    """Bare executable name of a gate command, path and ``.exe`` stripped.

    ``"vendor/bin/phpstan analyse"`` -> ``"phpstan"``. Returns ``""`` for an
    empty or whitespace-only command. Single source of this logic: both the
    allow-list check and :func:`validate_default_gate_command` compare against
    it, and two copies would drift into two different security answers.
    """
    if not command or not command.strip():
        return ""
    first_token = command.split()[0]
    exe = first_token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return exe[:-4] if os.name == "nt" and exe.lower().endswith(".exe") else exe


# Wrappers that run *another* tool: the gate's identity is what follows
# them, not the wrapper. Several default gates ship as "npx eslint ..." or
# "python -m pytest ...", and a user who drops the wrapper (plain "eslint
# {files}" against a vendored install) is doing something legitimate.
_RUNNER_EXECUTABLES = frozenset({"npx", "npm", "pnpm", "yarn", "python", "python3", "py"})

# Tokens a runner takes before naming the real tool ("npm run lint",
# "python -m pytest"). Anything else starting with "-" means the runner is
# the tool itself ("python -c pass"), which is exactly the neutering case.
_RUNNER_PASSTHROUGH = frozenset({"run", "exec", "-m"})

# Guards against a pathological "npx npx npx ..." chain walking the token list.
_MAX_RUNNER_HOPS = 3


def gate_command_identity(command: str | None) -> str:
    """The tool a gate command actually invokes, wrappers seen through.

    ``"npx eslint {files}"`` and ``"eslint {files}"`` both answer ``eslint``;
    ``"python -m pytest -q"`` answers ``pytest``. A runner followed by a flag
    is the tool itself: ``"python -c pass"`` answers ``python``, which is why
    swapping it in for ``ruff`` is caught.

    Comparing bare basenames instead would reject the legitimate
    wrapper-dropping case — a real regression this design hit and fixed.
    """
    tokens = command.split() if command else []
    if not tokens:
        return ""

    idx = 0
    exe = executable_basename(tokens[0])
    for _ in range(_MAX_RUNNER_HOPS):
        if exe not in _RUNNER_EXECUTABLES:
            break
        idx += 1
        while idx < len(tokens) and tokens[idx] in _RUNNER_PASSTHROUGH:
            idx += 1
        if idx >= len(tokens) or tokens[idx].startswith("-"):
            # Runner invoked directly — it IS the tool being named.
            break
        exe = executable_basename(tokens[idx])
    return exe


def validate_default_gate_command(
    name: str,
    override_command: str | None,
    default_command: str | None,
) -> str | None:
    """Guard a *default* gate against having its tool swapped out.

    The allow-list alone cannot protect a default gate: every entry on it is
    a legitimate executable, so ``gates.ruff.command = "python -c pass"``
    passes validation and leaves a gate that is enabled, fires on its
    triggers, and is green forever. Since `.tausik/config.json` travels with
    the repository, a clone can neuter the framework's own supervision.

    Policy: an override of a default gate may change the *arguments*, the
    *path*, and the *wrapper*, never the tool. Accepted:
    ``vendor/bin/phpstan analyse --level=8`` (vendored path), ``eslint
    {files}`` against a default of ``npx eslint {files}`` (wrapper dropped).
    Refused: ``python -c pass`` in place of ``ruff`` — the default command
    is kept and a warning is logged.

    Known residual (deliberate, documented in the threat surface): identity
    is the tool, not the meaning of the call, so an inert invocation of the
    *same* tool — ``ruff --version``, ``pytest --collect-only`` — still
    passes. "Does real work" is not machine-checkable, and a
    default-prefix rule would break the vendored and wrapper cases above.

    Returns None when the override is acceptable, else an error message.
    """
    if not default_command:
        # Built-in gate (filesize, tdd_order, renar_drift_*) — implemented
        # in-process, no command to extend. Accepting one would invent an
        # executable where the default deliberately has none.
        return (
            f"Gate '{name}': built-in gate takes no command override "
            f"(default has no command) — override ignored."
        )

    override_tool = gate_command_identity(override_command)
    default_tool = gate_command_identity(default_command)
    if override_tool != default_tool:
        return (
            f"Gate '{name}': command override must keep invoking "
            f"'{default_tool}' (got '{override_tool or 'empty'}'). "
            f"Arguments, vendored paths and runner wrappers may change; "
            f"the tool may not."
        )
    return None


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

    exe = executable_basename(command)

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
